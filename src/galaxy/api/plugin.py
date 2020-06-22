import asyncio
import dataclasses
import json
import logging
import sys
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union, AsyncGenerator

from galaxy.api.consts import Feature, OSCompatibility
from galaxy.api.jsonrpc import ApplicationError, Connection
from galaxy.api.types import (
    Achievement, Authentication, Game, GameLibrarySettings, GameTime, LocalGame, NextStep, UserInfo, UserPresence,
    Subscription, SubscriptionGame
)
from galaxy.task_manager import TaskManager
from galaxy.api.importer import Importer, CollectionImporter


logger = logging.getLogger(__name__)


class JSONEncoder(json.JSONEncoder):
    def default(self, o):  # pylint: disable=method-hidden
        if dataclasses.is_dataclass(o):
            # filter None values
            def dict_factory(elements):
                return {k: v for k, v in elements if v is not None}

            return dataclasses.asdict(o, dict_factory=dict_factory)
        if isinstance(o, Enum):
            return o.value
        return super().default(o)


class Plugin:
    """Use and override methods of this class to create a new platform integration."""

    def __init__(self, platform, version, reader, writer, handshake_token):
        logger.info("Creating plugin for platform %s, version %s", platform.value, version)
        self._platform = platform
        self._version = version

        self._features: Set[Feature] = set()
        self._active = True

        self._reader, self._writer = reader, writer
        self._handshake_token = handshake_token

        encoder = JSONEncoder()
        self._connection = Connection(self._reader, self._writer, encoder)

        self._persistent_cache = dict()

        self._internal_task_manager = TaskManager("plugin internal")
        self._external_task_manager = TaskManager("plugin external")

        self._achievements_importer = Importer(
            self._external_task_manager,
            "achievements",
            self.get_unlocked_achievements,
            self.prepare_achievements_context,
            self._game_achievements_import_success,
            self._game_achievements_import_failure,
            self._achievements_import_finished,
            self.achievements_import_complete
        )
        self._game_time_importer = Importer(
            self._external_task_manager,
            "game times",
            self.get_game_time,
            self.prepare_game_times_context,
            self._game_time_import_success,
            self._game_time_import_failure,
            self._game_times_import_finished,
            self.game_times_import_complete
        )
        self._game_library_settings_importer = Importer(
            self._external_task_manager,
            "game library settings",
            self.get_game_library_settings,
            self.prepare_game_library_settings_context,
            self._game_library_settings_import_success,
            self._game_library_settings_import_failure,
            self._game_library_settings_import_finished,
            self.game_library_settings_import_complete
        )
        self._os_compatibility_importer = Importer(
            self._external_task_manager,
            "os compatibility",
            self.get_os_compatibility,
            self.prepare_os_compatibility_context,
            self._os_compatibility_import_success,
            self._os_compatibility_import_failure,
            self._os_compatibility_import_finished,
            self.os_compatibility_import_complete
        )
        self._user_presence_importer = Importer(
            self._external_task_manager,
            "users presence",
            self.get_user_presence,
            self.prepare_user_presence_context,
            self._user_presence_import_success,
            self._user_presence_import_failure,
            self._user_presence_import_finished,
            self.user_presence_import_complete
        )
        self._local_size_importer = Importer(
            self._external_task_manager,
            "local size",
            self.get_local_size,
            self.prepare_local_size_context,
            self._local_size_import_success,
            self._local_size_import_failure,
            self._local_size_import_finished,
            self.local_size_import_complete
        )
        self._subscription_games_importer = CollectionImporter(
            self._subscriptions_games_partial_import_finished,
            self._external_task_manager,
            "subscription games",
            self.get_subscription_games,
            self.prepare_subscription_games_context,
            self._subscription_games_import_success,
            self._subscription_games_import_failure,
            self._subscription_games_import_finished,
            self.subscription_games_import_complete
        )

        # internal
        self._register_method("shutdown", self._shutdown, internal=True)
        self._register_method("get_capabilities", self._get_capabilities, internal=True, immediate=True)
        self._register_method(
            "initialize_cache",
            self._initialize_cache,
            internal=True,
            immediate=True,
            sensitive_params="data"
        )
        self._register_method("ping", self._ping, internal=True, immediate=True)

        # implemented by developer
        self._register_method(
            "init_authentication",
            self.authenticate,
            sensitive_params=["stored_credentials"]
        )
        self._register_method(
            "pass_login_credentials",
            self.pass_login_credentials,
            sensitive_params=["cookies", "credentials"]
        )
        self._register_method(
            "import_owned_games",
            self.get_owned_games,
            result_name="owned_games"
        )
        self._detect_feature(Feature.ImportOwnedGames, ["get_owned_games"])

        self._register_method("start_achievements_import", self._start_achievements_import)
        self._detect_feature(Feature.ImportAchievements, ["get_unlocked_achievements"])

        self._register_method("import_local_games", self.get_local_games, result_name="local_games")
        self._detect_feature(Feature.ImportInstalledGames, ["get_local_games"])

        self._register_notification("launch_game", self.launch_game)
        self._detect_feature(Feature.LaunchGame, ["launch_game"])

        self._register_notification("install_game", self.install_game)
        self._detect_feature(Feature.InstallGame, ["install_game"])

        self._register_notification("uninstall_game", self.uninstall_game)
        self._detect_feature(Feature.UninstallGame, ["uninstall_game"])

        self._register_notification("shutdown_platform_client", self.shutdown_platform_client)
        self._detect_feature(Feature.ShutdownPlatformClient, ["shutdown_platform_client"])

        self._register_notification("launch_platform_client", self.launch_platform_client)
        self._detect_feature(Feature.LaunchPlatformClient, ["launch_platform_client"])

        self._register_method("import_friends", self.get_friends, result_name="friend_info_list")
        self._detect_feature(Feature.ImportFriends, ["get_friends"])

        self._register_method("start_game_times_import", self._start_game_times_import)
        self._detect_feature(Feature.ImportGameTime, ["get_game_time"])

        self._register_method("start_game_library_settings_import", self._start_game_library_settings_import)
        self._detect_feature(Feature.ImportGameLibrarySettings, ["get_game_library_settings"])

        self._register_method("start_os_compatibility_import", self._start_os_compatibility_import)
        self._detect_feature(Feature.ImportOSCompatibility, ["get_os_compatibility"])

        self._register_method("start_user_presence_import", self._start_user_presence_import)
        self._detect_feature(Feature.ImportUserPresence, ["get_user_presence"])

        self._register_method("start_local_size_import", self._start_local_size_import)
        self._detect_feature(Feature.ImportLocalSize, ["get_local_size"])

        self._register_method("import_subscriptions", self.get_subscriptions, result_name="subscriptions")
        self._detect_feature(Feature.ImportSubscriptions, ["get_subscriptions"])

        self._register_method("start_subscription_games_import", self._start_subscription_games_import)
        self._detect_feature(Feature.ImportSubscriptionGames, ["get_subscription_games"])

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.close()
        await self.wait_closed()

    @property
    def features(self) -> List[Feature]:
        return list(self._features)

    @property
    def persistent_cache(self) -> Dict[str, str]:
        """The cache is only available after the :meth:`~.handshake_complete()` is called.
        """
        return self._persistent_cache

    def _implements(self, methods: List[str]) -> bool:
        for method in methods:
            if method not in self.__class__.__dict__:
                return False
        return True

    def _detect_feature(self, feature: Feature, methods: List[str]):
        if self._implements(methods):
            self._features.add(feature)

    def _register_method(self, name, handler, result_name=None, internal=False, immediate=False,
                         sensitive_params=False):
        def wrap_result(result):
            if result_name:
                result = {
                    result_name: result
                }
            return result

        if immediate:
            def method(*args, **kwargs):
                result = handler(*args, **kwargs)
                return wrap_result(result)

            self._connection.register_method(name, method, True, sensitive_params)
        else:
            async def method(*args, **kwargs):
                if not internal:
                    handler_ = self._wrap_external_method(handler, name)
                else:
                    handler_ = handler
                result = await handler_(*args, **kwargs)
                return wrap_result(result)

            self._connection.register_method(name, method, False, sensitive_params)

    def _register_notification(self, name, handler, internal=False, immediate=False, sensitive_params=False):
        if not internal and not immediate:
            handler = self._wrap_external_method(handler, name)
        self._connection.register_notification(name, handler, immediate, sensitive_params)

    def _wrap_external_method(self, handler, name: str):
        async def wrapper(*args, **kwargs):
            return await self._external_task_manager.create_task(handler(*args, **kwargs), name, False)

        return wrapper

    async def run(self):
        """Plugin's main coroutine."""
        await self._connection.run()
        logger.debug("Plugin run loop finished")

    def close(self) -> None:
        if not self._active:
            return

        logger.info("Closing plugin")
        self._connection.close()
        self._external_task_manager.cancel()

        async def shutdown():
            try:
                await asyncio.wait_for(self.shutdown(), 30)
            except asyncio.TimeoutError:
                logging.warning("Plugin shutdown timed out")

        self._internal_task_manager.create_task(shutdown(), "shutdown")
        self._active = False

    async def wait_closed(self) -> None:
        logger.debug("Waiting for plugin to close")
        await self._external_task_manager.wait()
        await self._internal_task_manager.wait()
        await self._connection.wait_closed()
        logger.debug("Plugin closed")

    def create_task(self, coro, description):
        """Wrapper around asyncio.create_task - takes care of canceling tasks on shutdown"""
        return self._external_task_manager.create_task(coro, description)

    async def _pass_control(self):
        while self._active:
            try:
                self.tick()
            except Exception:
                logger.exception("Unexpected exception raised in plugin tick")
            await asyncio.sleep(1)

    async def _shutdown(self):
        logger.info("Shutting down")
        self.close()
        await self._external_task_manager.wait()
        await self._internal_task_manager.wait()

    def _get_capabilities(self):
        return {
            "platform_name": self._platform,
            "features": self.features,
            "token": self._handshake_token
        }

    def _initialize_cache(self, data: Dict):
        self._persistent_cache = data
        try:
            self.handshake_complete()
        except Exception:
            logger.exception("Unhandled exception during `handshake_complete` step")
        self._internal_task_manager.create_task(self._pass_control(), "tick")

    @staticmethod
    def _ping():
        pass

    # notifications
    def store_credentials(self, credentials: Dict[str, Any]) -> None:
        """Notify the client to store authentication credentials.
        Credentials are passed on the next authenticate call.

        :param credentials: credentials that client will store; they are stored locally on a user pc

        Example use case of store_credentials:

        .. code-block:: python
            :linenos:

            async def pass_login_credentials(self, step, credentials, cookies):
                if self.got_everything(credentials,cookies):
                    user_data = await self.parse_credentials(credentials,cookies)
                else:
                    next_params = self.get_next_params(credentials,cookies)
                    next_cookies = self.get_next_cookies(credentials,cookies)
                    return NextStep("web_session", next_params, cookies=next_cookies)
                self.store_credentials(user_data['credentials'])
                return Authentication(user_data['userId'], user_data['username'])

        """
        # temporary solution for persistent_cache vs credentials issue
        self.persistent_cache["credentials"] = credentials  # type: ignore

        self._connection.send_notification("store_credentials", credentials, sensitive_params=True)

    def add_game(self, game: Game) -> None:
        """Notify the client to add game to the list of owned games
        of the currently authenticated user.

        :param game: Game to add to the list of owned games

        Example use case of add_game:

        .. code-block:: python
            :linenos:

            async def check_for_new_games(self):
                games = await self.get_owned_games()
                for game in games:
                    if game not in self.owned_games_cache:
                        self.owned_games_cache.append(game)
                        self.add_game(game)

        """
        params = {"owned_game": game}
        self._connection.send_notification("owned_game_added", params)

    def remove_game(self, game_id: str) -> None:
        """Notify the client to remove game from the list of owned games
        of the currently authenticated user.

        :param game_id: the id of the game to remove from the list of owned games

        Example use case of remove_game:

        .. code-block:: python
            :linenos:

            async def check_for_removed_games(self):
                games = await self.get_owned_games()
                for game in self.owned_games_cache:
                    if game not in games:
                        self.owned_games_cache.remove(game)
                        self.remove_game(game.game_id)

        """
        params = {"game_id": game_id}
        self._connection.send_notification("owned_game_removed", params)

    def update_game(self, game: Game) -> None:
        """Notify the client to update the status of a game
        owned by the currently authenticated user.

        :param game: Game to update
        """
        params = {"owned_game": game}
        self._connection.send_notification("owned_game_updated", params)

    def unlock_achievement(self, game_id: str, achievement: Achievement) -> None:
        """Notify the client to unlock an achievement for a specific game.

        :param game_id: the id of the game for which to unlock an achievement.
        :param achievement: achievement to unlock.
        """
        params = {
            "game_id": game_id,
            "achievement": achievement
        }
        self._connection.send_notification("achievement_unlocked", params)

    def _game_achievements_import_success(self, game_id: str, achievements: List[Achievement]) -> None:
        params = {
            "game_id": game_id,
            "unlocked_achievements": achievements
        }
        self._connection.send_notification("game_achievements_import_success", params)

    def _game_achievements_import_failure(self, game_id: str, error: ApplicationError) -> None:
        params = {
            "game_id": game_id,
            "error": error.json()
        }
        self._connection.send_notification("game_achievements_import_failure", params)

    def _achievements_import_finished(self) -> None:
        self._connection.send_notification("achievements_import_finished", None)

    def update_local_game_status(self, local_game: LocalGame) -> None:
        """Notify the client to update the status of a local game.

        :param local_game: the LocalGame to update

        Example use case triggered by the :meth:`.tick` method:

        .. code-block:: python
            :linenos:
            :emphasize-lines: 5

            async def _check_statuses(self):
                for game in await self._get_local_games():
                    if game.status == self._cached_game_statuses.get(game.id):
                        continue
                    self.update_local_game_status(LocalGame(game.id, game.status))
                    self._cached_games_statuses[game.id] = game.status
                await asyncio.sleep(5)  # interval

            def tick(self):
                if self._check_statuses_task is None or self._check_statuses_task.done():
                    self._check_statuses_task = asyncio.create_task(self._check_statuses())
        """
        params = {"local_game": local_game}
        self._connection.send_notification("local_game_status_changed", params)

    def add_friend(self, user: UserInfo) -> None:
        """Notify the client to add a user to friends list of the currently authenticated user.

        :param user: UserInfo of a user that the client will add to friends list
        """
        params = {"friend_info": user}
        self._connection.send_notification("friend_added", params)

    def remove_friend(self, user_id: str) -> None:
        """Notify the client to remove a user from friends list of the currently authenticated user.

        :param user_id: id of the user to remove from friends list
        """
        params = {"user_id": user_id}
        self._connection.send_notification("friend_removed", params)

    def update_friend_info(self, user: UserInfo) -> None:
        """Notify the client about the updated friend information.

        :param user: UserInfo of a friend whose info was updated
        """
        self._connection.send_notification("friend_updated", params={"friend_info": user})

    def update_game_time(self, game_time: GameTime) -> None:
        """Notify the client to update game time for a game.

        :param game_time: game time to update
        """
        params = {"game_time": game_time}
        self._connection.send_notification("game_time_updated", params)

    def update_user_presence(self, user_id: str, user_presence: UserPresence) -> None:
        """Notify the client about the updated user presence information.

        :param user_id: the id of the user whose presence information is updated
        :param user_presence: presence information of the specified user
        """
        self._connection.send_notification(
            "user_presence_updated",
            {
                "user_id": user_id,
                "presence": user_presence
            }
        )

    def _game_time_import_success(self, game_id: str, game_time: GameTime) -> None:
        params = {"game_time": game_time}
        self._connection.send_notification("game_time_import_success", params)

    def _game_time_import_failure(self, game_id: str, error: ApplicationError) -> None:
        params = {
            "game_id": game_id,
            "error": error.json()
        }
        self._connection.send_notification("game_time_import_failure", params)

    def _game_times_import_finished(self) -> None:
        self._connection.send_notification("game_times_import_finished", None)

    def _game_library_settings_import_success(self, game_id: str, game_library_settings: GameLibrarySettings) -> None:
        params = {"game_library_settings": game_library_settings}
        self._connection.send_notification("game_library_settings_import_success", params)

    def _game_library_settings_import_failure(self, game_id: str, error: ApplicationError) -> None:
        params = {
            "game_id": game_id,
            "error": error.json()
        }
        self._connection.send_notification("game_library_settings_import_failure", params)

    def _game_library_settings_import_finished(self) -> None:
        self._connection.send_notification("game_library_settings_import_finished", None)

    def _os_compatibility_import_success(self, game_id: str, os_compatibility: Optional[OSCompatibility]) -> None:
        self._connection.send_notification(
            "os_compatibility_import_success",
            {
                "game_id": game_id,
                "os_compatibility": os_compatibility
            }
        )

    def _os_compatibility_import_failure(self, game_id: str, error: ApplicationError) -> None:
        self._connection.send_notification(
            "os_compatibility_import_failure",
            {
                "game_id": game_id,
                "error": error.json()
            }
        )

    def _os_compatibility_import_finished(self) -> None:
        self._connection.send_notification("os_compatibility_import_finished", None)

    def _user_presence_import_success(self, user_id: str, user_presence: UserPresence) -> None:
        self._connection.send_notification(
            "user_presence_import_success",
            {
                "user_id": user_id,
                "presence": user_presence
            }
        )

    def _user_presence_import_failure(self, user_id: str, error: ApplicationError) -> None:
        self._connection.send_notification(
            "user_presence_import_failure",
            {
                "user_id": user_id,
                "error": error.json()
            }
        )

    def _user_presence_import_finished(self) -> None:
        self._connection.send_notification("user_presence_import_finished", None)

    def _local_size_import_success(self, game_id: str, size: Optional[int]) -> None:
        self._connection.send_notification(
            "local_size_import_success",
            {
                "game_id": game_id,
                "local_size": size
            }
        )

    def _local_size_import_failure(self, game_id: str, error: ApplicationError) -> None:
        self._connection.send_notification(
            "local_size_import_failure",
            {
                "game_id": game_id,
                "error": error.json()
            }
        )

    def _local_size_import_finished(self) -> None:
        self._connection.send_notification("local_size_import_finished", None)

    def _subscription_games_import_success(self, subscription_name: str,
                                           subscription_games: Optional[List[SubscriptionGame]]) -> None:
        self._connection.send_notification(
            "subscription_games_import_success",
            {
                "subscription_name": subscription_name,
                "subscription_games": subscription_games
            }
        )

    def _subscription_games_import_failure(self, subscription_name: str, error: ApplicationError) -> None:
        self._connection.send_notification(
            "subscription_games_import_failure",
            {
                "subscription_name": subscription_name,
                "error": error.json()
            }
        )

    def _subscriptions_games_partial_import_finished(self, subscription_name: str) -> None:
        self._connection.send_notification(
            "subscription_games_partial_import_finished",
            {
               "subscription_name": subscription_name
            }
        )

    def _subscription_games_import_finished(self) -> None:
        self._connection.send_notification("subscription_games_import_finished", None)

    def lost_authentication(self) -> None:
        """Notify the client that integration has lost authentication for the
         current user and is unable to perform actions which would require it.
         """
        self._connection.send_notification("authentication_lost", None)

    def push_cache(self) -> None:
        """Push local copy of the persistent cache to the GOG Galaxy Client replacing existing one.
        """
        self._connection.send_notification(
            "push_cache",
            params={"data": self._persistent_cache},
            sensitive_params="data"
        )

    async def refresh_credentials(self, params: Dict[str, Any], sensitive_params) -> Dict[str, Any]:
        return await self._connection.send_request("refresh_credentials", params, sensitive_params)

    # handlers
    def handshake_complete(self) -> None:
        """This method is called right after the handshake with the GOG Galaxy Client is complete and
        before any other operations are called by the GOG Galaxy Client.
        Persistent cache is available when this method is called.
        Override it if you need to do additional plugin initializations.
        This method is called internally."""

    def tick(self) -> None:
        """This method is called periodically.
        Override it to implement periodical non-blocking tasks.
        This method is called internally.

        Example of possible override of the method:

        .. code-block:: python
            :linenos:

            def tick(self):
                if not self.checking_for_new_games:
                    asyncio.create_task(self.check_for_new_games())
                if not self.checking_for_removed_games:
                    asyncio.create_task(self.check_for_removed_games())
                if not self.updating_game_statuses:
                    asyncio.create_task(self.update_game_statuses())

        """

    async def shutdown(self) -> None:
        """This method is called on integration shutdown.
        Override it to implement tear down.
        This method is called by the GOG Galaxy Client."""

    # methods
    async def authenticate(self, stored_credentials: Optional[Dict] = None) -> Union[NextStep, Authentication]:
        """Override this method to handle user authentication.
        This method should either return :class:`~galaxy.api.types.Authentication` if the authentication is finished
        or :class:`~galaxy.api.types.NextStep` if it requires going to another url.
        This method is called by the GOG Galaxy Client.

        :param stored_credentials: If the client received any credentials to store locally
            in the previous session they will be passed here as a parameter.


        Example of possible override of the method:

        .. code-block:: python
            :linenos:

            async def authenticate(self, stored_credentials=None):
                if not stored_credentials:
                    return NextStep("web_session", PARAMS, cookies=COOKIES)
                else:
                    try:
                        user_data = self._authenticate(stored_credentials)
                    except AccessDenied:
                        raise InvalidCredentials()
                return Authentication(user_data['userId'], user_data['username'])

        """
        raise NotImplementedError()

    async def pass_login_credentials(self, step: str, credentials: Dict[str, str], cookies: List[Dict[str, str]]) \
            -> Union[NextStep, Authentication]:
        """This method is called if we return :class:`~galaxy.api.types.NextStep` from :meth:`.authenticate`
        or :meth:`.pass_login_credentials`.
        This method's parameters provide the data extracted from the web page navigation that previous NextStep finished on.
        This method should either return :class:`~galaxy.api.types.Authentication` if the authentication is finished
        or :class:`~galaxy.api.types.NextStep` if it requires going to another cef url.
        This method is called by the GOG Galaxy Client.

        :param step: deprecated.
        :param credentials: end_uri previous NextStep finished on.
        :param cookies: cookies extracted from the end_uri site.

        Example of possible override of the method:

        .. code-block:: python
            :linenos:

            async def pass_login_credentials(self, step, credentials, cookies):
                if self.got_everything(credentials,cookies):
                    user_data = await self.parse_credentials(credentials,cookies)
                else:
                    next_params = self.get_next_params(credentials,cookies)
                    next_cookies = self.get_next_cookies(credentials,cookies)
                    return NextStep("web_session", next_params, cookies=next_cookies)
                self.store_credentials(user_data['credentials'])
                return Authentication(user_data['userId'], user_data['username'])

        """
        raise NotImplementedError()

    async def get_owned_games(self) -> List[Game]:
        """Override this method to return owned games for currently logged in user.
        This method is called by the GOG Galaxy Client.

        Example of possible override of the method:

        .. code-block:: python
            :linenos:

            async def get_owned_games(self):
                if not self.authenticated():
                    raise AuthenticationRequired()

                games = self.retrieve_owned_games()
                return games

        """
        raise NotImplementedError()

    async def _start_achievements_import(self, game_ids: List[str]) -> None:
        await self._achievements_importer.start(game_ids)

    async def prepare_achievements_context(self, game_ids: List[str]) -> Any:
        """Override this method to prepare context for get_unlocked_achievements.
        This allows for optimizations like batch requests to platform API.
        Default implementation returns None.

        :param game_ids: the ids of the games for which achievements are imported
        :return: context
        """
        return None

    async def get_unlocked_achievements(self, game_id: str, context: Any) -> List[Achievement]:
        """Override this method to return list of unlocked achievements
        for the game identified by the provided game_id.
        This method is called by import task initialized by GOG Galaxy Client.

        :param game_id: the id of the game for which the achievements are returned
        :param context: the value returned from :meth:`prepare_achievements_context`
        :return: list of Achievement objects
        """
        raise NotImplementedError()

    def achievements_import_complete(self):
        """Override this method to handle operations after achievements import is finished
        (like updating cache).
        """

    async def get_local_games(self) -> List[LocalGame]:
        """Override this method to return the list of
        games present locally on the users pc.
        This method is called by the GOG Galaxy Client.

        Example of possible override of the method:

        .. code-block:: python
            :linenos:

            async def get_local_games(self):
                local_games = []
                for game in self.games_present_on_user_pc:
                    local_game = LocalGame()
                    local_game.game_id = game.id
                    local_game.local_game_state = game.get_installation_status()
                    local_games.append(local_game)
                return local_games

        """
        raise NotImplementedError()

    async def launch_game(self, game_id: str) -> None:
        """Override this method to launch the game
        identified by the provided game_id.
        This method is called by the GOG Galaxy Client.

        :param str game_id: the id of the game to launch

        Example of possible override of the method:

        .. code-block:: python
            :linenos:

            async def launch_game(self, game_id):
                await self.open_uri(f"start client://launchgame/{game_id}")

        """
        raise NotImplementedError()

    async def install_game(self, game_id: str) -> None:
        """Override this method to install the game
        identified by the provided game_id.
        This method is called by the GOG Galaxy Client.

        :param str game_id: the id of the game to install

        Example of possible override of the method:

        .. code-block:: python
            :linenos:

            async def install_game(self, game_id):
                await self.open_uri(f"start client://installgame/{game_id}")

        """
        raise NotImplementedError()

    async def uninstall_game(self, game_id: str) -> None:
        """Override this method to uninstall the game
        identified by the provided game_id.
        This method is called by the GOG Galaxy Client.

        :param str game_id: the id of the game to uninstall

        Example of possible override of the method:

        .. code-block:: python
            :linenos:

            async def uninstall_game(self, game_id):
                await self.open_uri(f"start client://uninstallgame/{game_id}")

        """
        raise NotImplementedError()

    async def shutdown_platform_client(self) -> None:
        """Override this method to gracefully terminate platform client.
        This method is called by the GOG Galaxy Client."""
        raise NotImplementedError()

    async def launch_platform_client(self) -> None:
        """Override this method to launch platform client. Preferably minimized to tray.
        This method is called by the GOG Galaxy Client."""
        raise NotImplementedError()

    async def get_friends(self) -> List[UserInfo]:
        """Override this method to return the friends list
        of the currently authenticated user.
        This method is called by the GOG Galaxy Client.

        Example of possible override of the method:

        .. code-block:: python
            :linenos:

            async def get_friends(self):
                if not self._http_client.is_authenticated():
                    raise AuthenticationRequired()

                friends = self.retrieve_friends()
                return friends

        """
        raise NotImplementedError()

    async def _start_game_times_import(self, game_ids: List[str]) -> None:
        await self._game_time_importer.start(game_ids)

    async def prepare_game_times_context(self, game_ids: List[str]) -> Any:
        """Override this method to prepare context for get_game_time.
        This allows for optimizations like batch requests to platform API.
        Default implementation returns None.

        :param game_ids: the ids of the games for which game time are imported
        :return: context
        """
        return None

    async def get_game_time(self, game_id: str, context: Any) -> GameTime:
        """Override this method to return the game time for the game
        identified by the provided game_id.
        This method is called by import task initialized by GOG Galaxy Client.

        :param game_id: the id of the game for which the game time is returned
        :param context: the value returned from :meth:`prepare_game_times_context`
        :return: GameTime object
        """
        raise NotImplementedError()

    def game_times_import_complete(self) -> None:
        """Override this method to handle operations after game times import is finished
        (like updating cache).
        """

    async def _start_game_library_settings_import(self, game_ids: List[str]) -> None:
        await self._game_library_settings_importer.start(game_ids)

    async def prepare_game_library_settings_context(self, game_ids: List[str]) -> Any:
        """Override this method to prepare context for get_game_library_settings.
        This allows for optimizations like batch requests to platform API.
        Default implementation returns None.

        :param game_ids: the ids of the games for which game library settings are imported
        :return: context
        """
        return None

    async def get_game_library_settings(self, game_id: str, context: Any) -> GameLibrarySettings:
        """Override this method to return the game library settings for the game
        identified by the provided game_id.
        This method is called by import task initialized by GOG Galaxy Client.

        :param game_id: the id of the game for which the game library settings are imported
        :param context: the value returned from :meth:`prepare_game_library_settings_context`
        :return: GameLibrarySettings object
        """
        raise NotImplementedError()

    def game_library_settings_import_complete(self) -> None:
        """Override this method to handle operations after game library settings import is finished
        (like updating cache).
        """

    async def _start_os_compatibility_import(self, game_ids: List[str]) -> None:
        await self._os_compatibility_importer.start(game_ids)

    async def prepare_os_compatibility_context(self, game_ids: List[str]) -> Any:
        """Override this method to prepare context for get_os_compatibility.
        This allows for optimizations like batch requests to platform API.
        Default implementation returns None.

        :param game_ids: the ids of the games for which game os compatibility is imported
        :return: context
        """
        return None

    async def get_os_compatibility(self, game_id: str, context: Any) -> Optional[OSCompatibility]:
        """Override this method to return the OS compatibility for the game with the provided game_id.
        This method is called by import task initialized by GOG Galaxy Client.

        :param game_id: the id of the game for which the game os compatibility is imported
        :param context: the value returned from :meth:`prepare_os_compatibility_context`
        :return: OSCompatibility flags indicating compatible OSs, or None if compatibility is not know
        """
        raise NotImplementedError()

    def os_compatibility_import_complete(self) -> None:
        """Override this method to handle operations after OS compatibility import is finished (like updating cache)."""

    async def _start_user_presence_import(self, user_id_list: List[str]) -> None:
        await self._user_presence_importer.start(user_id_list)

    async def prepare_user_presence_context(self, user_id_list: List[str]) -> Any:
        """Override this method to prepare context for :meth:`get_user_presence`.
        This allows for optimizations like batch requests to platform API.
        Default implementation returns None.

        :param user_id_list: the ids of the users for whom presence information is imported
        :return: context
        """
        return None

    async def get_user_presence(self, user_id: str, context: Any) -> UserPresence:
        """Override this method to return presence information for the user with the provided user_id.
        This method is called by import task initialized by GOG Galaxy Client.

        :param user_id: the id of the user for whom presence information is imported
        :param context: the value returned from :meth:`prepare_user_presence_context`
        :return: UserPresence presence information of the provided user
        """
        raise NotImplementedError()

    def user_presence_import_complete(self) -> None:
        """Override this method to handle operations after presence import is finished (like updating cache)."""

    async def _start_local_size_import(self, game_ids: List[str]) -> None:
        await self._local_size_importer.start(game_ids)

    async def prepare_local_size_context(self, game_ids: List[str]) -> Any:
        """Override this method to prepare context for :meth:`get_local_size`
        Default implementation returns None.

        :param game_ids: the ids of the games for which information about size is imported
        :return: context
        """
        return None

    async def get_local_size(self, game_id: str, context: Any) -> Optional[int]:
        """Override this method to return installed game size.

        .. note::
          It is preferable to avoid iterating over local game files when overriding this method.
          If possible, please use a more efficient way of game size retrieval.

        :param game_id: the id of the installed game
        :param context: the value returned from :meth:`prepare_local_size_context`
        :return: the size of the game on a user-owned storage device (in bytes) or `None` if the size cannot be determined
        """
        raise NotImplementedError()

    def local_size_import_complete(self) -> None:
        """Override this method to handle operations after local game size import is finished (like updating cache)."""

    async def get_subscriptions(self) -> List[Subscription]:
        """Override this method to return a list of
        Subscriptions available on platform.
        This method is called by the GOG Galaxy Client.
        """
        raise NotImplementedError()

    async def _start_subscription_games_import(self, subscription_names: List[str]) -> None:
        await self._subscription_games_importer.start(subscription_names)

    async def prepare_subscription_games_context(self, subscription_names: List[str]) -> Any:
        """Override this method to prepare context for :meth:`get_subscription_games`
        Default implementation returns None.

        :param subscription_names: the names of the subscriptions' for which subscriptions games are imported
        :return: context
        """
        return None

    async def get_subscription_games(self, subscription_name: str, context: Any) -> AsyncGenerator[
        List[SubscriptionGame], None]:
        """Override this method to provide SubscriptionGames for a given subscription.
        This method should `yield` a list of SubscriptionGames -> yield [sub_games]

        This method will only be used if :meth:`get_subscriptions` has been implemented.

        :param context: the value returned from :meth:`prepare_subscription_games_context`
        :return a generator object that yields SubscriptionGames

        .. code-block:: python
            :linenos:

            async def get_subscription_games(subscription_name: str, context: Any):
                while True:
                    games_page = await self._get_subscriptions_from_backend(subscription_name, i)
                    if not games_pages:
                        yield None
                    yield [SubGame(game['game_id'], game['game_title']) for game in games_page]

        """
        raise NotImplementedError()

    def subscription_games_import_complete(self) -> None:
        """Override this method to handle operations after
        subscription games import is finished (like updating cache).
        """


def create_and_run_plugin(plugin_class, argv):
    """Call this method as an entry point for the implemented integration.

    :param plugin_class: your plugin class.
    :param argv: command line arguments with which the script was started.

    Example of possible use of the method:

    .. code-block:: python
            :linenos:

            def main():
                create_and_run_plugin(PlatformPlugin, sys.argv)

            if __name__ == "__main__":
                main()
    """
    if len(argv) < 3:
        logger.critical("Not enough parameters, required: token, port")
        sys.exit(1)

    token = argv[1]

    try:
        port = int(argv[2])
    except ValueError:
        logger.critical("Failed to parse port value: %s", argv[2])
        sys.exit(2)

    if not (1 <= port <= 65535):
        logger.critical("Port value out of range (1, 65535)")
        sys.exit(3)

    if not issubclass(plugin_class, Plugin):
        logger.critical("plugin_class must be subclass of Plugin")
        sys.exit(4)

    async def coroutine():
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        try:
            extra_info = writer.get_extra_info("sockname")
            logger.info("Using local address: %s:%u", *extra_info)
            async with plugin_class(reader, writer, token) as plugin:
                await plugin.run()
        finally:
            writer.close()
            await writer.wait_closed()

    try:
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        asyncio.run(coroutine())
    except Exception:
        logger.exception("Error while running plugin")
        sys.exit(5)

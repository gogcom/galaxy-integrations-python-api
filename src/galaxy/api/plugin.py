import asyncio
import json
import logging
import logging.handlers
import dataclasses
from enum import Enum
from collections import OrderedDict
import sys

from typing import Any, List, Dict, Optional, Union

from galaxy.api.types import Achievement, Game, LocalGame, FriendInfo, GameTime, UserInfo, Room

from galaxy.api.jsonrpc import Server, NotificationClient, ApplicationError
from galaxy.api.consts import Feature
from galaxy.api.errors import UnknownError, ImportInProgress
from galaxy.api.types import Authentication, NextStep, Message


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
        logging.info("Creating plugin for platform %s, version %s", platform.value, version)
        self._platform = platform
        self._version = version

        self._feature_methods = OrderedDict()
        self._active = True
        self._pass_control_task = None

        self._reader, self._writer = reader, writer
        self._handshake_token = handshake_token

        encoder = JSONEncoder()
        self._server = Server(self._reader, self._writer, encoder)
        self._notification_client = NotificationClient(self._writer, encoder)

        def eof_handler():
            self._shutdown()
        self._server.register_eof(eof_handler)

        self._achievements_import_in_progress = False
        self._game_times_import_in_progress = False

        self._persistent_cache = dict()

        # internal
        self._register_method("shutdown", self._shutdown, internal=True)
        self._register_method("get_capabilities", self._get_capabilities, internal=True)
        self._register_method(
            "initialize_cache",
            self._initialize_cache,
            internal=True,
            sensitive_params="data"
        )
        self._register_method("ping", self._ping, internal=True)

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
            result_name="owned_games",
            feature=Feature.ImportOwnedGames
        )
        self._register_method(
            "import_unlocked_achievements",
            self.get_unlocked_achievements,
            result_name="unlocked_achievements",
            feature=Feature.ImportAchievements
        )
        self._register_method(
            "start_achievements_import",
            self.start_achievements_import,
        )
        self._register_method(
            "import_local_games",
            self.get_local_games,
            result_name="local_games",
            feature=Feature.ImportInstalledGames
        )
        self._register_notification("launch_game", self.launch_game, feature=Feature.LaunchGame)
        self._register_notification("install_game", self.install_game, feature=Feature.InstallGame)
        self._register_notification(
            "uninstall_game",
            self.uninstall_game,
            feature=Feature.UninstallGame
        )
        self._register_method(
            "import_friends",
            self.get_friends,
            result_name="friend_info_list",
            feature=Feature.ImportFriends
        )
        self._register_method(
            "import_user_infos",
            self.get_users,
            result_name="user_info_list",
            feature=Feature.ImportUsers
        )
        self._register_method(
            "send_message",
            self.send_message,
            feature=Feature.Chat
        )
        self._register_method(
            "mark_as_read",
            self.mark_as_read,
            feature=Feature.Chat
        )
        self._register_method(
            "import_rooms",
            self.get_rooms,
            result_name="rooms",
            feature=Feature.Chat
        )
        self._register_method(
            "import_room_history_from_message",
            self.get_room_history_from_message,
            result_name="messages",
            feature=Feature.Chat
        )
        self._register_method(
            "import_room_history_from_timestamp",
            self.get_room_history_from_timestamp,
            result_name="messages",
            feature=Feature.Chat
        )
        self._register_method(
            "import_game_times",
            self.get_game_times,
            result_name="game_times",
            feature=Feature.ImportGameTime
        )
        self._register_method(
            "start_game_times_import",
            self.start_game_times_import,
        )

    @property
    def features(self):
        features = []
        if self.__class__ != Plugin:
            for feature, handlers in self._feature_methods.items():
                if self._implements(handlers):
                    features.append(feature)

        return features

    @property
    def persistent_cache(self) -> Dict:
        """The cache is only available after the :meth:`~.handshake_complete()` is called.
        """
        return self._persistent_cache

    def _implements(self, handlers):
        for handler in handlers:
            if handler.__name__ not in self.__class__.__dict__:
                return False
        return True

    def _register_method(self, name, handler, result_name=None, internal=False, sensitive_params=False, feature=None):
        if internal:
            def method(*args, **kwargs):
                result = handler(*args, **kwargs)
                if result_name:
                    result = {
                        result_name: result
                    }
                return result
            self._server.register_method(name, method, True, sensitive_params)
        else:
            async def method(*args, **kwargs):
                result = await handler(*args, **kwargs)
                if result_name:
                    result = {
                        result_name: result
                    }
                return result
            self._server.register_method(name, method, False, sensitive_params)

        if feature is not None:
            self._feature_methods.setdefault(feature, []).append(handler)

    def _register_notification(self, name, handler, internal=False, sensitive_params=False, feature=None):
        self._server.register_notification(name, handler, internal, sensitive_params)

        if feature is not None:
            self._feature_methods.setdefault(feature, []).append(handler)

    async def run(self):
        """Plugin's main coroutine."""
        await self._server.run()
        if self._pass_control_task is not None:
            await self._pass_control_task

    async def _pass_control(self):
        while self._active:
            try:
                self.tick()
            except Exception:
                logging.exception("Unexpected exception raised in plugin tick")
            await asyncio.sleep(1)

    def _shutdown(self):
        logging.info("Shutting down")
        self._server.stop()
        self._active = False
        self.shutdown()

    def _get_capabilities(self):
        return {
            "platform_name": self._platform,
            "features": self.features,
            "token": self._handshake_token
        }

    def _initialize_cache(self, data: Dict):
        self._persistent_cache = data
        self.handshake_complete()
        self._pass_control_task = asyncio.create_task(self._pass_control())

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
        self.persistent_cache['credentials'] = credentials
        self._notification_client.notify("store_credentials", credentials, sensitive_params=True)

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
        self._notification_client.notify("owned_game_added", params)

    def remove_game(self, game_id: str) -> None:
        """Notify the client to remove game from the list of owned games
        of the currently authenticated user.

        :param game_id: game id of the game to remove from the list of owned games

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
        self._notification_client.notify("owned_game_removed", params)

    def update_game(self, game: Game) -> None:
        """Notify the client to update the status of a game
        owned by the currently authenticated user.

        :param game: Game to update
        """
        params = {"owned_game": game}
        self._notification_client.notify("owned_game_updated", params)

    def unlock_achievement(self, game_id: str, achievement: Achievement) -> None:
        """Notify the client to unlock an achievement for a specific game.

        :param game_id: game_id of the game for which to unlock an achievement.
        :param achievement: achievement to unlock.
        """
        params = {
            "game_id": game_id,
            "achievement": achievement
        }
        self._notification_client.notify("achievement_unlocked", params)

    def game_achievements_import_success(self, game_id: str, achievements: List[Achievement]) -> None:
        """Notify the client that import of achievements for a given game has succeeded.
        This method is called by import_games_achievements.

        :param game_id: id of the game for which the achievements were imported
        :param achievements: list of imported achievements
        """
        params = {
            "game_id": game_id,
            "unlocked_achievements": achievements
        }
        self._notification_client.notify("game_achievements_import_success", params)

    def game_achievements_import_failure(self, game_id: str, error: ApplicationError) -> None:
        """Notify the client that import of achievements for a given game has failed.
        This method is called by import_games_achievements.

        :param game_id: id of the game for which the achievements import failed
        :param error: error which prevented the achievements import
        """
        params = {
            "game_id": game_id,
            "error": {
                "code": error.code,
                "message": error.message
            }
        }
        self._notification_client.notify("game_achievements_import_failure", params)

    def achievements_import_finished(self) -> None:
        """Notify the client that importing achievements has finished.
        This method is called by import_games_achievements_task"""
        self._notification_client.notify("achievements_import_finished", None)

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
                asyncio.sleep(5)  # interval

            def tick(self):
                if self._check_statuses_task is None or self._check_statuses_task.done():
                    self._check_statuses_task = asyncio.create_task(self._check_statuses())
        """
        params = {"local_game": local_game}
        self._notification_client.notify("local_game_status_changed", params)

    def add_friend(self, user: FriendInfo) -> None:
        """Notify the client to add a user to friends list of the currently authenticated user.

        :param user: FriendInfo of a user that the client will add to friends list
        """
        params = {"friend_info": user}
        self._notification_client.notify("friend_added", params)

    def remove_friend(self, user_id: str) -> None:
        """Notify the client to remove a user from friends list of the currently authenticated user.

        :param user_id: id of the user to remove from friends list
        """
        params = {"user_id": user_id}
        self._notification_client.notify("friend_removed", params)

    def update_room(
        self,
        room_id: str,
        unread_message_count: Optional[int]=None,
        new_messages: Optional[List[Message]]=None
    ) -> None:
        """WIP, Notify the client to update the information regarding
        a chat room that the currently authenticated user is in.

        :param room_id: id of the room to update
        :param unread_message_count: information about the new unread message count in the room
        :param new_messages: list of new messages that the user received
        """
        params = {"room_id": room_id}
        if unread_message_count is not None:
            params["unread_message_count"] = unread_message_count
        if new_messages is not None:
            params["messages"] = new_messages
        self._notification_client.notify("chat_room_updated", params)

    def update_game_time(self, game_time: GameTime) -> None:
        """Notify the client to update game time for a game.

        :param game_time: game time to update
        """
        params = {"game_time": game_time}
        self._notification_client.notify("game_time_updated", params)

    def game_time_import_success(self, game_time: GameTime) -> None:
        """Notify the client that import of a given game_time has succeeded.
        This method is called by import_game_times.

        :param game_time: game_time which was imported
        """
        params = {"game_time": game_time}
        self._notification_client.notify("game_time_import_success", params)

    def game_time_import_failure(self, game_id: str, error: ApplicationError) -> None:
        """Notify the client that import of a game time for a given game has failed.
        This method is called by import_game_times.

        :param game_id: id of the game for which the game time could not be imported
        :param error:   error which prevented the game time import
        """
        params = {
            "game_id": game_id,
            "error": {
                "code": error.code,
                "message": error.message
            }
        }
        self._notification_client.notify("game_time_import_failure", params)

    def game_times_import_finished(self) -> None:
        """Notify the client that importing game times has finished.
        This method is called by :meth:`~.import_game_times_task`.
        """
        self._notification_client.notify("game_times_import_finished", None)

    def lost_authentication(self) -> None:
        """Notify the client that integration has lost authentication for the
         current user and is unable to perform actions which would require it.
         """
        self._notification_client.notify("authentication_lost", None)

    def push_cache(self) -> None:
        """Push local copy of the persistent cache to the GOG Galaxy Client replacing existing one.
        """
        self._notification_client.notify(
            "push_cache",
            params={"data": self._persistent_cache},
            sensitive_params="data"
        )

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

    def shutdown(self) -> None:
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
        """This method is called if we return galaxy.api.types.NextStep from authenticate or from pass_login_credentials.
        This method's parameters provide the data extracted from the web page navigation that previous NextStep finished on.
        This method should either return galaxy.api.types.Authentication if the authentication is finished
        or galaxy.api.types.NextStep if it requires going to another cef url.
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

    async def get_unlocked_achievements(self, game_id: str) -> List[Achievement]:
        """
        .. deprecated:: 0.33
            Use :meth:`~.import_games_achievements`.
        """
        raise NotImplementedError()

    async def start_achievements_import(self, game_ids: List[str]) -> None:
        """Starts the task of importing achievements.
        This method is called by the GOG Galaxy Client.

        :param game_ids: ids of the games for which the achievements are imported
        """
        if self._achievements_import_in_progress:
            raise ImportInProgress()

        async def import_games_achievements_task(game_ids):
            try:
                await self.import_games_achievements(game_ids)
            finally:
                self.achievements_import_finished()
                self._achievements_import_in_progress = False

        asyncio.create_task(import_games_achievements_task(game_ids))
        self._achievements_import_in_progress = True

    async def import_games_achievements(self, game_ids: List[str]) -> None:
        """
        Override this method to return the unlocked achievements
        of the user that is currently logged in to the plugin.
        Call game_achievements_import_success/game_achievements_import_failure for each game_id on the list.
        This method is called by the GOG Galaxy Client.

        :param game_ids: ids of the games for which to import unlocked achievements
        """
        async def import_game_achievements(game_id):
            try:
                achievements = await self.get_unlocked_achievements(game_id)
                self.game_achievements_import_success(game_id, achievements)
            except Exception as error:
                self.game_achievements_import_failure(game_id, error)

        imports = [import_game_achievements(game_id) for game_id in game_ids]
        await asyncio.gather(*imports)

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

        :param str game_id: id of the game to launch

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

        :param str game_id: id of the game to install

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

        :param str game_id: id of the game to uninstall

        Example of possible override of the method:

        .. code-block:: python
            :linenos:

            async def uninstall_game(self, game_id):
                await self.open_uri(f"start client://uninstallgame/{game_id}")

        """
        raise NotImplementedError()

    async def get_friends(self) -> List[FriendInfo]:
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

    async def get_users(self, user_id_list: List[str]) -> List[UserInfo]:
        """WIP, Override this method to return the list of users matching the provided ids.
        This method is called by the GOG Galaxy Client.

        :param user_id_list: list of user ids
        """
        raise NotImplementedError()

    async def send_message(self, room_id: str, message_text: str) -> None:
        """WIP, Override this method to send message to a chat room.
         This method is called by the GOG Galaxy Client.

         :param room_id: id of the room to which the message should be sent
         :param message_text: text which should be sent in the message
         """
        raise NotImplementedError()

    async def mark_as_read(self, room_id: str, last_message_id: str) -> None:
        """WIP, Override this method to mark messages in a chat room as read up to the id provided in the parameter.
        This method is called by the GOG Galaxy Client.

        :param room_id: id of the room
        :param last_message_id: id of the last message; room is marked as read only if this id matches
         the last message id known to the client
        """
        raise NotImplementedError()

    async def get_rooms(self) -> List[Room]:
        """WIP, Override this method to return the chat rooms in which the user is currently in.
        This method is called by the GOG Galaxy Client
        """
        raise NotImplementedError()

    async def get_room_history_from_message(self, room_id: str, message_id: str) -> List[Message]:
        """WIP, Override this method to return the chat room history since the message provided in parameter.
        This method is called by the GOG Galaxy Client.

        :param room_id: id of the room
        :param message_id: id of the message since which the history should be retrieved
        """
        raise NotImplementedError()

    async def get_room_history_from_timestamp(self, room_id: str, from_timestamp: int) -> List[Message]:
        """WIP, Override this method to return the chat room history since the timestamp provided in parameter.
        This method is called by the GOG Galaxy Client.

        :param room_id: id of the room
        :param from_timestamp: timestamp since which the history should be retrieved
        """
        raise NotImplementedError()

    async def get_game_times(self) -> List[GameTime]:
        """
        .. deprecated:: 0.33
            Use :meth:`~.import_game_times`.
        """
        raise NotImplementedError()

    async def start_game_times_import(self, game_ids: List[str]) -> None:
        """Starts the task of importing game times
        This method is called by the GOG Galaxy Client.

        :param game_ids: ids of the games for which the game time is imported
        """
        if self._game_times_import_in_progress:
            raise ImportInProgress()

        async def import_game_times_task(game_ids):
            try:
                await self.import_game_times(game_ids)
            finally:
                self.game_times_import_finished()
                self._game_times_import_in_progress = False

        asyncio.create_task(import_game_times_task(game_ids))
        self._game_times_import_in_progress = True

    async def import_game_times(self, game_ids: List[str]) -> None:
        """
        Override this method to return game times for
        games owned by the currently authenticated user.
        Call game_time_import_success/game_time_import_failure for each game_id on the list.
        This method is called by GOG Galaxy Client.

        :param game_ids: ids of the games for which the game time is imported
        """
        try:
            game_times = await self.get_game_times()
            game_ids_set = set(game_ids)
            for game_time in game_times:
                if game_time.game_id not in game_ids_set:
                    continue
                self.game_time_import_success(game_time)
                game_ids_set.discard(game_time.game_id)
            for game_id in game_ids_set:
                self.game_time_import_failure(game_id, UnknownError())
        except Exception as error:
            for game_id in game_ids:
                self.game_time_import_failure(game_id, error)


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
        logging.critical("Not enough parameters, required: token, port")
        sys.exit(1)

    token = argv[1]

    try:
        port = int(argv[2])
    except ValueError:
        logging.critical("Failed to parse port value: %s", argv[2])
        sys.exit(2)

    if not (1 <= port <= 65535):
        logging.critical("Port value out of range (1, 65535)")
        sys.exit(3)

    if not issubclass(plugin_class, Plugin):
        logging.critical("plugin_class must be subclass of Plugin")
        sys.exit(4)

    async def coroutine():
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        extra_info = writer.get_extra_info("sockname")
        logging.info("Using local address: %s:%u", *extra_info)
        plugin = plugin_class(reader, writer, token)
        await plugin.run()

    try:
        asyncio.run(coroutine())
    except Exception:
        logging.exception("Error while running plugin")
        sys.exit(5)

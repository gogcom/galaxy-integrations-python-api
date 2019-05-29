import asyncio
import json
import logging
import logging.handlers
import dataclasses
from enum import Enum
from collections import OrderedDict
import sys

from galaxy.api.jsonrpc import Server, NotificationClient
from galaxy.api.consts import Feature
from galaxy.api.errors import UnknownError, ImportInProgress

class JSONEncoder(json.JSONEncoder):
    def default(self, o): # pylint: disable=method-hidden
        if dataclasses.is_dataclass(o):
            # filter None values
            def dict_factory(elements):
                return {k: v for k, v in elements if v is not None}
            return dataclasses.asdict(o, dict_factory=dict_factory)
        if isinstance(o, Enum):
            return o.value
        return super().default(o)

class Plugin():
    def __init__(self, platform, version, reader, writer, handshake_token):
        logging.info("Creating plugin for platform %s, version %s", platform.value, version)
        self._platform = platform
        self._version = version

        self._feature_methods = OrderedDict()
        self._active = True

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

        # internal
        self._register_method("shutdown", self._shutdown, internal=True)
        self._register_method("get_capabilities", self._get_capabilities, internal=True)
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
        """Plugin main coorutine"""
        async def pass_control():
            while self._active:
                try:
                    self.tick()
                except Exception:
                    logging.exception("Unexpected exception raised in plugin tick")
                await asyncio.sleep(1)

        await asyncio.gather(pass_control(), self._server.run())

    def _shutdown(self):
        logging.info("Shuting down")
        self._server.stop()
        self._active = False
        self.shutdown()

    def _get_capabilities(self):
        return {
            "platform_name": self._platform,
            "features": self.features,
            "token": self._handshake_token
        }

    @staticmethod
    def _ping():
        pass

    # notifications
    def store_credentials(self, credentials):
        """Notify client to store plugin credentials.
        They will be pass to next authencicate calls.
        """
        self._notification_client.notify("store_credentials", credentials, sensitive_params=True)

    def add_game(self, game):
        params = {"owned_game" : game}
        self._notification_client.notify("owned_game_added", params)

    def remove_game(self, game_id):
        params = {"game_id" : game_id}
        self._notification_client.notify("owned_game_removed", params)

    def update_game(self, game):
        params = {"owned_game" : game}
        self._notification_client.notify("owned_game_updated", params)

    def unlock_achievement(self, game_id, achievement):
        params = {
            "game_id": game_id,
            "achievement": achievement
        }
        self._notification_client.notify("achievement_unlocked", params)

    def game_achievements_import_success(self, game_id, achievements):
        params = {
            "game_id": game_id,
            "unlocked_achievements": achievements
        }
        self._notification_client.notify("game_achievements_import_success", params)

    def game_achievements_import_failure(self, game_id, error):
        params = {
            "game_id": game_id,
            "error": {
                "code": error.code,
                "message": error.message
            }
        }
        self._notification_client.notify("game_achievements_import_failure", params)

    def achievements_import_finished(self):
        self._notification_client.notify("achievements_import_finished", None)

    def update_local_game_status(self, local_game):
        params = {"local_game" : local_game}
        self._notification_client.notify("local_game_status_changed", params)

    def add_friend(self, user):
        params = {"friend_info" : user}
        self._notification_client.notify("friend_added", params)

    def remove_friend(self, user_id):
        params = {"user_id" : user_id}
        self._notification_client.notify("friend_removed", params)

    def update_room(self, room_id, unread_message_count=None, new_messages=None):
        params = {"room_id": room_id}
        if unread_message_count is not None:
            params["unread_message_count"] = unread_message_count
        if new_messages is not None:
            params["messages"] = new_messages
        self._notification_client.notify("chat_room_updated", params)

    def update_game_time(self, game_time):
        params = {"game_time" : game_time}
        self._notification_client.notify("game_time_updated", params)

    def game_time_import_success(self, game_time):
        params = {"game_time" : game_time}
        self._notification_client.notify("game_time_import_success", params)

    def game_time_import_failure(self, game_id, error):
        params = {
            "game_id": game_id,
            "error": {
                "code": error.code,
                "message": error.message
            }
        }
        self._notification_client.notify("game_time_import_failure", params)

    def game_times_import_finished(self):
        self._notification_client.notify("game_times_import_finished", None)

    def lost_authentication(self):
        self._notification_client.notify("authentication_lost", None)

    # handlers
    def tick(self):
        """This method is called periodicaly.
        Override it to implement periodical tasks like refreshing cache.
        This method should not be blocking - any longer actions should be
        handled by asycio tasks.
        """

    def shutdown(self):
        """This method is called on plugin shutdown.
        Override it to implement tear down.
        """

    # methods
    async def authenticate(self, stored_credentials=None):
        """Overide this method to handle plugin authentication.
        The method should return galaxy.api.types.Authentication
        or raise galaxy.api.types.LoginError on authentication failure.
        """
        raise NotImplementedError()

    async def pass_login_credentials(self, step, credentials, cookies):
        raise NotImplementedError()

    async def get_owned_games(self):
        raise NotImplementedError()

    async def get_unlocked_achievements(self, game_id):
        raise NotImplementedError()

    async def start_achievements_import(self, game_ids):
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

    async def import_games_achievements(self, game_ids):
        """Call game_achievements_import_success/game_achievements_import_failure for each game_id on the list"""
        async def import_game_achievements(game_id):
            try:
                achievements = await self.get_unlocked_achievements(game_id)
                self.game_achievements_import_success(game_id, achievements)
            except Exception as error:
                self.game_achievements_import_failure(game_id, error)

        imports = [import_game_achievements(game_id) for game_id in game_ids]
        await asyncio.gather(*imports)

    async def get_local_games(self):
        raise NotImplementedError()

    async def launch_game(self, game_id):
        raise NotImplementedError()

    async def install_game(self, game_id):
        raise NotImplementedError()

    async def uninstall_game(self, game_id):
        raise NotImplementedError()

    async def get_friends(self):
        raise NotImplementedError()

    async def get_users(self, user_id_list):
        raise NotImplementedError()

    async def send_message(self, room_id, message_text):
        raise NotImplementedError()

    async def mark_as_read(self, room_id, last_message_id):
        raise NotImplementedError()

    async def get_rooms(self):
        raise NotImplementedError()

    async def get_room_history_from_message(self, room_id, message_id):
        raise NotImplementedError()

    async def get_room_history_from_timestamp(self, room_id, from_timestamp):
        raise NotImplementedError()

    async def get_game_times(self):
        raise NotImplementedError()

    async def start_game_times_import(self, game_ids):
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

    async def import_game_times(self, game_ids):
        """Call game_time_import_success/game_time_import_failure for each game_id on the list"""
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
        extra_info = writer.get_extra_info('sockname')
        logging.info("Using local address: %s:%u", *extra_info)
        plugin = plugin_class(reader, writer, token)
        await plugin.run()

    try:
        asyncio.run(coroutine())
    except Exception:
        logging.exception("Error while running plugin")
        sys.exit(5)

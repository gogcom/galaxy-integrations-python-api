import asyncio
import json
import logging
import dataclasses
from enum import Enum
from collections import OrderedDict

from galaxy.api.jsonrpc import Server, NotificationClient
from galaxy.api.stream import stdio
from galaxy.api.consts import Feature

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
    def __init__(self, platform):
        self._platform = platform

        self._feature_methods = OrderedDict()
        self._active = True

        self._reader, self._writer = stdio()

        encoder = JSONEncoder()
        self._server = Server(self._reader, self._writer, encoder)
        self._notification_client = NotificationClient(self._writer, encoder)

        def eof_handler():
            self._active = False
        self._server.register_eof(eof_handler)

        # internal
        self._register_method("shutdown", self._shutdown, internal=True)
        self._register_method("get_capabilities", self._get_capabilities, internal=True)
        self._register_method("ping", self._ping, internal=True)

        # implemented by developer
        self._register_method("init_authentication", self.authenticate)
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
            result_name="user_info_list",
            feature=Feature.ImportUsers
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

    def _register_method(self, name, handler, result_name=None, internal=False, feature=None):
        if internal:
            def method(params):
                result = handler(**params)
                if result_name:
                    result = {
                        result_name: result
                    }
                return result
            self._server.register_method(name, method, True)
        else:
            async def method(params):
                result = await handler(**params)
                if result_name:
                    result = {
                        result_name: result
                    }
                return result
            self._server.register_method(name, method, False)

        if feature is not None:
            self._feature_methods.setdefault(feature, []).append(handler)

    def _register_notification(self, name, handler, internal=False, feature=None):
        self._server.register_notification(name, handler, internal)

        if feature is not None:
            self._feature_methods.setdefault(feature, []).append(handler)

    async def run(self):
        """Plugin main coorutine"""
        async def pass_control():
            while self._active:
                logging.debug("Passing control to plugin")
                self.tick()
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
            "features": self.features
        }

    @staticmethod
    def _ping():
        pass

    # notifications
    def store_credentials(self, credentials):
        """Notify client to store plugin credentials.
        They will be pass to next authencicate calls.
        """
        self._notification_client.notify("store_credentials", credentials)

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

    def update_local_game_status(self, local_game):
        params = {"local_game" : local_game}
        self._notification_client.notify("local_game_status_changed", params)

    def add_friend(self, user):
        params = {"user_info" : user}
        self._notification_client.notify("friend_added", params)

    def remove_friend(self, user_id):
        params = {"user_id" : user_id}
        self._notification_client.notify("friend_removed", params)

    def update_friend(self, user):
        params = {"user_info" : user}
        self._notification_client.notify("friend_updated", params)

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

    async def get_owned_games(self):
        raise NotImplementedError()

    async def get_unlocked_achievements(self, game_id):
        raise NotImplementedError()

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

    async def send_message(self, room_id, message):
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

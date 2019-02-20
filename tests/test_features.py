from galaxy.api.plugin import Plugin
from galaxy.api.consts import Platform, Feature

def test_base_class():
    plugin = Plugin(Platform.Generic, None, None, None)
    assert plugin.features == []

def test_no_overloads():
    class PluginImpl(Plugin): #pylint: disable=abstract-method
        pass

    plugin = PluginImpl(Platform.Generic, None, None, None)
    assert plugin.features == []

def test_one_method_feature():
    class PluginImpl(Plugin): #pylint: disable=abstract-method
        async def get_owned_games(self):
            pass

    plugin = PluginImpl(Platform.Generic, None, None, None)
    assert plugin.features == [Feature.ImportOwnedGames]

def test_multiple_methods_feature_all():
    class PluginImpl(Plugin): #pylint: disable=abstract-method
        async def send_message(self, room_id, message):
            pass
        async def mark_as_read(self, room_id, last_message_id):
            pass
        async def get_rooms(self):
            pass
        async def get_room_history_from_message(self, room_id, message_id):
            pass
        async def get_room_history_from_timestamp(self, room_id, timestamp):
            pass

    plugin = PluginImpl(Platform.Generic, None, None, None)
    assert plugin.features == [Feature.Chat]

def test_multiple_methods_feature_not_all():
    class PluginImpl(Plugin): #pylint: disable=abstract-method
        async def send_message(self, room_id, message):
            pass

    plugin = PluginImpl(Platform.Generic, None, None, None)
    assert plugin.features == []

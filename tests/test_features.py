from galaxy.api.plugin import Plugin
from galaxy.api.consts import Platform, Feature

def test_base_class():
    plugin = Plugin(Platform.Generic, "0.1", None, None, None)
    assert plugin.features == []

def test_no_overloads():
    class PluginImpl(Plugin): #pylint: disable=abstract-method
        pass

    plugin = PluginImpl(Platform.Generic, "0.1", None, None, None)
    assert plugin.features == []

def test_one_method_feature():
    class PluginImpl(Plugin): #pylint: disable=abstract-method
        async def get_owned_games(self):
            pass

    plugin = PluginImpl(Platform.Generic, "0.1", None, None, None)
    assert plugin.features == [Feature.ImportOwnedGames]
from galaxy.api.consts import Feature, Platform
from galaxy.api.plugin import Plugin


def test_base_class():
    plugin = Plugin(Platform.Generic, "0.1", None, None, None)
    assert set(plugin.features) == {
        Feature.ImportInstalledGames,
        Feature.ImportOwnedGames,
        Feature.LaunchGame,
        Feature.InstallGame,
        Feature.UninstallGame,
        Feature.ImportAchievements,
        Feature.ImportGameTime,
        Feature.ImportFriends,
        Feature.ShutdownPlatformClient,
        Feature.LaunchPlatformClient,
        Feature.ImportGameLibrarySettings,
        Feature.ImportOSCompatibility,
        Feature.ImportUserPresence,
        Feature.ImportLocalSize,
        Feature.ImportSubscriptions,
        Feature.ImportSubscriptionGames
    }


def test_no_overloads():
    class PluginImpl(Plugin):  # pylint: disable=abstract-method
        pass

    plugin = PluginImpl(Platform.Generic, "0.1", None, None, None)
    assert plugin.features == []


def test_one_method_feature():
    class PluginImpl(Plugin):  # pylint: disable=abstract-method
        async def get_owned_games(self):
            pass

    plugin = PluginImpl(Platform.Generic, "0.1", None, None, None)
    assert plugin.features == [Feature.ImportOwnedGames]


def test_multi_features():
    class PluginImpl(Plugin):  # pylint: disable=abstract-method
        async def get_owned_games(self):
            pass

        async def get_unlocked_achievements(self, game_id, context):
            pass

        async def get_game_time(self, game_id, context):
            pass

    plugin = PluginImpl(Platform.Generic, "0.1", None, None, None)
    assert set(plugin.features) == {Feature.ImportAchievements, Feature.ImportOwnedGames, Feature.ImportGameTime}

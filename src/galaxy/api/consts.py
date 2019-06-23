from enum import Enum, Flag


class Platform(Enum):
    """Supported gaming platforms"""
    Unknown = "unknown"
    Gog = "gog"
    Steam = "steam"
    Psn = "psn"
    XBoxOne = "xboxone"
    Generic = "generic"
    Origin = "origin"
    Uplay = "uplay"
    Battlenet = "battlenet"
    Epic = "epic"
    Wargaming = "wargaming"


class Feature(Enum):
    """Possible features that can be implemented by an integration.
    It does not have to support all or any specific features from the list.
    """
    Unknown = "Unknown"
    ImportInstalledGames = "ImportInstalledGames"
    ImportOwnedGames = "ImportOwnedGames"
    LaunchGame = "LaunchGame"
    InstallGame = "InstallGame"
    UninstallGame = "UninstallGame"
    ImportAchievements = "ImportAchievements"
    ImportGameTime = "ImportGameTime"
    Chat = "Chat"
    ImportUsers = "ImportUsers"
    VerifyGame = "VerifyGame"
    ImportFriends = "ImportFriends"


class LicenseType(Enum):
    """Possible game license types, understandable for the GOG Galaxy client."""
    Unknown = "Unknown"
    SinglePurchase = "SinglePurchase"
    FreeToPlay = "FreeToPlay"
    OtherUserLicense = "OtherUserLicense"


class LocalGameState(Flag):
    """Possible states that a local game can be in.
    For example a game which is both installed and currently running should have its state set as a "bitwise or" of Running and Installed flags:
    ``local_game_state=<LocalGameState.Running|Installed: 3>``
    """
    None_ = 0
    Installed = 1
    Running = 2


class PresenceState(Enum):
    """"Possible states that a user can be in."""
    Unknown = "Unknown"
    Online = "online"
    Offline = "offline"
    Away = "away"

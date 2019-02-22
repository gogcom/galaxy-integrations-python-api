from enum import Enum

class Platform(Enum):
    Unknown = "unknown"
    Gog = "gog"
    Steam = "steam"
    Psn = "psn"
    XBoxOne = "xboxone"
    Generic = "generic"
    Origin = "origin"
    Uplay = "uplay"
    Battlenet = "battlenet"

class Feature(Enum):
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

class LicenseType(Enum):
    Unknown = "Unknown"
    SinglePurchase = "SinglePurchase"
    FreeToPlay = "FreeToPlay"
    OtherUserLicense = "OtherUserLicense"

class LocalGameState(Enum):
    Unknown = "Unknown"
    Installed = "Installed"
    Running = "Running"

class PresenceState(Enum):
    Unknown = "Unknown"
    Online = "online"
    Offline = "offline"
    Away = "away"

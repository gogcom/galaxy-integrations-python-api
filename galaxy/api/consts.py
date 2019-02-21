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
	SinglePurchase = "SinglePurchase"
	FreeToPlay = "FreeToPlay"
	OtherUserLicense = "OtherUserLicense"
	Unknown = "Unknown"

class LocalGameState(Enum):
    Installed = "Installed"
    Running = "Running"

class PresenceState(Enum):
    Online = "online"
    Offline = "offline"
    Away = "away"

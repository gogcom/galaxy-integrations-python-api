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
    Bethesda = "bethesda"
    ParadoxPlaza = "paradox"
    HumbleBundle = "humble"
    Kartridge = "kartridge"
    ItchIo = "itch"
    NintendoSwitch = "nswitch"
    NintendoWiiU = "nwiiu"
    NintendoWii = "nwii"
    NintendoGameCube = "ncube"
    RiotGames = "riot"
    Wargaming = "wargaming"
    NintendoGameBoy = "ngameboy"
    Atari = "atari"
    Amiga = "amiga"
    SuperNintendoEntertainmentSystem = "snes"
    Beamdog = "beamdog"
    Direct2Drive = "d2d"
    Discord = "discord"
    DotEmu = "dotemu"
    GameHouse = "gamehouse"
    GreenManGaming = "gmg"
    WePlay = "weplay"
    ZxSpectrum = "zx"
    ColecoVision = "vision"
    NintendoEntertainmentSystem = "nes"
    SegaMasterSystem = "sms"
    Commodore64 = "c64"
    PcEngine = "pce"
    SegaGenesis = "segag"
    NeoGeo = "neo"
    Sega32X = "sega32"
    SegaCd = "segacd"
    _3Do = "3do"
    SegaSaturn = "saturn"
    PlayStation = "psx"
    PlayStation2 = "ps2"
    Nintendo64 = "n64"
    AtariJaguar = "jaguar"
    SegaDreamcast = "dc"
    Xbox = "xboxog"
    Amazon = "amazon"
    GamersGate = "gg"
    Newegg = "egg"
    BestBuy = "bb"
    GameUk = "gameuk"
    Fanatical = "fanatical"
    PlayAsia = "playasia"
    Stadia = "stadia"
    Arc = "arc"
    ElderScrollsOnline = "eso"
    Glyph = "glyph"
    AionLegionsOfWar = "aionl"
    Aion = "aion"
    BladeAndSoul = "blade"
    GuildWars = "gw"
    GuildWars2 = "gw2"
    Lineage2 = "lin2"
    FinalFantasy11 = "ffxi"
    FinalFantasy14 = "ffxiv"
    TotalWar = "totalwar"
    WindowsStore = "winstore"
    EliteDangerous = "elites"
    StarCitizen = "star"
    PlayStationPortable = "psp"
    PlayStationVita = "psvita"
    NintendoDs = "nds"
    Nintendo3Ds = "3ds"
    PathOfExile = "pathofexile"
    Twitch = "twitch"
    Minecraft = "minecraft"
    GameSessions = "gamesessions"
    Nuuvem = "nuuvem"
    FXStore = "fxstore"
    IndieGala = "indiegala"
    Playfire = "playfire"
    Oculus = "oculus"
    Test = "test"
    Rockstar = "rockstar"


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
    ShutdownPlatformClient = "ShutdownPlatformClient"
    LaunchPlatformClient = "LaunchPlatformClient"
    ImportGameLibrarySettings = "ImportGameLibrarySettings"
    ImportOSCompatibility = "ImportOSCompatibility"
    ImportUserPresence = "ImportUserPresence"
    ImportLocalSize = "ImportLocalSize"
    ImportSubscriptions = "ImportSubscriptions"
    ImportSubscriptionGames = "ImportSubscriptionGames"


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


class OSCompatibility(Flag):
    """Possible game OS compatibility.
    Use "bitwise or" to express multiple OSs compatibility, e.g. ``os=OSCompatibility.Windows|OSCompatibility.MacOS``
    """
    Windows = 0b001
    MacOS   = 0b010
    Linux   = 0b100


class PresenceState(Enum):
    """"Possible states of a user."""
    Unknown = "unknown"
    Online = "online"
    Offline = "offline"
    Away = "away"


class SubscriptionDiscovery(Flag):
    """Possible capabilities which inform what methods of subscriptions ownership detection are supported.

    :param AUTOMATIC: integration can retrieve the proper status of subscription ownership.
    :param USER_ENABLED: integration can handle override of ~class::`Subscription.owned` value to True
    """
    AUTOMATIC = 1
    USER_ENABLED = 2

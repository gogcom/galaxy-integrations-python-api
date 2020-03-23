from dataclasses import dataclass
from typing import Dict, List, Optional

from galaxy.api.consts import LicenseType, LocalGameState, PresenceState, SubscriptionDiscovery


@dataclass
class Authentication:
    """Return this from :meth:`.authenticate` or :meth:`.pass_login_credentials`
    to inform the client that authentication has successfully finished.

    :param user_id: id of the authenticated user
    :param user_name: username of the authenticated user
    """
    user_id: str
    user_name: str


@dataclass
class Cookie:
    """Cookie

    :param name: name of the cookie
    :param value: value of the cookie
    :param domain: optional domain of the cookie
    :param path: optional path of the cookie
    """
    name: str
    value: str
    domain: Optional[str] = None
    path: Optional[str] = None


@dataclass
class NextStep:
    """Return this from :meth:`.authenticate` or :meth:`.pass_login_credentials` to open client built-in browser with given url.
    For example:

    .. code-block:: python
        :linenos:

        PARAMS = {
            "window_title": "Login to platform",
            "window_width": 800,
            "window_height": 600,
            "start_uri": URL,
            "end_uri_regex": r"^https://platform_website\.com/.*"
        }

        JS = {r"^https://platform_website\.com/.*": [
            r'''
                location.reload();
            '''
        ]}

        COOKIES = [Cookie("Cookie1", "ok", ".platform.com"),
            Cookie("Cookie2", "ok", ".platform.com")
            ]

        async def authenticate(self, stored_credentials=None):
            if not stored_credentials:
                return NextStep("web_session", PARAMS, cookies=COOKIES, js=JS)

    :param auth_params: configuration options: {"window_title": :class:`str`, "window_width": :class:`str`,
        "window_height": :class:`int`, "start_uri": :class:`int`, "end_uri_regex": :class:`str`}
    :param cookies: browser initial set of cookies
    :param js: a map of the url regex patterns into the list of *js* scripts that should be executed
        on every document at given step of internal browser authentication.
    """
    next_step: str
    auth_params: Dict[str, str]
    cookies: Optional[List[Cookie]] = None
    js: Optional[Dict[str, List[str]]] = None


@dataclass
class LicenseInfo:
    """Information about the license of related product.

    :param license_type: type of license
    :param owner: optional owner of the related product, defaults to currently authenticated user
    """
    license_type: LicenseType
    owner: Optional[str] = None


@dataclass
class Dlc:
    """Downloadable content object.

    :param dlc_id: id of the dlc
    :param dlc_title: title of the dlc
    :param license_info: information about the license attached to the dlc
    """
    dlc_id: str
    dlc_title: str
    license_info: LicenseInfo


@dataclass
class Game:
    """Game object.

    :param game_id: unique identifier of the game, this will be passed as parameter for methods such as launch_game
    :param game_title: title of the game
    :param dlcs: list of dlcs available for the game
    :param license_info: information about the license attached to the game
    """
    game_id: str
    game_title: str
    dlcs: Optional[List[Dlc]]
    license_info: LicenseInfo


@dataclass
class Achievement:
    """Achievement, has to be initialized with either id or name.

    :param unlock_time: unlock time of the achievement
    :param achievement_id: optional id of the achievement
    :param achievement_name: optional name of the achievement
    """
    unlock_time: int
    achievement_id: Optional[str] = None
    achievement_name: Optional[str] = None

    def __post_init__(self):
        assert self.achievement_id or self.achievement_name, \
            "One of achievement_id or achievement_name is required"


@dataclass
class LocalGame:
    """Game locally present on the authenticated user's computer.

    :param game_id: id of the game
    :param local_game_state: state of the game
    """
    game_id: str
    local_game_state: LocalGameState


@dataclass
class FriendInfo:
    """
    .. deprecated:: 0.56
      Use :class:`UserInfo`.

    Information about a friend of the currently authenticated user.

    :param user_id: id of the user
    :param user_name: username of the user
    """
    user_id: str
    user_name: str


@dataclass
class UserInfo:
    """Information about a user of related user.

    :param user_id: id of the user
    :param user_name: username of the user
    :param avatar_url: the URL of the user avatar
    :param profile_url: the URL of the user profile
    """
    user_id: str
    user_name: str
    avatar_url: Optional[str]
    profile_url: Optional[str]


@dataclass
class GameTime:
    """Game time of a game, defines the total time spent in the game
    and the last time the game was played.

    :param game_id: id of the related game
    :param time_played: the total time spent in the game in **minutes**
    :param last_played_time: last time the game was played (**unix timestamp**)
    """
    game_id: str
    time_played: Optional[int]
    last_played_time: Optional[int]


@dataclass
class GameLibrarySettings:
    """Library settings of a game, defines assigned tags and visibility flag.

    :param game_id: id of the related game
    :param tags: collection of tags assigned to the game
    :param hidden: indicates if the game should be hidden in GOG Galaxy client
    """
    game_id: str
    tags: Optional[List[str]]
    hidden: Optional[bool]


@dataclass
class UserPresence:
    """Presence information of a user.

    The GOG Galaxy client will prefer to generate user status basing on `game_id` (or `game_title`)
    and `in_game_status` fields but if plugin is not capable of delivering it then the `full_status` will be used if
    available

    :param presence_state: the state of the user
    :param game_id: id of the game a user is currently in
    :param game_title: name of the game a user is currently in
    :param in_game_status: status set by the game itself e.x. "In Main Menu"
    :param full_status: full user status e.x. "Playing <title_name>: <in_game_status>"
    """
    presence_state: PresenceState
    game_id: Optional[str] = None
    game_title: Optional[str] = None
    in_game_status: Optional[str] = None
    full_status: Optional[str] = None


@dataclass
class Subscription:
    """Information about a subscription.

    :param subscription_name: name of the subscription, will also be used as its identifier.
    :param owned: whether the subscription is owned or not, None if unknown.
    :param end_time: unix timestamp of when the subscription ends, None if unknown.
    :param subscription_discovery: combination of settings that can be manually
        chosen by user to determine subscription handling behaviour. For example, if the integration cannot retrieve games
        for subscription when user doesn't own it, then USER_ENABLED should not be used.
        If the integration cannot determine subscription ownership for a user then AUTOMATIC should not be used.

    """
    subscription_name: str
    owned: Optional[bool] = None
    end_time: Optional[int] = None
    subscription_discovery: SubscriptionDiscovery = SubscriptionDiscovery.AUTOMATIC | \
                                                                 SubscriptionDiscovery.USER_ENABLED

    def __post_init__(self):
        assert self.subscription_discovery in [SubscriptionDiscovery.AUTOMATIC, SubscriptionDiscovery.USER_ENABLED,
                                               SubscriptionDiscovery.AUTOMATIC | SubscriptionDiscovery.USER_ENABLED]


@dataclass
class SubscriptionGame:
    """Information about a game from a subscription.

    :param game_title: title of the game
    :param game_id: id of the game
    :param start_time: unix timestamp of when the game has been added to subscription
    :param end_time: unix timestamp of when the game will be removed from subscription.
    """
    game_title: str
    game_id: str
    start_time: Optional[int] = None
    end_time: Optional[int] = None

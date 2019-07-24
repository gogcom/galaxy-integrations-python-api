from dataclasses import dataclass
from typing import List, Dict, Optional

from galaxy.api.consts import LicenseType, LocalGameState

@dataclass
class Authentication():
    """Return this from :meth:`.authenticate` or :meth:`.pass_login_credentials`
    to inform the client that authentication has successfully finished.

    :param user_id: id of the authenticated user
    :param user_name: username of the authenticated user
    """
    user_id: str
    user_name: str

@dataclass
class Cookie():
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
class NextStep():
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

    :param auth_params: configuration options: {"window_title": :class:`str`, "window_width": :class:`str`, "window_height": :class:`int`, "start_uri": :class:`int`, "end_uri_regex": :class:`str`}
    :param cookies: browser initial set of cookies
    :param js: a map of the url regex patterns into the list of *js* scripts that should be executed on every document at given step of internal browser authentication.
    """
    next_step: str
    auth_params: Dict[str, str]
    cookies: Optional[List[Cookie]] = None
    js: Optional[Dict[str, List[str]]] = None

@dataclass
class LicenseInfo():
    """Information about the license of related product.

    :param license_type: type of license
    :param owner: optional owner of the related product, defaults to currently authenticated user
    """
    license_type: LicenseType
    owner: Optional[str] = None

@dataclass
class Dlc():
    """Downloadable content object.

    :param dlc_id: id of the dlc
    :param dlc_title: title of the dlc
    :param license_info: information about the license attached to the dlc
    """
    dlc_id: str
    dlc_title: str
    license_info: LicenseInfo

@dataclass
class Game():
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
class Achievement():
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
class LocalGame():
    """Game locally present on the authenticated user's computer.

    :param game_id: id of the game
    :param local_game_state: state of the game
    """
    game_id: str
    local_game_state: LocalGameState

@dataclass
class FriendInfo():
    """Information about a friend of the currently authenticated user.

    :param user_id: id of the user
    :param user_name: username of the user
    """
    user_id: str
    user_name: str

@dataclass
class GameTime():
    """Game time of a game, defines the total time spent in the game
    and the last time the game was played.

    :param game_id: id of the related game
    :param time_played: the total time spent in the game in **minutes**
    :param last_time_played: last time the game was played (**unix timestamp**)
    """
    game_id: str
    time_played: Optional[int]
    last_played_time: Optional[int]

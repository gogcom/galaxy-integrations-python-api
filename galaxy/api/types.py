from dataclasses import dataclass
from typing import List, Optional

from galaxy.api.consts import LicenseType, LocalGameState, PresenceState

@dataclass
class Authentication():
    user_id: str
    user_name: str

@dataclass
class LicenseInfo():
    license_type: LicenseType
    owner: Optional[str] = None

@dataclass
class Dlc():
    dlc_id: str
    dlc_title: str
    license_info: LicenseInfo

@dataclass
class Game():
    game_id: str
    game_title: str
    dlcs: List[Dlc]
    license_info: LicenseInfo

@dataclass
class Achievement():
    achievement_id: str
    unlock_time: int

@dataclass
class LocalGame():
    game_id: str
    local_game_state: LocalGameState

@dataclass
class Presence():
    presence_state: PresenceState
    game_id: Optional[str] = None
    presence_status: Optional[str] = None

@dataclass
class UserInfo():
    user_id: str
    is_friend: bool
    user_name: str
    avatar_url: str
    presence: Presence

@dataclass
class Room():
    room_id: str
    unread_message_count: int
    last_message_id: str

@dataclass
class Message():
    message_id: str
    sender_id: str
    sent_time: int
    message_text: str

@dataclass
class GameTime():
    game_id: str
    time_played: int
    last_played_time: int

from dataclasses import dataclass
from typing import List

from galaxy.api.jsonrpc import ApplicationError
from galaxy.api.consts import LocalGameState, PresenceState

@dataclass
class AuthenticationSuccess():
    user_id: str
    user_name: str

@dataclass
class NextStep():
    next_step: str
    auth_params: dict

class LoginError(ApplicationError):
    def __init__(self, current_step, reason):
        data = {
            "current_step": current_step,
            "reason": reason
        }
        super().__init__(data)

@dataclass
class LicenseInfo():
    license_type: str
    owner: str = None

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

class GetGamesError(ApplicationError):
    def __init__(self, reason):
        data = {
            "reason": reason
        }
        super().__init__(data)

@dataclass
class Achievement():
    achievement_id: str
    unlock_time: int

class GetAchievementsError(ApplicationError):
    def __init__(self, reason):
        data = {
            "reason": reason
        }
        super().__init__(data)

@dataclass
class LocalGame():
    game_id: str
    local_game_state: LocalGameState

class GetLocalGamesError(ApplicationError):
    def __init__(self, reason):
        data = {
            "reason": reason
        }
        super().__init__(data)

@dataclass
class Presence():
    presence_state: PresenceState
    game_id: str = None
    presence_status: str = None

@dataclass
class UserInfo():
    user_id: str
    is_friend: bool
    user_name: str
    avatar_url: str
    presence: Presence

class GetFriendsError(ApplicationError):
    def __init__(self, reason):
        data = {
            "reason": reason
        }
        super().__init__(data)

class GetUsersError(ApplicationError):
    def __init__(self, reason):
        data = {
            "reason": reason
        }
        super().__init__(data)

class SendMessageError(ApplicationError):
    def __init__(self, reason):
        data = {
            "reason": reason
        }
        super().__init__(data)

class MarkAsReadError(ApplicationError):
    def __init__(self, reason):
        data = {
            "reason": reason
        }
        super().__init__(data)

@dataclass
class Room():
    room_id: str
    unread_message_count: int
    last_message_id: str

class GetRoomsError(ApplicationError):
    def __init__(self, reason):
        data = {
            "reason": reason
        }
        super().__init__(data)

@dataclass
class Message():
    message_id: str
    sender_id: str
    sent_time: int
    message_text: str

class GetRoomHistoryError(ApplicationError):
    def __init__(self, reason):
        data = {
            "reason": reason
        }
        super().__init__(data)

@dataclass
class GameTime():
    game_id: str
    time_played: int
    last_played_time: int

class GetGameTimeError(ApplicationError):
    def __init__(self, reason):
        data = {
            "reason": reason
        }
        super().__init__(data)
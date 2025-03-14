import json
import time
import uuid


class MessageType:
    JOIN_REQUEST = "join_request"
    JOIN_RESPONSE = "join_response"
    GAME_STATE = "game_state"
    PLAYER_ACTION = "player_action"
    CHAT = "chat"
    DISCONNECT = "disconnect"


class ActionType:
    HIT = "hit"
    STAND = "stand"
    PLACE_BET = "place_bet"
    START_GAME = "start_game"
    NEW_ROUND = "new_round"


class Message:
    def __init__(self, msg_type, sender_id, content, timestamp=None, message_id=None):
        self.msg_type = msg_type
        self.sender_id = sender_id
        self.content = content
        self.timestamp = timestamp if timestamp else int(time.time() * 1000)
        self.message_id = message_id if message_id else str(uuid.uuid4())

    def to_json(self):
        """Convert message to JSON string"""
        return json.dumps({
            "msg_type": self.msg_type,
            "sender_id": self.sender_id,
            "content": self.content,
            "timestamp": self.timestamp,
            "message_id": self.message_id
        })

    @classmethod
    def from_json(cls, json_string):
        """Create a Message object from JSON string"""
        data = json.loads(json_string)
        return cls(
            data["msg_type"],
            data["sender_id"],
            data["content"],
            data["timestamp"],
            data["message_id"]
        )

    @classmethod
    def create_join_request(cls, player_id, player_name):
        """Create a join request message"""
        content = {
            "player_id": player_id,
            "player_name": player_name
        }
        return cls(MessageType.JOIN_REQUEST, player_id, content)

    @classmethod
    def create_join_response(cls, host_id, accepted, game_id=None, reason=None):
        """Create a response to a join request"""
        content = {
            "accepted": accepted,
            "game_id": game_id,
            "reason": reason
        }
        return cls(MessageType.JOIN_RESPONSE, host_id, content)

    @classmethod
    def create_action_message(cls, player_id, action_type, action_data=None):
        """Create a player action message"""
        content = {
            "action_type": action_type,
            "action_data": action_data or {}
        }
        return cls(MessageType.PLAYER_ACTION, player_id, content)

    @classmethod
    def create_game_state_message(cls, host_id, game_state):
        """Create a game state update message"""
        return cls(MessageType.GAME_STATE, host_id, game_state)

    @classmethod
    def create_chat_message(cls, player_id, player_name, text):
        """Create a chat message"""
        content = {
            "player_name": player_name,
            "text": text
        }
        return cls(MessageType.CHAT, player_id, content)

    @classmethod
    def create_disconnect_message(cls, player_id):
        """Create a disconnect message"""
        return cls(MessageType.DISCONNECT, player_id, {})
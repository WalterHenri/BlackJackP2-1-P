import json
from shared.models.card import Suits, Values, Card
from shared.game_logic.state_manager import GameState


class Serializer:
    @staticmethod
    def serialize_game_state(game):
        """Convert game state to JSON string for network transmission"""
        return json.dumps(game.get_game_state())

    @staticmethod
    def deserialize_game_state(json_data):
        """Convert JSON string back to game state dict"""
        return json.loads(json_data)

    @staticmethod
    def serialize_card(card):
        """Convert a card to a serializable dict"""
        return {
            "suit": card.suit.value,
            "value": card.value.value
        }

    @staticmethod
    def deserialize_card(card_dict):
        """Convert a dict back to a Card object"""
        return Card(
            Suits(card_dict["suit"]),
            Values(card_dict["value"])
        )
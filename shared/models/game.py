from shared.models.deck import Deck
from shared.game_logic.state_manager import GameStateManager, GameState
from shared.game_logic.rules import RulesEngine
from shared.game_logic.bet_manager import BetManager
import uuid

class Game:
    def __init__(self, game_id=None):
        self.game_id = game_id if game_id else str(uuid.uuid4())
        self.deck = Deck()
        self.state_manager = GameStateManager()
        self.rules = RulesEngine()
        self.bet_manager = BetManager()
        self.host_player_id = None
        self.messages = []

    def initialize_game(self, host_player):
        """Initialize a new game with a host player"""
        self.host_player_id = host_player.player_id
        host_player.is_host = True
        self.state_manager.add_player(host_player)
        self.state_manager.dealer_index = 0  # Host is dealer

    def add_player(self, player):
        """Add a player to the game"""
        if self.state_manager.state != GameState.WAITING_FOR_PLAYERS:
            return False, "Cannot add players after game has started"

        player_index = self.state_manager.add_player(player)
        return True, player_index

    def start_game(self):
        """Start the game once all players have joined"""
        if len(self.state_manager.players) < 2:
            return False, "Need at least 2 players to start"

        self.deck.init()
        self.deck.shuffle()
        self.state_manager.start_new_round()
        return True, "Game started successfully"

    def place_bet(self, player_id, amount):
        """Place a bet for the specified player"""
        if self.state_manager.state != GameState.BETTING:
            return False, "Not in betting phase"

        player = self._find_player_by_id(player_id)
        if not player:
            return False, "Player not found"

        success, message = self.bet_manager.place_bet(player, amount)

        # Check if all players have bet
        all_bet = all(player.current_bet > 0 for player in self.state_manager.players)
        if all_bet:
            self.state_manager.start_dealing()
            self._deal_initial_cards()

        return success, message

    def _find_player_by_id(self, player_id):
        """Find a player by their ID"""
        for player in self.state_manager.players:
            if player.player_id == player_id:
                return player
        return None

    def _deal_initial_cards(self):
        """Deal the initial 2 cards to each player"""
        if self.state_manager.state != GameState.DEALING:
            return False

        # Deal 1 card at a time to each player
        for _ in range(2):
            for player in self.state_manager.players:
                card = self.deck.draw()
                if card:
                    player.hand.add_card(card)
                    # Check if player got 21 with initial cards (should not happen)
                    if player.hand.get_value() == 21:
                        # Redraw the second card
                        self.deck.return_card(card)
                        new_card = self.deck.draw()
                        while new_card and player.hand.would_be_21(new_card):
                            self.deck.return_card(new_card)
                            new_card = self.deck.draw()
                        if new_card:
                            player.hand.cards[-1] = new_card

        self.state_manager.start_player_turns()
        return True

    def hit(self, player_id):
        """Player requests another card"""
        if self.state_manager.state != GameState.PLAYER_TURN:
            return False, "Not in player turn phase"

        current_player = self.state_manager.get_current_player()
        if not current_player or current_player.player_id != player_id:
            return False, "Not your turn"

        if not current_player.can_hit():
            return False, "Cannot hit - hand is bust or at max value"

        card = self.deck.draw()
        if not card:
            return False, "No cards left in deck"

        current_player.hand.add_card(card)

        # Check for bust or 21
        if current_player.hand.is_busted:
            self._handle_player_done()
            return True, f"Bust! Your hand value: {current_player.hand.get_value()}"
        elif current_player.hand.get_value() == 21:
            self._handle_player_done()
            return True, "21! Perfect hand!"

        return True, f"Hit! Card: {card}. Hand value: {current_player.hand.get_value()}"

    def stand(self, player_id):
        """Player chooses to stand (no more cards)"""
        if self.state_manager.state != GameState.PLAYER_TURN:
            return False, "Not in player turn phase"

        current_player = self.state_manager.get_current_player()
        if not current_player or current_player.player_id != player_id:
            return False, "Not your turn"

        self._handle_player_done()
        return True, f"Stand with hand value: {current_player.hand.get_value()}"

    def _handle_player_done(self):
        """Handle end of current player's turn"""
        # Move to next player
        if not self.state_manager.next_player():
            # If we've gone through all players, end the game and determine winner
            self._end_round()

    def _end_round(self):
        """End the current round and determine winners"""
        winners, best_score = self.state_manager.find_winner()

        # Process wins/losses
        for player in self.state_manager.players:
            if player in winners:
                self.bet_manager.process_winner(player)
                self.messages.append(f"{player.name} ganhou com {player.hand.get_value()} pontos!")
            else:
                player.lose()
                self.messages.append(f"{player.name} perdeu com {player.hand.get_value()} pontos.")

        self.state_manager.state = GameState.GAME_OVER
        return winners

    def start_new_round(self):
        """Start a new round of the game"""
        # Reset all player hands
        for player in self.state_manager.players:
            player.reset_hand()

        # Clear bets
        self.bet_manager.clear_bets()

        # Get a fresh shuffled deck
        self.deck.init()
        self.deck.shuffle()

        # Rotate dealer position for fairness
        self.state_manager.dealer_index = (self.state_manager.dealer_index + 1) % len(self.state_manager.players)

        # Start new round
        if self.state_manager.start_new_round():
            return True, "New round started"
        else:
            return False, "Failed to start new round"

    def get_game_state(self):
        """Get the current state of the game for serialization"""
        return {
            "game_id": self.game_id,
            "state": self.state_manager.state.name,
            "current_player_index": self.state_manager.current_player_index,
            "players": [
                {
                    "id": player.player_id,
                    "name": player.name,
                    "balance": player.balance,
                    "current_bet": player.current_bet,
                    "is_host": player.is_host,
                    "hand_value": player.hand.get_value() if player.hand else 0,
                    "is_busted": player.hand.is_busted if player.hand else False,
                    "hand": [{"suit": card.suit.name, "value": card.value.name} for card in player.hand.cards]
                }
                for player in self.state_manager.players
            ],
            "dealer_index": self.state_manager.dealer_index,
            "cards_remaining": self.deck.cards_remaining(),
            "messages": self.messages[-5:]  # Last 5 messages
        }
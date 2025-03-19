from enum import Enum, auto


class GameState(Enum):
    WAITING_FOR_PLAYERS = auto()
    BETTING = auto()
    DEALING = auto()
    PLAYER_TURN = auto()
    GAME_OVER = auto()


class GameStateManager:
    def __init__(self):
        self.state = GameState.WAITING_FOR_PLAYERS
        self.current_player_index = 0
        self.players = []
        self.dealer_index = -1  # Host is dealer
        self.min_bet = 10
        self.max_bet = 500

    def add_player(self, player):
        """Add a player to the game"""
        self.players.append(player)
        return len(self.players) - 1  # Return player index

    def remove_player(self, player_id):
        """Remove a player from the game"""
        for i, player in enumerate(self.players):
            if player.player_id == player_id:
                self.players.pop(i)
                if i < self.current_player_index:
                    self.current_player_index -= 1
                return True
        return False

    def start_new_round(self):
        """Start a new round of the game"""
        if len(self.players) < 2:
            return False

        self.state = GameState.BETTING
        return True

    def start_dealing(self):
        """Start dealing cards once all bets are placed"""
        self.state = GameState.DEALING
        # Reset to first player after dealer
        self.current_player_index = (self.dealer_index + 1) % len(self.players)
        return True

    def start_player_turns(self):
        """Start player turns after initial dealing"""
        self.state = GameState.PLAYER_TURN
        # Make sure we start with the first player
        self.current_player_index = 0
        return True

    def next_player(self):
        """Move to the next player's turn"""
        if self.state != GameState.PLAYER_TURN:
            return False

        self.current_player_index = (self.current_player_index + 1) % len(self.players)

        # If we've gone through all players, end the game
        if self.current_player_index == 0:
            return False

        # Skip players who are busted or standing
        while (self.current_player_index < len(self.players) and 
               not self.players[self.current_player_index].can_hit()):
            self.current_player_index += 1
            if self.current_player_index >= len(self.players):
                return False

        return True

    def get_current_player(self):
        """Get the current player object"""
        if not self.players or self.current_player_index >= len(self.players):
            return None
        return self.players[self.current_player_index]

    def find_winner(self):
        """Find the winner(s) of the current round"""
        best_score = 0
        winners = []

        for player in self.players:
            score = player.hand.get_value()

            # Skip busted players
            if player.hand.is_busted:
                continue

            if score > best_score:
                best_score = score
                winners = [player]
            elif score == best_score:
                winners.append(player)

        return winners, best_score

    def end_game(self):
        """End the current game and determine winners"""
        self.state = GameState.GAME_OVER
        return self.find_winner()
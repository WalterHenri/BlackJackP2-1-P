from shared.models.hand import Hand


class Player:
    def __init__(self, name, balance=1000, player_id=None):
        self.name = name
        self.balance = balance
        self.hand = Hand()
        self.current_bet = 0
        self.player_id = player_id
        self.is_host = False
        self.is_connected = True

    def place_bet(self, amount):
        """Place a bet"""
        if amount <= self.balance:
            self.current_bet = amount
            self.balance -= amount
            return True
        return False

    def win(self, amount=None):
        """Player wins the bet"""
        if amount is None:
            amount = self.current_bet * 2
        self.balance += amount
        self.current_bet = 0

    def lose(self):
        """Player loses the bet"""
        self.current_bet = 0

    def draw(self):
        """Player draws (ties) - gets bet back"""
        self.balance += self.current_bet
        self.current_bet = 0

    def can_hit(self):
        """Check if player can request another card"""
        return self.hand.is_active and not self.hand.is_busted and self.hand.get_value() < 21

    def reset_hand(self):
        """Reset the player's hand for a new game"""
        self.hand.clear()
        self.current_bet = 0

    def __str__(self):
        return f"{self.name} (Balance: {self.balance})"
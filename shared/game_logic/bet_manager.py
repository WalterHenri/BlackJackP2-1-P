class BetManager:
    def __init__(self, min_bet=10, max_bet=500):
        self.min_bet = min_bet
        self.max_bet = max_bet
        self.pot = 0

    def place_bet(self, player, amount):
        """Process a player's bet"""
        if amount < self.min_bet:
            return False, f"Bet must be at least {self.min_bet}"

        if amount > self.max_bet:
            return False, f"Bet cannot exceed {self.max_bet}"

        if amount > player.balance:
            return False, "Insufficient funds"

        player.place_bet(amount)
        self.pot += amount
        return True, "Bet placed successfully"

    def process_winner(self, player):
        """Process winnings for a player"""
        winnings = player.current_bet * 2  # Double the bet
        player.win(winnings)
        self.pot -= winnings
        return winnings

    def process_push(self, player):
        """Process a push (tie) for a player"""
        player.draw()  # Player gets bet back
        self.pot -= player.current_bet

    def clear_bets(self):
        """Clear all bets - used when starting a new round"""
        self.pot = 0
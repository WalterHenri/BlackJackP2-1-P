class Hand:
    def __init__(self):
        self.cards = []
        self.is_active = True
        self.is_busted = False

    def add_card(self, card):
        """Add a card to the hand"""
        self.cards.append(card)
        if self.get_value() > 21:
            self.is_busted = True
            self.is_active = False

    def would_be_21(self, card):
        """Check if adding this card would result in 21"""
        total = self.get_value() + card.get_value()
        return total == 21

    def get_value(self):
        """Calculate the total value of the hand"""
        total = 0

        # Sum up all cards, with Aces worth 1
        for card in self.cards:
            total += card.get_value()

        return total

    def clear(self):
        """Clear all cards from the hand"""
        self.cards.clear()
        self.is_active = True
        self.is_busted = False

    def __str__(self):
        """String representation of the hand"""
        return ", ".join(str(card) for card in self.cards) + f" (Total: {self.get_value()})"
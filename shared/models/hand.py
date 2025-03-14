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

    def get_value(self):
        """Calculate the total value of the hand"""
        total = sum(card.get_value() for card in self.cards)

        # Handle Aces (value 1 could be 11 if it doesn't cause a bust)
        aces = sum(1 for card in self.cards if card.value.value == 1)
        while aces > 0 and total + 10 <= 21:
            total += 10
            aces -= 1

        return total

    def clear(self):
        """Clear all cards from the hand"""
        self.cards.clear()
        self.is_active = True
        self.is_busted = False

    def __str__(self):
        """String representation of the hand"""
        return ", ".join(str(card) for card in self.cards) + f" (Total: {self.get_value()})"
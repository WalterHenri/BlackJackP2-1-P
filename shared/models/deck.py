import random
from shared.models.card import Card, Suits, Values


class Deck:
    def __init__(self):
        self.cards = []
        self.init()

    def init(self):
        """Initialize a standard deck of 52 cards"""
        self.cards.clear()
        for suit in Suits:
            for value in Values:
                card = Card(suit, value)
                self.cards.append(card)

    def shuffle(self):
        """Shuffle the deck"""
        random.shuffle(self.cards)

    def draw(self):
        """Draw a card from the top of the deck"""
        if not self.cards:
            return None
        return self.cards.pop()

    def return_card(self, card):
        """Return a card to the deck and shuffle"""
        self.cards.append(card)
        self.shuffle()

    def cards_remaining(self):
        """Return the number of cards remaining in the deck"""
        return len(self.cards)
from enum import Enum


class Suits(Enum):
    HEARTS = 1
    DIAMONDS = 2
    SPADES = 3
    CLUBS = 4

    def __str__(self):
        return self.name.capitalize()


class Values(Enum):
    ACE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13

    def __str__(self):
        if self.value >= 11:
            return self.name.capitalize()
        elif self.value == 1:
            return "Ace"
        else:
            return str(self.value)


class Card:
    def __init__(self, suit, value):
        self.suit = Suits(suit) if isinstance(suit, int) else suit
        self.value = Values(value) if isinstance(value, int) else value

    def get_value(self):
        """Returns the blackjack value of the card"""
        if self.value >= 10:
            return 10
        return self.value

    def __str__(self):
        return f"{self.value} of {self.suit}"
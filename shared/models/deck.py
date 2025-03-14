from random import random
from shared.models.card import Card


class Deck:
    def __init__(self):
        self.cards = []

    def init(self):
        self.cards.clear()
        for i in range(1,5):
            for j in range(1,9):
                card = Card(i,j)
                self.cards.append(card)

    def shuffle(self):
        counter = 0
        while counter < len(self.cards):
            i = random() % len(self.cards)
            j = random() % len(self.cards)
            self.swap_values(i,j)
            counter += 1

    def draw(self):
        return self.cards.pop()

    def swap_values(self, i, j):
        self.cards[i], self.cards[j] = self.cards[j], self.cards[i]
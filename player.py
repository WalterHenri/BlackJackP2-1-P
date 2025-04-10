from card import Deck

class Player:
    def __init__(self, name):
        self.name = name
        self.hand = []
        self.score = 0
        self.status = "playing"  # can be "playing", "standing", "busted"
    
    def hit(self, deck):
        card = deck.draw()
        if card:
            self.hand.append(card)
            self.calculate_score()
            if self.score > 21:
                self.status = "busted"
        return card
    
    def stand(self):
        self.status = "standing"
    
    def calculate_score(self):
        self.score = sum(card.get_numeric_value() for card in self.hand)
        # Simple Ace handling for this version - if bust with Ace, count some Aces as 1
        num_aces = sum(1 for card in self.hand if card.value == 'A')
        while self.score > 21 and num_aces > 0:
            self.score -= 10  # Count an Ace as 1 instead of 11
            num_aces -= 1
        return self.score 
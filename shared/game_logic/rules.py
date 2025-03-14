class RulesEngine:
    @staticmethod
    def is_bust(hand):
        """Check if a hand is busted (over 21)"""
        return hand.get_value() > 21

    @staticmethod
    def is_blackjack(hand):
        """Check if a hand is a natural blackjack (21 with 2 cards)"""
        return len(hand.cards) == 2 and hand.get_value() == 21

    @staticmethod
    def compare_hands(hand1, hand2):
        """Compare two hands to determine winner
        Returns: 1 if hand1 wins, -1 if hand2 wins, 0 if tie"""
        value1 = hand1.get_value()
        value2 = hand2.get_value()

        # If one hand is busted, the other wins
        if hand1.is_busted and not hand2.is_busted:
            return -1
        if not hand1.is_busted and hand2.is_busted:
            return 1
        if hand1.is_busted and hand2.is_busted:
            return 0  # Both bust, it's a push

        # Both hands are valid, compare values
        if value1 > value2:
            return 1
        elif value1 < value2:
            return -1
        else:
            # In case of tie, check for blackjack
            if RulesEngine.is_blackjack(hand1) and not RulesEngine.is_blackjack(hand2):
                return 1
            elif not RulesEngine.is_blackjack(hand1) and RulesEngine.is_blackjack(hand2):
                return -1

            # If still tied, compare card count (fewer cards is better)
            if len(hand1.cards) < len(hand2.cards):
                return 1
            elif len(hand1.cards) > len(hand2.cards):
                return -1

            # True tie
            return 0

    @staticmethod
    def calculate_winners(players):
        """Calculate winners among a list of players
        Returns list of winning player indices"""
        if not players:
            return []

        winners = []
        best_value = 0

        # First pass: find highest non-bust value
        for i, player in enumerate(players):
            if not player.hand.is_busted:
                value = player.hand.get_value()
                if value > best_value:
                    best_value = value

        # Second pass: find all players with that value
        for i, player in enumerate(players):
            if not player.hand.is_busted and player.hand.get_value() == best_value:
                winners.append(i)

        return winners
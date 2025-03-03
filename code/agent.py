import game.visualize_utils as U
from game.players import BasePokerPlayer
import random

class MyEnhancedPokerPlayer(BasePokerPlayer):
    def __init__(self, uuid=None):
        self.uuid = uuid
    
    #using _preflop_strategy if round_state['street'] == 'preflop', or using _postflop_strategy
    def declare_action(self, valid_actions, hole_card, round_state):
        if round_state['street'] == 'preflop':
            action, amount = self._preflop_strategy(valid_actions, hole_card, round_state)
        else:
            action, amount = self._postflop_strategy(valid_actions, hole_card, round_state)
        return action, amount
    
    #determine action by hand_rank and position
    def _preflop_strategy(self, valid_actions, hole_card, round_state):
        position = self._get_position(round_state)
        hand_rank = self._evaluate_preflop_hand(hole_card)
        preflop_action = self._get_preflop_action(valid_actions, hand_rank, position, round_state)
        return preflop_action
    
    def _get_position(self, round_state):
        seats = round_state['seats']
        player_uuid = self.uuid
        player_index = next(index for index, seat in enumerate(seats) if seat['uuid'] == player_uuid)
        dealer_btn = round_state['dealer_btn']
        position = (player_index - dealer_btn + len(seats)) % len(seats)
        position_names = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']
        return position_names[position]
    
    def _evaluate_preflop_hand(self, hole_card):
        rank_order = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        ranks = [rank_order[card[1]] for card in hole_card]
        suits = [card[0] for card in hole_card]
        suited = (suits[0] == suits[1])
        ranks.sort(reverse=True)

        if ranks[0] == ranks[1]:
            return 8  # Pair
        elif suited:
            if ranks[0] > 9 or ranks[1] > 9:
                return 7  # High suited cards
            return 6  # Suited cards
        elif ranks[0] > 9 or ranks[1] > 9:
            return 5  # High cards
        return 4  # Other hands
    
    def _get_preflop_action(self, valid_actions, hand_rank, position, round_state):
        strong_hands = [8, 7]  # Pair or high suited cards
        medium_hands = [6, 5]

        if hand_rank in strong_hands:
            return 'raise', valid_actions[2]['amount']['max']
        elif position in ['BTN', 'CO', 'SB'] and hand_rank in medium_hands:
            return 'call', next(act['amount'] for act in valid_actions if act['action'] == 'call')
        else:
            return 'fold', 0
  
    #determine action by community_card, hand_strength, and rate_of_return
    def _postflop_strategy(self, valid_actions, hole_card, round_state):
        community_card = round_state['community_card']
        hand_strength = self._evaluate_hand_strength(hole_card, community_card)
        pot_odds = self._calculate_pot_odds(valid_actions)
        rate_of_return = hand_strength / pot_odds if pot_odds > 0 else 0
        return self._make_decision(valid_actions, rate_of_return, hand_strength, round_state)

    def _evaluate_hand_strength(self, hole_card, community_card):
        all_cards = hole_card + community_card
        suits = {'C': 0, 'D': 0, 'H': 0, 'S': 0}
        ranks = [0] * 13

        for card in all_cards:
            rank = '23456789TJQKA'.index(card[1])
            suit = card[0]
            suits[suit] |= (1 << rank)
            ranks[rank] += 1

        flush = any(bin(suits[suit]).count('1') >= 5 for suit in suits)
        straight = self._evaluate_straight(ranks)
        hand_type = self._evaluate_hand_type(ranks, flush, straight)
        hand_strength = self._calculate_hand_strength(hand_type, ranks)
        return hand_strength

    def _evaluate_straight(self, ranks):
        for i in range(9, -1, -1):
            if all(ranks[i + j] > 0 for j in range(5)):
                return True
        if all(ranks[j] > 0 for j in [12, 0, 1, 2, 3]):
            return True
        return False

    def _evaluate_hand_type(self, ranks, flush, straight):
        if straight and flush:
            return 8
        if 4 in ranks:
            return 7
        if 3 in ranks and 2 in ranks:
            return 6
        if flush:
            return 5
        if straight:
            return 4
        if 3 in ranks:
            return 3
        if ranks.count(2) == 2:
            return 2
        if 2 in ranks:
            return 1
        return 0

    def _calculate_hand_strength(self, hand_type, ranks):
        hand_value = hand_type << 20
        if hand_type == 0:  # High card
            for i in range(12, -1, -1):
                if ranks[i] > 0:
                    hand_value |= (i << (4 * (4 - ranks[i])))
        return hand_value

    def _calculate_pot_odds(self, valid_actions):
        call_amount = next(act['amount'] for act in valid_actions if act['action'] == 'call')
        pot_size = call_amount + sum(act['amount'] for act in valid_actions if act['action'] == 'raise' or act['action'] == 'call')
        if pot_size == 0:
            return 0
        return call_amount / pot_size

    def _make_decision(self, valid_actions, rate_of_return, hand_strength, round_state):
        stack_size = next(seat['stack'] for seat in round_state['seats'] if seat['uuid'] == self.uuid)
        big_blind = round_state['small_blind_amount'] * 2

        if stack_size - rate_of_return < big_blind * 4 and hand_strength < 0.5:
            return 'fold', 0

        if rate_of_return < 0.8:
            if random.random() < 0.05:
                return 'raise', valid_actions[2]['amount']['min']*2
            return 'fold', 0
        elif rate_of_return < 1.0:
            if random.random() < 0.15:
                return 'raise', valid_actions[2]['amount']['min']*2
            return 'fold', 0
        elif rate_of_return < 1.3:
            if random.random() < 0.4:
                return 'raise', valid_actions[2]['amount']['min']*2
            return 'call', next(act['amount'] for act in valid_actions if act['action'] == 'call')
        else:
            if random.random() < 0.7:
                return 'raise', valid_actions[2]['amount']['min']*2
            return 'call', next(act['amount'] for act in valid_actions if act['action'] == 'call')
        
    def receive_game_start_message(self, game_info):
        pass

    def receive_round_start_message(self, round_count, hole_card, seats):
        pass

    def receive_street_start_message(self, street, round_state):
        pass

    def receive_game_update_message(self, new_action, round_state):
        pass

    def receive_round_result_message(self, winners, hand_info, round_state):
        pass


def setup_ai():
    return MyEnhancedPokerPlayer()

from game.players import BasePokerPlayer
import random
import numpy as np
from agents.random_player import setup_ai as random_ai
from agents.emulator import Emulator
from agents.game_state_utils import restore_game_state

class RLPLayer(BasePokerPlayer):

    def __init__(self):
        self.q_table = {}
        self.learning_rate = 0.1
        self.discount_factor = 0.9
        self.exploration_rate = 1.0
        self.exploration_decay = 0.99
        self.last_state = None
        self.last_action = None
        self.emulator = Emulator()

    def receive_game_start_message(self, game_info):
        player_num = game_info["player_num"]
        max_round = game_info["rule"]["max_round"]
        small_blind_amount = game_info["rule"]["small_blind_amount"]
        ante_amount = game_info["rule"]["ante"]
        blind_structure = game_info["rule"]["blind_structure"]

        self.emulator.set_game_rule(player_num, max_round, small_blind_amount, ante_amount)
        self.emulator.set_blind_structure(blind_structure)

        for player_info in game_info["seats"]:
            self.emulator.register_player(player_info["uuid"], random_ai())

    def declare_action(self, valid_actions, hole_card, round_state):
        state = self.get_state(round_state, hole_card)
        self.valid_actions = valid_actions
        if random.random() < self.exploration_rate:
            action = random.choice(valid_actions)
        else:
            action = self.choose_best_action(state, valid_actions)
        self.last_state = state
        self.last_action = action
        #print(action['amount'])
        action_amount = action['amount'] if isinstance(action['amount'], int) else action['amount']['amount']
        #print(action['action'], action_amount)
        return action['action'], action_amount

    def receive_round_result_message(self, winners, hand_info, round_state):
        if not hand_info or not self.last_state or not self.last_action:
            return
        reward = self.get_reward(winners)
        new_state = self.get_state(round_state, hand_info[0]['hand']['hole'])
        self.update_q_table(self.last_state, self.last_action, reward, new_state)
        self.exploration_rate *= self.exploration_decay

    def get_state(self, round_state, hole_card):
        return (tuple(hole_card), round_state['street'], round_state['pot']['main']['amount'])

    def choose_best_action(self, state, valid_actions):
        if state not in self.q_table:
            self.q_table[state] = {action['action']: 0 for action in valid_actions}
        return max(valid_actions, key=lambda x: self.q_table[state][x['action']])

    def update_q_table(self, state, action, reward, new_state):
        if state not in self.q_table:
            self.q_table[state] = {action['action']: 0 for action in self.valid_actions}
        if new_state not in self.q_table:
            self.q_table[new_state] = {action['action']: 0 for action in self.valid_actions}

        old_value = self.q_table[state][action['action']]
        next_max = max(self.q_table[new_state].values())

        new_value = old_value + self.learning_rate * (reward + self.discount_factor * next_max - old_value)
        self.q_table[state][action['action']] = new_value

    def get_reward(self, winners):
        if self.uuid in [winner['uuid'] for winner in winners]:
            return 1  # Win
        else:
            return -1  # Lose

    def receive_round_start_message(self, round_count, hole_card, seats):
        pass

    def receive_street_start_message(self, street, round_state):
        pass

    def receive_game_update_message(self, new_action, round_state):
        pass

def setup_ai():
    return RLPLayer()

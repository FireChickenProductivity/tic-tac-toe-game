#This file contains integration tests and a client test using mock sockets

import protocol_definitions
from protocol import Message
import game_utilities
import unittest
from testing_utilities import *
from server import MUST_LOG_IN_TEXT

#Utility code

def create_text_message(text: str):
    return Message(protocol_definitions.TEXT_MESSAGE_PROTOCOL_TYPE_CODE, [text])

def create_must_login_message():
    return create_text_message(MUST_LOG_IN_TEXT)

def create_game_update_message(text: str):
    EMPTY_GAME_BOARD_MESSAGE = Message(protocol_definitions.GAME_UPDATE_PROTOCOL_TYPE_CODE, text)
    return EMPTY_GAME_BOARD_MESSAGE

def create_move_message(move_information):
    return Message(protocol_definitions.GAME_UPDATE_PROTOCOL_TYPE_CODE, [move_information])

def create_result_message(username, result):
    return Message(protocol_definitions.GAME_ENDING_PROTOCOL_TYPE_CODE, [username, result])

def create_victory_message(username):
    return create_result_message(username, game_utilities.VICTORY)

def create_tie_message(username):
    return create_result_message(username, game_utilities.TIE)

def create_loss_message(username):
    return create_result_message(username, game_utilities.LOSS)

EMPTY_GAME_BOARD = [game_utilities.EMPTY_POSITION*9]
EMPTY_GAME_BOARD_MESSAGE = create_game_update_message(EMPTY_GAME_BOARD)
PLAYING_X_MESSAGE = Message(protocol_definitions.GAME_PIECE_PROTOCOL_TYPE_CODE, [game_utilities.X_PIECE])
PLAYING_O_MESSAGE = Message(protocol_definitions.GAME_PIECE_PROTOCOL_TYPE_CODE, [game_utilities.O_PIECE])
GAME_CREATION_MESSAGE = create_text_message("The game was created!")

class PlayerCommands:
    def __init__(self, initial_count):
        self.initial_count = initial_count
        self.commands = []

    def insert_command(self, command):
        self.initial_count += 2
        for buffer_command in (command, self.initial_count):
            self.commands.append(buffer_command)

    def get_commands(self):
        return self.commands

ROW_CHARACTERS = {1: 'a', 2: 'b', 3: 'c', '': ''}

def compute_game_playing_actions_creating_board_state(state: str, initial_x_player_message_count, initial_o_player_message_count):
    """Returns actions that could have produced the board state by deriving the necessary moves and waiting commands"""
    x_messages = PlayerCommands(initial_x_player_message_count)
    o_messages = PlayerCommands(initial_o_player_message_count)
    row_number = 1
    column_number = 0
    row = ROW_CHARACTERS[row_number]
    for character in state:
        column_number += 1
        if column_number > 3:
            row_number += 1
            column_number = 1
            row = ROW_CHARACTERS[row_number]
        command = "move " + row + str(column_number)
        if character == game_utilities.X_PIECE:
            x_messages.insert_command(command)
        elif character == game_utilities.O_PIECE:
            o_messages.insert_command(command)
    return [messages.get_commands() for messages in (x_messages, o_messages)]



def compute_player_indices(state, player_piece):
    return [index for index in range(len(state)) if player_piece == state[index]]

class MoveIndices:
    def __init__(self, piece: str, state: str):
        self.indices = compute_player_indices(state, piece)
        self.piece = piece
    
    def get_index(self, index):
        return self.indices[index]
    
    def get_piece(self):
        return self.piece
    
    def get_last_index(self):
        return self.get_index(-1)

    def __len__(self):
        return len(self.indices)

def compute_next_partial_state(partial_state, piece, index):
    return partial_state[:index] + piece + partial_state[index + 1:]

def compute_sequential_game_playing_update_messages(state: str):
    """Returns the server board update messages that would have generated the state with each player moving sequentially across the indices while alternating turns (the player on their turn picks the next index with their piece there in the state string)"""
    messages = []
    partial_state = " "*9
    x_indices = MoveIndices(game_utilities.X_PIECE, state)
    o_indices = MoveIndices(game_utilities.O_PIECE, state)
    for i in range(len(o_indices)):
        for indices in (x_indices, o_indices):
            index = indices.get_index(i)
            partial_state = compute_next_partial_state(partial_state, indices.get_piece(), index)
            messages.append(create_move_message(partial_state))
    if len(x_indices) > len(o_indices):
        partial_state = compute_next_partial_state(partial_state, x_indices.get_piece(), x_indices.get_last_index())
        messages.append(create_move_message(partial_state))
    return messages

#Client test
class TestClient(unittest.TestCase):
    def test_local_help_system(self):
        testcase = TestCase()
        testcase.buffer_client_commands("Bob", ["help"])
        testcase.run()
        output = testcase.get_output("Bob")
        print('output', output)
        testcase.assert_values_match_output([ContainsMatcher("Help")], 'Bob')

#Integration testing
class TestCommunication(unittest.TestCase):
    def test_game_creation(self):
        expected_messages = [
            SkipItem(), 
            GAME_CREATION_MESSAGE,
            PLAYING_X_MESSAGE,
            EMPTY_GAME_BOARD_MESSAGE
        ]
        testcase = TestCase(should_perform_automatic_login=True)
        testcase.buffer_client_commands("Bob", ["create Alice", 2, "join Alice"])
        testcase.run()
        testcase.assert_received_values_match_log(expected_messages, 'Bob')
        
    def test_join_and_quit(self):
        testcase = TestCase(should_perform_automatic_login=True)
        testcase.buffer_client_commands("Bob", ["create Alice", 2, "join Alice", 4, 'quit', 5])
        testcase.buffer_client_commands("Alice", [4, 'join Bob', 6])
        testcase.run()
        expected_alice_messages = [
            SkipItem(),
            create_text_message("Bob invited you to a game!"),
            create_text_message("Bob has joined your game!"),
            create_text_message("Bob has left your game!"),
            PLAYING_O_MESSAGE,
            EMPTY_GAME_BOARD_MESSAGE,
        ]
        testcase.assert_received_values_match_log(expected_alice_messages, "Alice")

    def test_second_player_join(self):
        testcase = TestCase(should_perform_automatic_login=True)
        testcase.buffer_client_commands("Bob", ["create Alice", 4])
        testcase.buffer_client_commands("Alice", [2, 'join Bob', 4, 'quit'])
        expected_alice_messages = [
            SkipItem(),
            create_text_message("Bob invited you to a game!"),
            PLAYING_O_MESSAGE,
            EMPTY_GAME_BOARD_MESSAGE,
        ]
        expected_bob_messages = [
            SkipItem(),
            GAME_CREATION_MESSAGE,
            create_text_message("Alice has joined your game!"),
            create_text_message("Alice has left your game!")
        ]
        testcase.run()
        testcase.assert_received_values_match_log(expected_alice_messages, "Alice")
        testcase.assert_received_values_match_log(expected_bob_messages, 'Bob')

    def perform_gameplay_test(self, final_state, expected_first_player_outcome, expected_second_player_outcome):
        """Tests gameplay reaching the final state"""
        testcase = TestCase(should_perform_automatic_login=True)
        bob_messages_number_before_game_starts = 5
        alice_messages_number_before_game_starts = 6

        #Compute the client commands and board state update messages corresponding to the final board state
        bob_move_commands, alice_move_commands = compute_game_playing_actions_creating_board_state(
            final_state,
            bob_messages_number_before_game_starts,
            alice_messages_number_before_game_starts
        )
        board_state_update_messages = compute_sequential_game_playing_update_messages(final_state)

        #Buffer the client commands
        bob_commands = ["create Alice", 3, 'join Alice', bob_messages_number_before_game_starts]
        bob_commands.extend(bob_move_commands)
        alice_commands = [2, 'join Bob', alice_messages_number_before_game_starts]
        alice_commands.extend(alice_move_commands)
        testcase.buffer_client_commands("Bob", bob_commands)
        testcase.buffer_client_commands("Alice", alice_commands)

        #Assert the expected messages are received at the client
        expected_bob_messages = [
            SkipItem(),
            GAME_CREATION_MESSAGE,
            create_text_message("Alice has joined your game!"),
            PLAYING_X_MESSAGE,
            EMPTY_GAME_BOARD_MESSAGE,
        ] + board_state_update_messages
        expected_bob_messages.append(create_result_message("Alice", expected_first_player_outcome))

        expected_alice_messages = [
            SkipItem(),
            create_text_message("Bob invited you to a game!"),
            PLAYING_O_MESSAGE,
            EMPTY_GAME_BOARD_MESSAGE,
            create_text_message("Bob has joined your game!"),
        ] + board_state_update_messages
        expected_alice_messages.append(create_result_message("Bob", expected_second_player_outcome))
        
        testcase.run()
        testcase.assert_received_values_match_log(expected_bob_messages, 'Bob')
        testcase.assert_received_values_match_log(expected_alice_messages, "Alice")

    def test_gameplay(self):
        self.perform_gameplay_test("XOOX  X  ", game_utilities.VICTORY, game_utilities.LOSS)
    
    def test_tie(self):
        self.perform_gameplay_test("XOXOOXXXO", game_utilities.TIE, game_utilities.TIE)

    def test_first_player_loss(self):
        self.perform_gameplay_test("OXXXO   O", game_utilities.LOSS, game_utilities.VICTORY)

    def test_absent_player_does_not_receive_moves(self):
        testcase = TestCase(should_perform_automatic_login=True)
        testcase.buffer_client_commands("Bob", ["create Alice", 2, "join Alice", 4, 'move a1', 5])
        testcase.create_client("Alice")
        testcase.run()
        expected_alice_messages = [SkipItem()]*3
        testcase.assert_received_values_match_log(expected_alice_messages, "Alice")

    def test_quitting_player_does_not_receive_moves(self):
        testcase = TestCase(should_perform_automatic_login=True)
        testcase.buffer_client_commands("Bob", ["create Alice", 3, "join Alice", 6, 'move a1', 7, 'quit'])
        testcase.buffer_client_commands("Alice", [2, "join Bob", 5, 'quit', 6])
        testcase.run()
        expected_alice_messages = [SkipItem()]*6
        testcase.assert_received_values_match_log(expected_alice_messages, "Alice")

    def test_exiting_notifies_of_leaving(self):
        testcase = TestCase(should_perform_automatic_login=True)
        testcase.buffer_client_commands("Bob", ["create Alice", 2, "join Alice", 4, 'exit'])
        testcase.buffer_client_commands("Alice", [4, 'join Bob', 6])
        testcase.run()
        expected_alice_messages = [SkipItem()]*3 + [create_text_message("Bob has left your game!")] + [SkipItem()]*2
        testcase.assert_received_values_match_log(expected_alice_messages, "Alice")

    def _server_handles_command_when_not_logged_in(self, command):
        testcase = TestCase()
        testcase.buffer_client_commands("Bob", [command, 1])
        testcase.run()
        expected_bob_messages = [create_must_login_message()]
        testcase.assert_received_values_match_log(expected_bob_messages, "Bob")

    def test_server_handles_joining_when_not_logged_in(self):
        self._server_handles_command_when_not_logged_in(Message(protocol_definitions.JOIN_GAME_PROTOCOL_TYPE_CODE, "Alice"))

    def test_server_handles_creating_when_not_logged_in(self):
        self._server_handles_command_when_not_logged_in(Message(protocol_definitions.GAME_CREATION_PROTOCOL_TYPE_CODE, 'Alice'))

if __name__ == '__main__':
    unittest.main()
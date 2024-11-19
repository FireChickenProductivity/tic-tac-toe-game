from server import Server, help_messages
import protocol_definitions
from protocol import Message
import connection_handler
import unittest
from testing_utilities import *

def create_text_message(text: str):
    return Message(protocol_definitions.TEXT_MESSAGE_PROTOCOL_TYPE_CODE, [text])

def create_game_update_message(text: str):
    EMPTY_GAME_BOARD_MESSAGE = Message(protocol_definitions.GAME_UPDATE_PROTOCOL_TYPE_CODE, text)
    return EMPTY_GAME_BOARD_MESSAGE

def create_move_message(move_number):
    return Message(protocol_definitions.GAME_UPDATE_PROTOCOL_TYPE_CODE, move_number)
    
EMPTY_GAME_BOARD = [" "*9]
EMPTY_GAME_BOARD_MESSAGE = create_game_update_message(EMPTY_GAME_BOARD)
PLAYING_X_MESSAGE = Message(protocol_definitions.GAME_PIECE_PROTOCOL_TYPE_CODE, ["X"])
PLAYING_O_MESSAGE = Message(protocol_definitions.GAME_PIECE_PROTOCOL_TYPE_CODE, ["O"])
GAME_CREATION_MESSAGE = create_text_message("The game was created!")

class PlayerMessages:
    def __init__(self, initial_count):
        self.initial_count = initial_count
        self.messages = []

    def insert_message(self, message):
        self.initial_count += 1
        for buffer_message in (message, self.initial_count):
            self.messages.append(buffer_message)

    def get_messages(self):
        return self.messages

def compute_game_playing_actions_creating_board_state(state: str, initial_x_player_message_count, initial_o_player_message_count):
    x_messages = PlayerMessages(initial_x_player_message_count)
    o_messages = PlayerMessages(initial_o_player_message_count)
    for index, character in enumerate(state):
        move_number = index + 1
        message = create_move_message(move_number)
        if character == 'X':
            x_messages.insert_message(message)
        elif character == 'O':
            o_messages.insert_message(message)
    return [messages.get_messages() for messages in (x_messages, o_messages)]

def compute_sequential_game_playing_update_messages_for_player(state, player_piece):
    messages = []
    for i in range(len(state)):
        character = state[i]
        if character == player_piece:
            message = create_move_message(i + 1)
            messages.append(message)
    return messages

def compute_sequential_game_playing_update_messages(state: str):
    messages = []
    x_messages = compute_sequential_game_playing_update_messages_for_player(state, 'X')
    o_messages = compute_sequential_game_playing_update_messages_for_player(state, 'O')
    for i in range(len(o_messages)):
        messages.append(x_messages[i])
        messages.append(o_messages[i])
    if len(x_messages) > len(o_messages):
        messages.append(x_messages[-1])
    return messages

class TestMocking(unittest.TestCase):
    def test_can_send_messages_back_and_forth(self):
        expected_message = Message(0, [help_messages[""]])
        testcase = TestCase()
        testcase.create_client("Bob")
        testcase.buffer_client_command("Bob", "help")
        testcase.buffer_client_command("Bob", 1)
        testcase.run()
        output = testcase.get_output("Bob")
        print('output', output)
        testcase.assert_received_values_match_log([expected_message], 'Bob')
        testcase.assert_values_match_output([ContainsMatcher("Help")], 'Bob')

    def test_game_creation(self):
        expected_messages = [
            SkipItem(), 
            GAME_CREATION_MESSAGE,
            PLAYING_X_MESSAGE,
            EMPTY_GAME_BOARD_MESSAGE
        ]
        testcase = TestCase(should_perform_automatic_login=True)
        testcase.create_client("Bob")
        testcase.buffer_client_commands("Bob", ["create Alice", 2, "join Alice"])
        testcase.run()
        testcase.assert_received_values_match_log(expected_messages, 'Bob')
        
    def test_join_and_quit(self):
        testcase = TestCase(should_perform_automatic_login=True)
        testcase.create_client("Bob")
        testcase.create_client("Alice")
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
        testcase.create_client("Bob")
        testcase.create_client("Alice")
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

    def test_gameplay(self):
        testcase = TestCase(should_perform_automatic_login=True)
        final_state = "XOOXO X"
        bob_messages_number_before_game_starts = 5
        alice_messages_number_before_game_starts = 4
        bob_move_commands, alice_move_commands = compute_game_playing_actions_creating_board_state(
            final_state,
            bob_messages_number_before_game_starts,
            alice_messages_number_before_game_starts
        )
        board_state_update_messages = compute_sequential_game_playing_update_messages(final_state)
        testcase.create_client("Bob")
        testcase.create_client("Alice")
        testcase.buffer_client_commands("Bob", ["create Alice", 3, 'join Alice', bob_messages_number_before_game_starts] + bob_move_commands)
        testcase.buffer_client_commands("Alice", [2, 'join Bob', alice_messages_number_before_game_starts] + alice_move_commands)
        expected_bob_messages = [
            SkipItem(),
            GAME_CREATION_MESSAGE,
            create_text_message("Alice has joined your game!"),
            PLAYING_X_MESSAGE,
            EMPTY_GAME_BOARD_MESSAGE,
        ] + board_state_update_messages
        expected_alice_messages = [
            SkipItem(),
            create_text_message("Bob invited you to a game!"),
            PLAYING_O_MESSAGE,
            EMPTY_GAME_BOARD_MESSAGE,
        ] + board_state_update_messages
        testcase.assert_received_values_match_log(expected_alice_messages, "Alice")
        testcase.assert_received_values_match_log(expected_bob_messages, 'Bob')
if __name__ == '__main__':
    unittest.main()
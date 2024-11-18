from server import Server, help_messages
import protocol_definitions
from protocol import Message
import connection_handler
import unittest
from testing_utilities import *

def create_text_message(text: str):
    return Message(protocol_definitions.TEXT_MESSAGE_PROTOCOL_TYPE_CODE, [text])

EMPTY_GAME_BOARD = [" "*9]
EMPTY_GAME_BOARD_MESSAGE = Message(protocol_definitions.GAME_UPDATE_PROTOCOL_TYPE_CODE, EMPTY_GAME_BOARD)
PLAYING_X_MESSAGE = Message(protocol_definitions.GAME_PIECE_PROTOCOL_TYPE_CODE, ["X"])
PLAYING_O_MESSAGE = Message(protocol_definitions.GAME_PIECE_PROTOCOL_TYPE_CODE, ["O"])
GAME_CREATION_MESSAGE = create_text_message("The game was created!")

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

if __name__ == '__main__':
    unittest.main()
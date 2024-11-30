import game_actions
import protocol_definitions
from protocol import Message
from help_system import create_help_message

def _parse_two_space_separated_values(text):
    """Parses text into 2 space separated values. Returns None on failure."""
    values = text.split(" ", maxsplit=1)
    if len(values) != 2:
        return None
    return values

class Command:
    def __init__(self, client, name: str, help_message: str, action):
        self.client = client
        self.name = name
        self.help_message = help_message
        self.action = action
    
    def _handle_result(self, result):
        if type(result) == str:
            self.client.output_text(result + "\n" + self.get_help_message())
        else:
            self.client.send_message(result)

    def perform_command(self, value):
        result = self.action(self.client, value)
        self._handle_result(result)
    
    def get_name(self):
        return self.name
    
    def get_help_message(self):
        return self.help_message

def make_move(client, value):
    game = client.get_current_game()
    if not game:
        result = "You cannot make a move because you are not in a game."
    elif not game_actions.is_valid_move_text(value):
        result = "You must provide a valid move. Use the row followed by the column, such as 'move a1'."
    else:
        move_number = game_actions.convert_move_text_to_move_number(value)
        current_piece = game_actions.compute_current_player(game)
        if game[move_number - 1] != ' ':
            result = "You cannot move there because that spot is already taken."
        elif current_piece == client.get_current_piece():
            result = Message(protocol_definitions.GAME_UPDATE_PROTOCOL_TYPE_CODE, move_number)
        else:
            result = "You cannot move because it is not your turn."
    return result

def create_game(client, value):
    if value == "":
        return "To create a game, you must specify the username of your opponent."
    else:
        return Message(protocol_definitions.GAME_CREATION_PROTOCOL_TYPE_CODE, value)

def join_game(client, value):
    if value == "":
        return "To join a game, you must specify the username of your opponent."
    else:
        client.set_current_opponent(value)
        return Message(protocol_definitions.JOIN_GAME_PROTOCOL_TYPE_CODE, value)

def quit_game(client, value):
    if client.get_current_game() is None:
        return "You cannot quit a game when you are not in one."
    else:
        client.output_text("You have exited the current game.")
        client.reset_game_state()
        return Message(protocol_definitions.QUIT_GAME_PROTOCOL_TYPE_CODE)

def register_account(client, value):
    values = _parse_two_space_separated_values(value)
    if values is None:
        result ='When creating an account, you must provide a username, press space, and provide your password!'
    elif client.get_current_game() is not None:
        result = "You cannot register an account in the middle of a game!"
    else:
        result = Message(protocol_definitions.ACCOUNT_CREATION_PROTOCOL_TYPE_CODE, values)
    return result

def login(client, value):
    values = _parse_two_space_separated_values(value)
    if values is None:
        result = 'When logging in, you must provide a username, press space, and provide your password!'
    elif client.get_current_game() is not None:
        result = "You cannot log in to an account in the middle of a game!"
    else:
        client.set_credentials(*values)
        result = Message(protocol_definitions.SIGN_IN_PROTOCOL_TYPE_CODE, values)
    return result

def display_help_message(client, value):
    label = ""
    if value:
        label = value
    help_text = create_help_message(label)
    client.handle_help_message(help_text)

def create_commands(client):
    commands = [
        Command(
        client,
        'move',
        "To make a move, choose a space on the board and find it's corresponding coordinate. The rows are designated by 'a', 'b', or 'c'. The columns are '1', '2', or '3'. An example coordinate would be 'b3'. Type 'move' followed by the chosen coordinate into the terminal to make your move. You can only make a move on empty spaces.",
        make_move
        ),
        Command(
            client,
            'create',
            "To create a new game, type 'create' into the terminal followed by the username of your opponent."
        )
    ]
    command_dictionary = {}
    for command in commands:
        command_dictionary[command.get_name()] = command
    return command
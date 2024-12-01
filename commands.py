import game_actions
import protocol_definitions
from protocol import Message

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
        elif result is not None:
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
    elif not client.has_attempted_login():
        return "You must log in before creating a game!"
    else:
        return Message(protocol_definitions.GAME_CREATION_PROTOCOL_TYPE_CODE, value)

def join_game(client, value):
    if value == "":
        return "To join a game, you must specify the username of your opponent."
    elif not client.has_attempted_login():
        return "You must log in before joining a game!"
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

def output_help_message(client, value):
    client.handle_help_command(value)

class CommandManager:
    def __init__(self, commands):
        self.commands = commands

    def has_command(self, name):
        return name in self.commands

    def perform_command(self, name, value):
        self.commands[name].perform_command(value)

    def get_command_names_text(self):
        text = ""
        for command in self.commands.values():
            if text:
                text += ", "
            text += command.get_name()
        return text

    def get_command_help_message(self, name):
        return self.commands[name].get_help_message()


def create_commands(client):
    def create_command_for_client(name, help_message, action):
        return Command(client, name, help_message, action)
    commands = [
        create_command_for_client(
        'move',
        "To make a move, choose a space on the board and find it's corresponding coordinate. The rows are designated by 'a', 'b', or 'c'. The columns are '1', '2', or '3'. An example coordinate would be 'b3'. Type 'move' followed by the chosen coordinate into the terminal to make your move. You can only make a move on empty spaces.",
        make_move
        ),
        create_command_for_client(
            'create',
            "To create a new game, type 'create' into the terminal followed by the username of the person you are playing against.",
            create_game
        ),
        create_command_for_client(
            'join',
            "To join a game, type 'join' followed by the username of the person you want to play against.",
            join_game
        ),
        create_command_for_client(
            'quit',
            "To quit a game, enter 'quit' into the terminal.",
            quit_game
        ),
        create_command_for_client(
            'register',
            "Upon successfully connecting to the server, you must register an account. To do this, type 'register' followed by your chosen username and password into the terminal, seperated by spaces.",
            register_account
        ),
        create_command_for_client(
            'login',
            "After you have created an account, you will need to login. Type 'login' followed by your registered username and password into the terminal, seperated by spaces.",
            login
        ),
        create_command_for_client(
            'help',
            "Type 'help' for generic instructions or 'help' followed by a topic for specific instructions.",
            output_help_message
        )
    ]
    command_dictionary = {}
    for command in commands:
        command_dictionary[command.get_name()] = command
    return CommandManager(command_dictionary)
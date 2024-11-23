import game_actions
import protocol_definitions
from protocol import Message



class Command:
    def __init__(self, client, name: str, help_message: str, action):
        self.client = client
        self.name = name
        self.help_message = help_message
        self.action = action
    
    def _handle_result(self, feedback, message):
        if feedback:
            self.client.output_text(feedback + "\n" + self.get_help_message())
        if message:
            self.client.send_message(message)

    def perform_command(self, value):
        feedback, message = self.action(self.client, value)
        self._handle_result(feedback, message)
    
    def get_name(self):
        return self.name
    
    def get_help_message(self):
        return self.help_message

def make_move(client, value):
    game = client.get_current_game()
    message = None
    feedback = None
    if not game:
        feedback = "You cannot make a move because you are not in a game."
    elif not game_actions.is_valid_move_text(value):
        feedback = "You must provide a valid move. Use the row followed by the column, such as 'move a1'."
    else:
        move_number = game_actions.convert_move_text_to_move_number(value)
        current_piece = game_actions.compute_current_player(game)
        if game[move_number - 1] != ' ':
            feedback = "You cannot move there because that spot is already taken."
        elif current_piece == client.get_current_piece():
                message = Message(protocol_definitions.GAME_UPDATE_PROTOCOL_TYPE_CODE, move_number)
        else:
            feedback = "You cannot move because it is not your turn."
    if feedback:
        return feedback
    return feedback, message

def create_game(client, value):
    feedback = None
    message = None
    if value == "":
        feedback = "To create a game, you must specify the username of your opponent."
    else:
        message = Message(protocol_definitions.GAME_CREATION_PROTOCOL_TYPE_CODE, value)
    return feedback, message

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
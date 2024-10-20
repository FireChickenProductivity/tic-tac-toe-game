
#!/usr/bin/env python3

import sys
import socket
import selectors
import traceback
import os

import protocol
from protocol import Message
import protocol_definitions
import logging_utilities
import connection_handler
from game_manager import GameHandler
from connection_table import ConnectionTable, ConnectionTableEntry
from database_management import Account, create_database_at_path, retrieve_account_with_name_from_database_at_path, insert_account_into_database_at_path
import sqlite3 #Imported for database exceptions only

os.makedirs("logs", exist_ok=True)
logger = logging_utilities.Logger(os.path.join("logs", "server.log"))

DATA_STORING_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(DATA_STORING_DIRECTORY, 'database.db')
create_database_at_path(DATABASE_PATH)

help_messages = {
    "": "Help topics include:\nregister\nlogin\ncreate-game\njoin-game\nmove\nquit\n\nType 'help' followed by the command you would like more information about.",
    "register": "Upon successfully connecting to the server, you must register an account. To do this, type 'register' followed by your chosen username and password into the terminal, seperated by spaces.",
    "login": "After you have created an account, you will need to login. Type 'login' followed by your registered username and password into the terminal, seperated by spaces.",
    "create-game": "To create a new game, type 'create' into the terminal followed by the username of your opponent.",
    "join-game": "To join someone else's game, type 'join' followed by your opponent's username.",
    "move": "To make a move, choose a space on the board and find it's corresponding coordinate. The columns are designated by 'a', 'b', or 'c'. The rows are '1', '2', or '3'. An example coordinate would be 'b3'. Type 'move' followed by the chosen coordinate into the terminal to make your move. You can only make a move on empty spaces.",
    "quit": "To quit a game, enter 'quit' into the terminal."
}

protocol_callback_handler = protocol.ProtocolCallbackHandler()
def create_help_message(values, connection_information):
    label: str = values.get("text", "")
    if label in help_messages:
        text = help_messages[label]
        type_code = protocol_definitions.BASE_HELP_MESSAGE_PROTOCOL_TYPE_CODE
    else:
        text = f"Did not recognize help topic {label}!\n{help_messages[""]}"
        type_code = protocol_definitions.HELP_MESSAGE_PROTOCOL_TYPE_CODE
    values = (text,)
    message = Message(type_code, values)
    connection_table.send_message_to_entry(message, connection_information)

def handle_account_creation(values, connection_information):
    try:
        username = values['username']
        password = values['password']
        insert_account_into_database_at_path(Account(username, password), DATABASE_PATH)
        text = "Your account was successfully created with username: " + username
    except sqlite3.Error:
        text = f"The username {username} was already taken!"
    message = Message(protocol_definitions.TEXT_MESSAGE_PROTOCOL_TYPE_CODE, (text,))
    connection_table.send_message_to_entry(message, connection_information)

def handle_signin(values, connection_information):
    username = values['username']
    password = values['password']
    account: Account = retrieve_account_with_name_from_database_at_path(username, DATABASE_PATH)
    if account is None or password != account.password:
        text = f"No account with username matches your password!"
    else:
        text = f"You are signed in as {username}!"
        state = connection_table.get_entry_state(connection_information)
        state.username = username
        usernames_to_connections[username] = connection_information
    message = Message(protocol_definitions.TEXT_MESSAGE_PROTOCOL_TYPE_CODE, (text,))
    connection_table.send_message_to_entry(message, connection_information)

def handle_game_creation(values, connection_information):
    creator_state = connection_table.get_entry_state(connection_information)
    creator_username = creator_state.username
    invited_user_username = values["username"]
    if game_handler.create_game(creator_username, invited_user_username):
        text = "The game was created!"
    else:
        text = "The game could not be created."
    message = Message(protocol_definitions.TEXT_MESSAGE_PROTOCOL_TYPE_CODE, (text,))
    connection_table.send_message_to_entry(message, connection_information)

def handle_game_join(values, connection_information):
    joiner_state = connection_table.get_entry_state(connection_information)
    joiner_username = joiner_state.username
    other_player_username = values["username"]
    if game_handler.game_exists(joiner_username, other_player_username):
        game = game_handler.get_game(joiner_username, other_player_username)
        if joiner_state.current_game is not None:
            handle_game_quit({}, connection_information)
        joiner_state.current_game = game
        game_text = game.compute_text()
        game_message = Message(protocol_definitions.GAME_UPDATE_PROTOCOL_TYPE_CODE, (game_text,))
        connection_table.send_message_to_entry(game_message, connection_information)
        if other_player_username in usernames_to_connections:
            other_player_connection_information = usernames_to_connections[other_player_username]
            join_message = Message(protocol_definitions.TEXT_MESSAGE_PROTOCOL_TYPE_CODE, (f"{joiner_username} has joined your game!",))
            connection_table.send_message_to_entry(join_message, other_player_connection_information)

def handle_game_quit(values, connection_information):
    state = connection_table.get_entry_state(connection_information)
    game = state.current_game
    if game is not None:
        other_player_username = game.compute_other_player(state.username)
        if other_player_username in usernames_to_connections:
            other_player_connection_information = usernames_to_connections[other_player_username]
            quitting_message = Message(protocol_definitions.TEXT_MESSAGE_PROTOCOL_TYPE_CODE, (f"{state.username} has left your game!",))
            connection_table.send_message_to_entry(quitting_message, other_player_connection_information)
    else:
        failure_message = Message(protocol_definitions.TEXT_MESSAGE_PROTOCOL_TYPE_CODE, (f"You are not in a game, so you cannot quit one.",))
        connection_table.send_message_to_entry(failure_message, connection_information)

def handle_game_move(values, connection_information):
    state = connection_table.get_entry_state(connection_information)
    game = state.current_game
    if game is None:
        failure_message = Message(protocol_definitions.TEXT_MESSAGE_PROTOCOL_TYPE_CODE, (f"You are not in a game, so you cannot make moves.",))
        connection_table.send_message_to_entry(failure_message, connection_information)
    else:
        if game.make_move(state.username, values["number"]):
            game_text = game.compute_text()
            game_message = Message(protocol_definitions.GAME_UPDATE_PROTOCOL_TYPE_CODE, (game_text,))
            connection_table.send_message_to_entry(game_message, connection_information)
            other_player_username = game.compute_other_player(state.username)
            if other_player_username in usernames_to_connections:
                other_player_connection_information = usernames_to_connections[other_player_username]
                other_player_game_state = connection_table.get_entry_state(other_player_connection_information)
                if other_player_game_state.current_game is not None and other_player_game_state.current_game.compute_other_player(other_player_username) == state.username:
                    connection_table.send_message_to_entry(game_message, other_player_connection_information)
        else:
            failure_message = Message(protocol_definitions.TEXT_MESSAGE_PROTOCOL_TYPE_CODE, (f"The move was not permitted!",))
            connection_table.send_message_to_entry(failure_message, connection_information)


protocol_callback_handler.register_callback_with_protocol(create_help_message, protocol_definitions.BASE_HELP_MESSAGE_PROTOCOL_TYPE_CODE)
protocol_callback_handler.register_callback_with_protocol(create_help_message, protocol_definitions.HELP_MESSAGE_PROTOCOL_TYPE_CODE)
protocol_callback_handler.register_callback_with_protocol(handle_signin, protocol_definitions.SIGN_IN_PROTOCOL_TYPE_CODE)
protocol_callback_handler.register_callback_with_protocol(handle_account_creation, protocol_definitions.ACCOUNT_CREATION_PROTOCOL_TYPE_CODE)
protocol_callback_handler.register_callback_with_protocol(handle_game_creation, protocol_definitions.GAME_CREATION_PROTOCOL_TYPE_CODE)
protocol_callback_handler.register_callback_with_protocol(handle_game_join, protocol_definitions.JOIN_GAME_PROTOCOL_TYPE_CODE)
protocol_callback_handler.register_callback_with_protocol(handle_game_quit, protocol_definitions.QUIT_GAME_PROTOCOL_TYPE_CODE)
protocol_callback_handler.register_callback_with_protocol(handle_game_move, protocol_definitions.GAME_UPDATE_PROTOCOL_TYPE_CODE)

def cleanup_connection(connection_information):
    """Performs cleanup when a connection gets closed"""
    state = connection_table.get_entry_state(connection_information)
    connection_table.remove_entry(connection_information)
    username = state.username
    if username is not None and username in usernames_to_connections:
        usernames_to_connections.pop(username, None)

def create_connection_handler(selector, connection, address):
    connection_information = connection_handler.ConnectionInformation(connection, address)
    handler = connection_handler.ConnectionHandler(
        selector,
        connection_information,
        logger,
        protocol_callback_handler, 
        is_server = True,
        on_close_callback=cleanup_connection
    )
    return handler

class AssociatedConnectionState:
    """Data structure for holding variables associated with a connection"""
    def __init__(self):
        self.username = None
        self.current_game = None

    def __str__(self) -> str:
        return f"Username: {self.username}, playing game: {self.current_game}"

sel = selectors.DefaultSelector()
connection_table = ConnectionTable()
usernames_to_connections = {}
game_handler = GameHandler()

def accept_wrapper(sock):
    conn, addr = sock.accept()  # Should be ready to read
    logger.log_message(f"accepted connection from {addr}")
    conn.setblocking(False)
    connection_handler = create_connection_handler(sel, conn, addr)
    sel.register(conn, selectors.EVENT_READ, data=connection_handler)
    connection_table_entry = ConnectionTableEntry(connection_handler, AssociatedConnectionState())
    connection_table.insert_entry(connection_table_entry)


if len(sys.argv) != 3:
    print("usage:", sys.argv[0], "<host> <port>")
    sys.exit(1)

host, port = sys.argv[1], int(sys.argv[2])
lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Avoid bind() exception: OSError: [Errno 48] Address already in use
lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
lsock.bind((host, port))
lsock.listen()
print("listening on", (host, port))
lsock.setblocking(False)
sel.register(lsock, selectors.EVENT_READ, data=None)

try:
    while True:
        events = sel.select(timeout=None)
        for key, mask in events:
            if key.data is None:
                accept_wrapper(key.fileobj)
            else:
                message = key.data
                try:
                    message.process_events(mask)
                except Exception:
                    logger.log_message(
                        f"main: error: exception for {message.connection_information.addr}:\n{traceback.format_exc()}",
                    )
                    message.close()
except KeyboardInterrupt:
    print("caught keyboard interrupt, exiting")
finally:
    sel.close()

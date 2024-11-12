
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

class AssociatedConnectionState:
    """Data structure for holding variables associated with a connection"""
    def __init__(self):
        self.username = None
        self.current_game = None

    def __str__(self) -> str:
        return f"Username: {self.username}, playing game: {self.current_game}"

help_messages = {
    "": "Help topics include:\nregister\nlogin\ncreate-game\njoin-game\nmove\nquit\n\nType 'help' followed by the command you would like more information about.",
    "register": "Upon successfully connecting to the server, you must register an account. To do this, type 'register' followed by your chosen username and password into the terminal, seperated by spaces.",
    "login": "After you have created an account, you will need to login. Type 'login' followed by your registered username and password into the terminal, seperated by spaces.",
    "create-game": "To create a new game, type 'create' into the terminal followed by the username of your opponent.",
    "join-game": "To join someone else's game, type 'join' followed by your opponent's username.",
    "move": "To make a move, choose a space on the board and find it's corresponding coordinate. The columns are designated by 'a', 'b', or 'c'. The rows are '1', '2', or '3'. An example coordinate would be 'b3'. Type 'move' followed by the chosen coordinate into the terminal to make your move. You can only make a move on empty spaces.",
    "quit": "To quit a game, enter 'quit' into the terminal."
}

def create_listening_socket(address):
    lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Avoid bind() exception: OSError: [Errno 48] Address already in use
    lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    lsock.bind(address)
    lsock.listen()
    print("listening on", address)
    lsock.setblocking(False)
    return lsock

class Server:
    def __init__(self, host, port, selector, logger, database_path, listening_socket_creation_function):
        """
            Runs the server side of interactions with clients
            host: the server's host address
            port: the server's port number
            selector: the selector used to handle connection sockets
            logger: the logger to use for logging significant occurrences or errors
            listening_socket_creation_function: the function used to create a socket from an address, which is settable to aid with testing
        """
        self.selector = selector
        self.logger = logger
        self.database_path = database_path
        self.create_socket_from_address = listening_socket_creation_function
        self.connection_table = ConnectionTable()
        self.usernames_to_connections = {}
        self.game_handler = GameHandler()
        listening_socket = self.create_socket_from_address((host, port))
        self.selector.register(listening_socket, selectors.EVENT_READ, data=None)
        self._create_protocol_callback_handler()
        self.should_close = False

    def _create_protocol_callback_handler(self):
        self.protocol_callback_handler = protocol.ProtocolCallbackHandler()
        self.protocol_callback_handler.register_callback_with_protocol(self.create_help_message, protocol_definitions.BASE_HELP_MESSAGE_PROTOCOL_TYPE_CODE)
        self.protocol_callback_handler.register_callback_with_protocol(self.create_help_message, protocol_definitions.HELP_MESSAGE_PROTOCOL_TYPE_CODE)
        self.protocol_callback_handler.register_callback_with_protocol(self.handle_signin, protocol_definitions.SIGN_IN_PROTOCOL_TYPE_CODE)
        self.protocol_callback_handler.register_callback_with_protocol(self.handle_account_creation, protocol_definitions.ACCOUNT_CREATION_PROTOCOL_TYPE_CODE)
        self.protocol_callback_handler.register_callback_with_protocol(self.handle_game_creation, protocol_definitions.GAME_CREATION_PROTOCOL_TYPE_CODE)
        self.protocol_callback_handler.register_callback_with_protocol(self.handle_game_join, protocol_definitions.JOIN_GAME_PROTOCOL_TYPE_CODE)
        self.protocol_callback_handler.register_callback_with_protocol(self.handle_game_quit, protocol_definitions.QUIT_GAME_PROTOCOL_TYPE_CODE)
        self.protocol_callback_handler.register_callback_with_protocol(self.handle_game_move, protocol_definitions.GAME_UPDATE_PROTOCOL_TYPE_CODE)

    def create_help_message(self, values, connection_information):
        label: str = values.get("text", "")
        if label in help_messages:
            text = help_messages[label]
            type_code = protocol_definitions.BASE_HELP_MESSAGE_PROTOCOL_TYPE_CODE
        else:
            text = f"Did not recognize help topic {label}!\n{help_messages[""]}"
            type_code = protocol_definitions.HELP_MESSAGE_PROTOCOL_TYPE_CODE
        values = (text,)
        message = Message(type_code, values)
        self.connection_table.send_message_to_entry(message, connection_information)

    def handle_account_creation(self, values, connection_information):
        try:
            username = values['username']
            password = values['password']
            insert_account_into_database_at_path(Account(username, password), self.database_path)
            text = "Your account was successfully created with username: " + username
        except sqlite3.Error:
            text = f"The username {username} was already taken!"
        message = Message(protocol_definitions.TEXT_MESSAGE_PROTOCOL_TYPE_CODE, (text,))
        self.connection_table.send_message_to_entry(message, connection_information)

    def handle_signin(self, values, connection_information):
        username = values['username']
        password = values['password']
        account: Account = retrieve_account_with_name_from_database_at_path(username, self.database_path)
        if account is None or password != account.password:
            text = f"No account with username matches your password!"
        else:
            text = f"You are signed in as {username}!"
            state = self.connection_table.get_entry_state(connection_information)
            state.username = username
            self.usernames_to_connections[username] = connection_information
        message = Message(protocol_definitions.TEXT_MESSAGE_PROTOCOL_TYPE_CODE, (text,))
        self.connection_table.send_message_to_entry(message, connection_information)

    def handle_game_creation(self, values, connection_information):
        creator_state = self.connection_table.get_entry_state(connection_information)
        creator_username = creator_state.username
        invited_user_username = values["username"]
        if self.game_handler.create_game(creator_username, invited_user_username):
            text = "The game was created!"
        else:
            text = "The game could not be created."
        message = Message(protocol_definitions.TEXT_MESSAGE_PROTOCOL_TYPE_CODE, (text,))
        self.connection_table.send_message_to_entry(message, connection_information)

    def handle_game_join(self, values, connection_information):
        joiner_state = self.connection_table.get_entry_state(connection_information)
        joiner_username = joiner_state.username
        other_player_username = values["username"]
        if self.game_handler.game_exists(joiner_username, other_player_username):
            game = self.game_handler.get_game(joiner_username, other_player_username)
            if joiner_state.current_game is not None:
                self.handle_game_quit({}, connection_information)
            joiner_state.current_game = game
            player_piece = game.compute_player_piece(joiner_username)
            piece_message = Message(protocol_definitions.GAME_PIECE_PROTOCOL_TYPE_CODE, (player_piece,))
            self.connection_table.send_message_to_entry(piece_message, connection_information)
            game_text = game.compute_text()
            game_message = Message(protocol_definitions.GAME_UPDATE_PROTOCOL_TYPE_CODE, (game_text,))
            self.connection_table.send_message_to_entry(game_message, connection_information)
            if other_player_username in self.usernames_to_connections:
                other_player_connection_information = self.usernames_to_connections[other_player_username]
                join_message = Message(protocol_definitions.TEXT_MESSAGE_PROTOCOL_TYPE_CODE, (f"{joiner_username} has joined your game!",))
                self.connection_table.send_message_to_entry(join_message, other_player_connection_information)

    def handle_game_quit(self, values, connection_information):
        state = self.connection_table.get_entry_state(connection_information)
        game = state.current_game
        if game is not None:
            other_player_username = game.compute_other_player(state.username)
            if other_player_username in self.usernames_to_connections:
                other_player_connection_information = self.usernames_to_connections[other_player_username]
                quitting_message = Message(protocol_definitions.TEXT_MESSAGE_PROTOCOL_TYPE_CODE, (f"{state.username} has left your game!",))
                self.connection_table.send_message_to_entry(quitting_message, other_player_connection_information)
        else:
            failure_message = Message(protocol_definitions.TEXT_MESSAGE_PROTOCOL_TYPE_CODE, (f"You are not in a game, so you cannot quit one.",))
            self.connection_table.send_message_to_entry(failure_message, connection_information)

    def handle_game_move(self, values, connection_information):
        state = self.connection_table.get_entry_state(connection_information)
        game = state.current_game
        if game is None:
            failure_message = Message(protocol_definitions.TEXT_MESSAGE_PROTOCOL_TYPE_CODE, ("You are not in a game, so you cannot make moves.",))
            self.connection_table.send_message_to_entry(failure_message, connection_information)
        elif game.get_current_turn() != state.username:
            out_of_turn_message = Message(protocol_definitions.TEXT_MESSAGE_PROTOCOL_TYPE_CODE, ("Not your turn. Wait for your opponent's move.",))
            self.connection_table.send_message_to_entry(out_of_turn_message, connection_information)
        else:
            if game.make_move(state.username, values["number"]):
                game_text = game.compute_text()
                game_message = Message(protocol_definitions.GAME_UPDATE_PROTOCOL_TYPE_CODE, (game_text,))
                self.connection_table.send_message_to_entry(game_message, connection_information)
                other_player_username = game.compute_other_player(state.username)
                if other_player_username in self.usernames_to_connections:
                    other_player_connection_information = self.usernames_to_connections[other_player_username]
                    self.connection_table.send_message_to_entry(game_message, other_player_connection_information)

                # checks win condition
                winner = game.check_winner()
                if winner:
                    winner_message = Message(protocol_definitions.GAME_OVER_PROTOCOL_TYPE_CODE, (f"Game over! Winner: {winner}",))
                    self.connection_table.send_message_to_entry(winner_message, connection_information)
                    other_player_connection_information = self.usernames_to_connections[other_player_username]
                    self.connection_table.send_message_to_entry(winner_message, other_player_connection_information)

                    # resets game state
                    state.current_game = None
                    game.current_turn = None
                    self.game_handler.remove_game(game.creator_username, game.invited_username)
            else:
                invalid_move_message = Message(protocol_definitions.TEXT_MESSAGE_PROTOCOL_TYPE_CODE, ("Invalid move.",))
                self.connection_table.send_message_to_entry(invalid_move_message, connection_information)


    def cleanup_connection(self, connection_information):
        """Performs cleanup when a connection gets closed"""
        state = self.connection_table.get_entry_state(connection_information)
        self.connection_table.remove_entry(connection_information)
        username = state.username
        if username is not None and username in self.usernames_to_connections:
            self.usernames_to_connections.pop(username, None)

    def create_connection_handler(self, selector, connection, address):
        connection_information = connection_handler.ConnectionInformation(connection, address)
        handler = connection_handler.ConnectionHandler(
            selector,
            connection_information,
            self.logger,
            self.protocol_callback_handler, 
            is_server = True,
            on_close_callback=self.cleanup_connection
        )
        return handler

    def accept_wrapper(self, sock):
        conn, addr = sock.accept()  # Should be ready to read
        self.logger.log_message(f"accepted connection from {addr}")
        conn.setblocking(False)
        connection_handler = self.create_connection_handler(self.selector, conn, addr)
        self.selector.register(conn, selectors.EVENT_READ, data=connection_handler)
        connection_table_entry = ConnectionTableEntry(connection_handler, AssociatedConnectionState())
        self.connection_table.insert_entry(connection_table_entry)

    def close(self):
        self.should_close = True

    def listen_for_socket_events(self):
        try:
            while not self.should_close:
                events = self.selector.select(timeout=None)
                for key, mask in events:
                    if key.data is None:
                        self.accept_wrapper(key.fileobj)
                    else:
                        message = key.data
                        try:
                            message.process_events(mask)
                        except Exception:
                            self.logger.log_message(
                                f"main: error: exception for {message.connection_information.addr}:\n{traceback.format_exc()}",
                            )
                            message.close()
        except KeyboardInterrupt:
            print("caught keyboard interrupt, exiting")
        finally:
            self.selector.close()

    def get_connection_table(self):
        return self.connection_table

    def get_game_manager(self):
        return self.game_manager

    def get_usernames_to_connections(self):
        return self.usernames_to_connections


def main():
    """The entry point for the server program"""
    #Handle the arguments
    if len(sys.argv) != 3:
        print("usage:", sys.argv[0], "<host> <port>")
        sys.exit(1)
    host, port = sys.argv[1], int(sys.argv[2])

    #Make the logger and logging directory
    os.makedirs("logs", exist_ok=True)
    logger = logging_utilities.FileLogger(os.path.join("logs", "server.log"), debugging_mode = False)

    #Create the database
    DATA_STORING_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
    DATABASE_PATH = os.path.join(DATA_STORING_DIRECTORY, 'database.db')
    create_database_at_path(DATABASE_PATH)

    #Create the selector
    sel = selectors.DefaultSelector()

    #Initialize the server and listen for socket events
    server = Server(host, port, sel, logger, DATABASE_PATH, create_listening_socket)
    server.listen_for_socket_events()


if __name__ == '__main__':
    main()
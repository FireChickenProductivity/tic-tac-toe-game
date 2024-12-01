
#!/usr/bin/env python3

import sys
import socket
import selectors
import traceback
import os
import argparse

import protocol
from protocol import Message
import protocol_definitions
import logging_utilities
import connection_handler
from game_manager import GameHandler, Game
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
        self.usernames_to_connections = {}
        self.connection_table = ConnectionTable(self.usernames_to_connections)
        self.game_handler = GameHandler()
        listening_socket = self.create_socket_from_address((host, port))
        self.selector.register(listening_socket, selectors.EVENT_READ, data=None)
        self._create_protocol_callback_handler()
        self.should_close = False

    def _create_protocol_callback_handler(self):
        self.protocol_callback_handler = protocol.ProtocolCallbackHandler()
        self.protocol_callback_handler.register_callback_with_protocol(self.handle_signin, protocol_definitions.SIGN_IN_PROTOCOL_TYPE_CODE)
        self.protocol_callback_handler.register_callback_with_protocol(self.handle_account_creation, protocol_definitions.ACCOUNT_CREATION_PROTOCOL_TYPE_CODE)
        self.protocol_callback_handler.register_callback_with_protocol(self.handle_game_creation, protocol_definitions.GAME_CREATION_PROTOCOL_TYPE_CODE)
        self.protocol_callback_handler.register_callback_with_protocol(self.handle_game_join, protocol_definitions.JOIN_GAME_PROTOCOL_TYPE_CODE)
        self.protocol_callback_handler.register_callback_with_protocol(self.handle_game_quit, protocol_definitions.QUIT_GAME_PROTOCOL_TYPE_CODE)
        self.protocol_callback_handler.register_callback_with_protocol(self.handle_game_move, protocol_definitions.GAME_UPDATE_PROTOCOL_TYPE_CODE)

    def _compute_opponent_username(self, username: str):
        state = self.connection_table.get_entry_state(username)
        if state is not None and state.current_game is not None:
            return state.current_game.compute_other_player(username)
        return None

    def _send_message_to_opponent(self, player_username: str, message: Message):
        opponent_username = self._compute_opponent_username(player_username)
        if opponent_username is not None:
            self.connection_table.send_message_to_entry(message, opponent_username)

    def _send_text_message_to_opponent(self, text, player_username: str):
        self._send_message_to_opponent(player_username, Message(protocol_definitions.TEXT_MESSAGE_PROTOCOL_TYPE_CODE, text))

    def _send_text_message(self, text, connection_information):
        message = Message(protocol_definitions.TEXT_MESSAGE_PROTOCOL_TYPE_CODE, text)
        self.connection_table.send_message_to_entry(message, connection_information)

    def handle_account_creation(self, username, password, connection_information):
        try:
            insert_account_into_database_at_path(Account(username, password), self.database_path)
            text = "Your account was successfully created with username: " + username
        except sqlite3.Error:
            text = f"The username {username} was already taken!"
        self._send_text_message(text, connection_information)

    def handle_signin(self, username, password, connection_information):
        account: Account = retrieve_account_with_name_from_database_at_path(username, self.database_path)
        if account is None or password != account.password:
            text = f"No account with username matches your password!"
        else:
            text = f"You are signed in as {username}!"
            state = self.connection_table.get_entry_state(connection_information)
            state.username = username
            self.usernames_to_connections[username] = connection_information
        self._send_text_message(text, connection_information)

    def _validate_user_logged_in(self, state, connection_information):
        """Returns true if the user has logged in and otherwise returns false and notifies the user that they must log in"""
        if state.username:
            return True
        else:
            self._send_text_message("You must login before using that command!", connection_information)
            return False

    def handle_game_creation(self, invited_user_username, connection_information):
        creator_state = self.connection_table.get_entry_state(connection_information)
        if self._validate_user_logged_in(creator_state, connection_information):
            creator_username = creator_state.username
            is_game_created = self.game_handler.create_game(creator_username, invited_user_username)
            if is_game_created:
                text = "The game was created!"
            else:
                text = "The game could not be created."
            self._send_text_message(text, connection_information)
            if is_game_created:
                self._send_text_message(f"{creator_username} invited you to a game!", invited_user_username)

    def handle_game_join(self, other_player_username, connection_information):
        joiner_state = self.connection_table.get_entry_state(connection_information)
        joiner_username = joiner_state.username
        if self._validate_user_logged_in(joiner_state, connection_information) and self.game_handler.game_exists(joiner_username, other_player_username):
            game = self.game_handler.get_game(joiner_username, other_player_username)
            if joiner_state.current_game is not None:
                self.handle_game_quit(connection_information)
            joiner_state.current_game = game
            player_piece = game.compute_player_piece(joiner_username)
            piece_message = Message(protocol_definitions.GAME_PIECE_PROTOCOL_TYPE_CODE, (player_piece,))
            self.connection_table.send_message_to_entry(piece_message, connection_information)
            game_text = game.compute_text()
            game_message = Message(protocol_definitions.GAME_UPDATE_PROTOCOL_TYPE_CODE, (game_text,))
            self.connection_table.send_message_to_entry(game_message, connection_information)
            self._send_text_message(f"{joiner_username} has joined your game!", other_player_username)

    def _notify_opponent_of_player_exit(self, connection_information, state):
        """Notifies the opponent of the current player exiting."""
        if state.current_game is not None:
            self._send_text_message_to_opponent(f"{state.username} has left your game!", state.username)
        

    def handle_game_quit(self, connection_information):
        state = self.connection_table.get_entry_state(connection_information)
        if state.current_game is not None:
            self._notify_opponent_of_player_exit(connection_information, state)
            state.current_game = None
        else:
            self._send_text_message(f"You are not in a game, so you cannot quit one.", connection_information)

    def _message_clients_about_game_ending(self, player_username, opponent_username, victory_condition, game: Game):
        player_outcome = game.compute_player_outcome(victory_condition, player_username)
        self.connection_table.send_message_to_entry(Message(protocol_definitions.GAME_ENDING_PROTOCOL_TYPE_CODE, (opponent_username, player_outcome)), player_username)
        opponent_outcome = game.compute_player_outcome(victory_condition, opponent_username)
        self._send_message_to_opponent(player_username, Message(protocol_definitions.GAME_ENDING_PROTOCOL_TYPE_CODE, (player_username, opponent_outcome)))

    def handle_game_move(self, move_number, connection_information):
        state = self.connection_table.get_entry_state(connection_information)
        game: Game = state.current_game
        if game is None:
            self._send_text_message("You are not in a game, so you cannot make moves.", connection_information)
        elif game.get_current_turn() != state.username:
            self._send_text_message("Not your turn.", connection_information)
        else:
            if game.make_move(state.username, move_number):
                game_text = game.compute_text()
                game_message = Message(protocol_definitions.GAME_UPDATE_PROTOCOL_TYPE_CODE, (game_text,))
                other_player_username = game.compute_other_player(state.username)
                self.connection_table.send_message_to_entry(game_message, connection_information)
                if other_player_username in self.usernames_to_connections:
                    other_player_connection_information = self.usernames_to_connections[other_player_username]
                    other_player_game_state = self.connection_table.get_entry_state(other_player_connection_information)
                    if other_player_game_state.current_game is not None and other_player_game_state.current_game.compute_other_player(other_player_username) == state.username:
                        self.connection_table.send_message_to_entry(game_message, other_player_connection_information)
                victory_condition = game.check_winner()
                if victory_condition is not None:
                    self._message_clients_about_game_ending(state.username, other_player_username, victory_condition, game)
            else:
                self._send_text_message("This tile is already taken.", connection_information)

    def cleanup_connection(self, connection_information):
        """Performs cleanup when a connection gets closed"""
        entry = self.connection_table.get_entry(connection_information)
        if entry is not None:
            state = entry.get_state()
            self._notify_opponent_of_player_exit(connection_information, state)
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
        self.selector.register(conn, selectors.EVENT_READ | selectors.EVENT_WRITE, data=connection_handler)
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
    parser = argparse.ArgumentParser(prog='server.py', description='The server program for hosting tictactoe games.', usage=f"usage: {sys.argv[0]} [-i <host>] -p <port>")
    parser.add_argument("-i", default="0.0.0.0")
    parser.add_argument("-p", type=int)
    arguments = parser.parse_args()

    #Handle the arguments
    if arguments.p is None:
        parser.print_usage()
        sys.exit(1)
    host, port = arguments.i, arguments.p

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
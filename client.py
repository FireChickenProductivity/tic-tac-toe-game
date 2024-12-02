#!/usr/bin/env python3

import sys
import socket
import time
import selectors
import traceback
import os
from threading import Thread
import argparse

import connection_handler
import logging_utilities
import protocol_definitions
import protocol
import game_actions
from commands import create_commands, CommandManager
import cryptography_boundary

def create_socket_from_address(target_address):
    """Creates a client socket that connects to the specified address"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    sock.connect_ex(target_address)
    return sock

class Client:
    #The default and maximum amount of time to wait in between reconnection attempts
    DEFAULT_RECONNECTION_TIMEOUT = 5
    MAXIMUM_RECONNECTION_TIMEOUT = 30
    def __init__(self, host, port, selector, logger, *, output_text_function = print, socket_creation_function = create_socket_from_address):
        """
            Handles the client side of interactions with a server
            host: the server's host address
            port: the server's port number
            selector: the selector to register the client with
            logger: the logger to use for logging significant occurrences or errors
            output_text_function: the function used to output text for the client. This is settable as an argument primarily to aid with testing
            socket_creation_function: the function used to create the socket from an address, which is settable to help with testing
        """
        self.username = None
        self.password = None
        self.current_piece = ""
        self.reconnection_timeout = self.DEFAULT_RECONNECTION_TIMEOUT
        self.host = host
        self.port = port
        self.current_game = None
        self.current_opponent = None
        self.output_text = output_text_function
        self.selector = selector
        self.logger = logger
        self.create_socket_from_address = socket_creation_function
        self._create_protocol_callback_handler()
        self._create_connection_handler()
        self.is_closed = False
        self.has_received_successful_message = False
        self.commands: CommandManager = create_commands(self)

    def handle_help_command(self, label):
        if self.commands.has_command(label):
            text = self.commands.get_command_help_message(label)
        else:
            text = f"Please choose a help topic by typing 'help' followed by one of the following commands: {self.commands.get_command_names_text()}."
            if label != "":
                text = f"{label} is not a command. " + text
        self.output_text("Help: " + text)

    def handle_game_ending(self, opponent_username, outcome):
        outcome_text = 'tie'
        if outcome == game_actions.LOSS:
            outcome_text = 'loss'
        elif outcome == game_actions.VICTORY:
            outcome_text = 'win'
        self.output_text(f"Your game with {opponent_username} ended with a {outcome_text}!")
        if opponent_username == self.current_opponent:
            self.reset_game_state()
            self.output_text("This game has ended.\nYou may start another game with the 'create' command and may quit the program using the 'exit' command.")

    def handle_game_update(self, game_text):
        """Updates the game state"""
        self.output_text("The game board is now:")
        self.current_game = game_text
        gamerow_1 = [' ',' ',' ','|',' ',' ',' ','|',' ',' ',' ']
        gamerow_2 = [' ',' ',' ','|',' ',' ',' ','|',' ',' ',' ']
        gamerow_3 = [' ',' ',' ','|',' ',' ',' ','|',' ',' ',' ']
        for index, character in enumerate(self.current_game):
            if character == ' ':
                continue
            match index + 1:
                case 1:
                    gamerow_1[1] = character
                case 2:
                    gamerow_1[5] = character
                case 3:
                    gamerow_1[9] = character
                case 4:
                    gamerow_2[1] = character
                case 5:
                    gamerow_2[5] = character
                case 6:
                    gamerow_2[9] = character
                case 7:
                    gamerow_3[1] = character
                case 8:
                    gamerow_3[5] = character
                case 9:
                    gamerow_3[9] = character
        srow_1 = "".join(gamerow_1)
        srow_2 = "".join(gamerow_2)
        srow_3 = "".join(gamerow_3)
        self.information_text = f"{self.username} ({self.current_piece}) vs {self.current_opponent} ({game_actions.compute_other_piece(self.current_piece)})"
        if not game_actions.check_winner(self.current_game):
            self.information_text += f"\n{game_actions.compute_current_player(self.current_game)}'s turn."
        self.output_text(self.information_text)
        self.output_text(srow_1 + "\n___|___|___ a\n" +
                         srow_2 + "\n___|___|___ b\n" +
                         srow_3 + "\n   |   |    c\n 1   2   3\n")

    def handle_game_piece_update(self, character):
        """Update the player's game piece"""
        self.current_piece = character
        self.output_text(f"You are playing as {self.current_piece}.")

    def handle_text_message(self, text):
        """Displays a text message from the server"""
        self.output_text("Server: " + text)

    def _create_protocol_callback_handler(self):
        """Creates the callback handler to let the client respond to the server"""
        self.protocol_callback_handler = protocol.ProtocolCallbackHandler()
        self.protocol_callback_handler.register_callback_with_protocol(self.handle_text_message, protocol_definitions.TEXT_MESSAGE_PROTOCOL_TYPE_CODE)
        self.protocol_callback_handler.register_callback_with_protocol(self.handle_game_update, protocol_definitions.GAME_UPDATE_PROTOCOL_TYPE_CODE)
        self.protocol_callback_handler.register_callback_with_protocol(self.handle_game_piece_update, protocol_definitions.GAME_PIECE_PROTOCOL_TYPE_CODE)
        self.protocol_callback_handler.register_callback_with_protocol(self.handle_game_ending, protocol_definitions.GAME_ENDING_PROTOCOL_TYPE_CODE)

    def _create_connection_handler(self):
        """Creates the connection handler for managing the connection with the server"""
        addr = (self.host, self.port)
        print("starting connection to", addr)
        sock = self.create_socket_from_address(addr)
        connection_information = connection_handler.ConnectionInformation(sock, addr)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        public_key = cryptography_boundary.load_public_key("public_rsa.pem")
        self.connection_handler = connection_handler.ConnectionHandler(
            self.selector,
            connection_information,
            self.logger,
            self.protocol_callback_handler,
            public_key,
        )
        self.selector.register(sock, events, data=self.connection_handler)

    def send_message(self, message: protocol.Message):
        """Sends the message to the server"""
        self.connection_handler.send_message(message)

    def close(self, should_reconnect=False):
        """Closes the connection with the server"""
        self.connection_handler.close()
        self.is_closed = not should_reconnect

    def pause_in_between_reconnection_attempts(self):
        """Waits as long as needed in between reconnection attempts and adjusts the timeout amount if needed"""
        if self.has_received_successful_message:
            self.reconnection_timeout = self.DEFAULT_RECONNECTION_TIMEOUT
            self.has_received_successful_message = False
        print(f"Waiting {self.reconnection_timeout} seconds before reconnecting.")
        time.sleep(self.reconnection_timeout)
        if self.reconnection_timeout < self.MAXIMUM_RECONNECTION_TIMEOUT:
            self.reconnection_timeout += 1

    def login(self):
        credentials = (self.username, self.password)
        self.send_message(protocol.Message(protocol_definitions.SIGN_IN_PROTOCOL_TYPE_CODE, credentials))

    def reconnect(self):
        """Attempts to reconnect to the server"""
        self.close(should_reconnect=True)
        done = False
        while not done:
            try:
                print("Trying to reconnect...")
                self._create_connection_handler()
                if self.has_attempted_login():
                    self.login()
                done = True
            except connection_handler.PeerDisconnectionException:
                done = False
                self.pause_in_between_reconnection_attempts()

    def reset_game_state(self):
        self.current_game = None
        self.current_piece = None
        self.current_opponent = None

    def handle_command(self, action, value):
        """Performs the specified client command"""
        if self.commands.has_command(action):
            self.commands.perform_command(action, value)
        else:
            self.output_text(f"The command '{action}' was not recognized. Valid commands are {self.commands.get_command_names_text()}")
    
    def set_credentials(self, username, password):
        self.username = username
        self.password = password

    def has_attempted_login(self):
        return self.username is not None

    def set_current_opponent(self, value):
        self.current_opponent = value

    def get_current_opponent(self):
        return self.current_opponent

    def get_current_game(self):
        return self.current_game

    def get_current_piece(self):
        return self.current_piece

    def perform_command_from_text_input(self, text: str):
        """Creates a request for the server from user input text"""
        text = text.strip()
        action_value_split = text.split(' ', maxsplit=1)
        action = action_value_split[0]
        value = ""
        #If an argument is detected for the action, put it inside value
        if len(action_value_split) > 1:
            value = action_value_split[1]
        self.handle_command(action, value)
    
    def run_selector_loop(self):
        """Responds to socket write and read events"""
        try:
            while not self.is_closed:
                events = self.selector.select(timeout=None)
                for key, mask in events:
                    message = key.data
                    try:
                        message.process_events(mask)
                        if mask & selectors.EVENT_READ:
                            self.has_received_successful_message = True
                    except connection_handler.PeerDisconnectionException:
                        print("Connection failure detected. Attempting reconnection...")
                        self.pause_in_between_reconnection_attempts()
                        self.reconnect()
                    except Exception:
                        self.logger.log_message(
                            f"main: error: exception for {message.connection_information.addr}:\n{traceback.format_exc()}",
                        )
                        message.close()
                # Check for a socket being monitored to continue.
                if not self.selector.get_map():
                    break
        except KeyboardInterrupt:
            print("caught keyboard interrupt, exiting")
        finally:
            self.close()

def perform_user_commands_through_connection(client: Client):
    """Loops taking input from the user and executing corresponding commands"""
    done = False
    while not done:
        user_input = input('')
        if user_input == 'exit':
            done = True
        else:
            client.perform_command_from_text_input(user_input)
    client.close()

def splash():
    """prints splash screen and game instructions"""
    print("        _____  _   __\n" +
            "         | |  | | / /`\n" +
            "         |_|  |_| \_\_,\n" +
            "       _____   __    __\n" +
            "        | |   / /\  / /`\n" +
            "        |_|  /_/--\ \_\_,\n" +
            "       _____  ___   ____\n" +
            "        | |  / / \ | |_\n" +
            "        |_|  \_\_/ |_|__\n")
    print("Welcome to Fire Chicken's Tic-Tac-Toe game!")
    print("To play, you will need to create an account and login.\n" +
            "Then, create a game or join someone else's.\n" + 
            "If you create a game, you must join it as well to start playing.\n\n" +
            "For help with commands, type 'help'.")

def main():
    """The entry point for the client program"""
    sel = selectors.DefaultSelector()
    os.makedirs("logs", exist_ok=True)
    client_logger = logging_utilities.FileLogger(os.path.join("logs", "client.log"), debugging_mode = False)

    parser = argparse.ArgumentParser(prog='client.py', description='The client program for playing tictactoe.', usage=f"usage: {sys.argv[0]} -i <host> -p <port>")
    parser.add_argument("-i")
    parser.add_argument("-p", type=int)
    arguments = parser.parse_args()

    if None in [arguments.i, arguments.p]:
        parser.print_usage()
        sys.exit(1)

    host, port = arguments.i, arguments.p

    connection = Client(host, port, sel, client_logger)
    splash()
    #Run the client input loop in a separate thread
    client_input_thread = Thread(target=perform_user_commands_through_connection, args=(connection,))
    client_input_thread.start()

    connection.run_selector_loop()

if __name__ == '__main__':
    main()
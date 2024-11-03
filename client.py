
#!/usr/bin/env python3

import sys
import socket
import time
import selectors
import traceback
import os
from threading import Thread
from game_manager import GameHandler

import connection_handler
import logging_utilities
import protocol_definitions
import protocol
import game_actions


def create_socket_from_address(target_address):
    """Creates a client socket that connects to the specified address"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    sock.connect_ex(target_address)
    return sock

def _parse_two_space_separated_values(text):
    """Parses text into 2 space separated values. Returns None on failure."""
    values = text.split(" ", maxsplit=1)
    if len(values) != 2:
        return None
    return values

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
        self.credentials = None
        self.reconnection_timeout = self.DEFAULT_RECONNECTION_TIMEOUT
        self.host = host
        self.port = port
        self.current_game = None
        self.output_text = output_text_function
        self.selector = selector
        self.logger = logger
        self.create_socket_from_address = socket_creation_function
        self._create_protocol_callback_handler()
        self._create_connection_handler()
        self.is_closed = False
        self.has_received_successful_message = False

    def update_game(self, values):
        """Updates the game state"""
        self.output_text("The game board is now:")
        self.current_game = values["text"]
        self.output_text("[" + self.current_game + "]")

    def handle_text_message(self, values):
        """Displays a text message from the server"""
        self.output_text("Server: " + values["text"])

    def _create_protocol_callback_handler(self):
        """Creates the callback handler to let the client respond to the server"""
        self.protocol_callback_handler = protocol.ProtocolCallbackHandler()
        self.protocol_callback_handler.register_callback_with_protocol(self.handle_text_message, protocol_definitions.TEXT_MESSAGE_PROTOCOL_TYPE_CODE)
        self.protocol_callback_handler.register_callback_with_protocol(self.update_game, protocol_definitions.GAME_UPDATE_PROTOCOL_TYPE_CODE)

    def _create_connection_handler(self):
        """Creates the connection handler for managing the connection with the server"""
        addr = (self.host, self.port)
        print("starting connection to", addr)
        sock = self.create_socket_from_address(addr)
        connection_information = connection_handler.ConnectionInformation(sock, addr)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self.connection_handler = connection_handler.ConnectionHandler(
            self.selector,
            connection_information,
            self.logger,
            self.protocol_callback_handler,
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

    def reconnect(self):
        """Attempts to reconnect to the server"""
        self.close(should_reconnect=True)
        done = False
        while not done:
            try:
                print("Trying to reconnect...")
                self._create_connection_handler()
                done = True
            except connection_handler.PeerDisconnectionException:
                done = False
                self.pause_in_between_reconnection_attempts()



    def create_request(self, action, value):
        """Creates a request for the server from an action value pair"""
        type_code = None
        values = None
        request = None
        if action == "help":
            if value:
                type_code = protocol_definitions.HELP_MESSAGE_PROTOCOL_TYPE_CODE
                values = (value,)
            else:
                type_code = protocol_definitions.BASE_HELP_MESSAGE_PROTOCOL_TYPE_CODE
                values = []
        elif action == "login":
            values = _parse_two_space_separated_values(value)
            if values is not None:
                type_code = protocol_definitions.SIGN_IN_PROTOCOL_TYPE_CODE
                self.credentials = values
        elif action == "register":
            values = _parse_two_space_separated_values(value)
            if values is not None:
                type_code = protocol_definitions.ACCOUNT_CREATION_PROTOCOL_TYPE_CODE
        elif action == "quit":
            if self.current_game is not None:
                type_code = protocol_definitions.QUIT_GAME_PROTOCOL_TYPE_CODE
                values = []
                self.current_game = None
        elif action == "join":
            if value != "" and self.current_game is None:
                type_code = protocol_definitions.JOIN_GAME_PROTOCOL_TYPE_CODE
                values = (value,)
        elif action == "create" and self.current_game is None:
            if value != "":
                type_code = protocol_definitions.GAME_CREATION_PROTOCOL_TYPE_CODE
                values = (value,)
        elif action == "move":
            if self.current_game and game_actions.is_valid_move_text(value):
                move_number = game_actions.convert_move_text_to_move_number(value)
                current_player = game_actions.compute_current_player(self.current_game)
                if current_player == self.username:
                    type_code = protocol_definitions.GAME_UPDATE_PROTOCOL_TYPE_CODE
                    values = (move_number,)
                    return protocol.Message(type_code, values)
            return None

        if type_code is not None:
            request = protocol.Message(type_code, values)
        return request

    def create_request_from_text_input(self, text: str):
        """Creates a request for the server from user input text"""
        text = text.strip()
        action_value_split = text.split(' ', maxsplit=1)
        action = action_value_split[0]
        value = ""
        #If an argument is detected for the action, put it inside value
        if len(action_value_split) > 1:
            value = action_value_split[1]
        request = self.create_request(action, value)
        return request
    
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
            request = client.create_request_from_text_input(user_input)
            if request is None:
                print('Command not recognized.')
            else:
                client.send_message(request)
    client.close()



def main():
    """The entry point for the client program"""
    sel = selectors.DefaultSelector()
    os.makedirs("logs", exist_ok=True)
    client_logger = logging_utilities.FileLogger(os.path.join("logs", "client.log"), debugging_mode = False)

    if len(sys.argv) != 3:
        print("usage:", sys.argv[0], "<host> <port>")
        sys.exit(1)

    host, port = sys.argv[1], int(sys.argv[2])

    connection = Client(host, port, sel, client_logger)
    #Run the client input loop in a separate thread
    client_input_thread = Thread(target=perform_user_commands_through_connection, args=(connection,))
    client_input_thread.start()

    connection.run_selector_loop()

if __name__ == '__main__':
    main()
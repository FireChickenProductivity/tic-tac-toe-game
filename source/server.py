
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
from connection_table import ConnectionTable, ConnectionTableEntry

os.makedirs("logs", exist_ok=True)
logger = logging_utilities.Logger(os.path.join("logs", "server.log"))

help_messages = {
    "": "The server will offer support for tictactoe games in the future. Help topics include\ngameplay\nsetup\n",
    "gameplay": "When the server supports tictactoe games, you submit your move by typing the coordinates for a position and pressing enter.",
    "setup": "When the server supports tictactoe games, you will create a game with the create command and join a game with the join command."
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

protocol_callback_handler.register_callback_with_protocol(create_help_message, protocol_definitions.BASE_HELP_MESSAGE_PROTOCOL_TYPE_CODE)
protocol_callback_handler.register_callback_with_protocol(create_help_message, protocol_definitions.HELP_MESSAGE_PROTOCOL_TYPE_CODE)

def cleanup_connection(connection_information):
    connection_table.remove_entry(connection_information)

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

sel = selectors.DefaultSelector()
connection_table = ConnectionTable()

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

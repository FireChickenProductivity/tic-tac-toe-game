
#!/usr/bin/env python3

import sys
import socket
import selectors
import traceback
import os

import connection_handler
import logging_utilities
import protocol_definitions
import protocol

sel = selectors.DefaultSelector()
os.makedirs("logs", exist_ok=True)
logger = logging_utilities.Logger(os.path.join("logs", "client.log"))

def create_request(action, value):
    if action == "help":
        if value:
            return protocol_definitions.HELP_MESSAGE_PROTOCOL_TYPE_CODE, (value,)
        else:
            return protocol_definitions.BASE_HELP_MESSAGE_PROTOCOL_TYPE_CODE, []

def create_connection(host, port):
    addr = (host, port)
    print("starting connection to", addr)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    sock.connect_ex(addr)
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    connection = connection_handler.ConnectionHandler(
        sel,
        connection_handler.ConnectionInformation(sock, addr),
        logger,
        protocol.ProtocolCallbackHandler(),
    )
    sel.register(sock, events, data=connection)
    return connection


if len(sys.argv) not in [4, 5]:
    print("usage:", sys.argv[0], "<host> <port> <action> [<value>]")
    sys.exit(1)

host, port = sys.argv[1], int(sys.argv[2])
action = sys.argv[3]
value = ""
if len(sys.argv) == 5:
    value = sys.argv[4]

# send messages to test connection persistence
type_code, request = create_request(action, value)
request_message = protocol.Message(type_code, request)
connection = create_connection(host, port)
connection.send_message(request_message)
new_type_code, new_request = create_request("help", "value")
new_request_message = protocol.Message(new_type_code, new_request)
connection.send_message(new_request_message)
new_type_code, new_request = create_request("help", "setup")
new_request_message = protocol.Message(new_type_code, new_request)
connection.send_message(new_request_message)
connection.send_message(request_message)


try:
    while True:
        events = sel.select(timeout=None)
        for key, mask in events:
            message = key.data
            try:
                message.process_events(mask)
            except Exception:
                logger.log_message(
                    f"main: error: exception for {message.connection_information.addr}:\n{traceback.format_exc()}",
                )
                message.close()
        # Check for a socket being monitored to continue.
        if not sel.get_map():
            break
except KeyboardInterrupt:
    print("caught keyboard interrupt, exiting")
finally:
    sel.close()

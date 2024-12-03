#Provides functionality for mocking sockets and socket management for the sake of automated testing

import connection_handler
import selectors

class MockInternet:
    def __init__(self):
        """Used by socket simulating classes to send information to each other"""
        self.sockets = {}

    def register_socket(self, address, socket):
        self.sockets[address] = socket

    def message_socket(self, address, message):
        target = self.sockets[address]
        target.receive_message_from_socket(message)

    def get_socket(self, address):
        return self.sockets[address]

    def connect_to_listening_socket(self, target_address, source_address):
        listening_socket = self.get_socket(target_address)
        return listening_socket.create_response_socket(source_address)

    def transmit_connection_closing(self, address):
        target = self.sockets[address]
        target.close()

    def create_socket_from_address(self, address, target_address):
        socket = MockTCPSocket(self, address)
        socket.connect_ex(target_address)
        return socket

    def create_listening_socket_from_address(self, address):
        socket = MockListeningSocket(self, address)
        socket.listen()
        return socket

class MockTCPSocket:
    SENDING_LIMIT = 1500
    def __init__(self, internet: MockInternet, address):
        """Simulates a TCP socket for testing purposes"""
        self.internet = internet
        self.address = address
        self.internet.register_socket(self.address, self)
        self.receive_buffer = b""
        self.open_for_reading = False
        self.open_for_writing = False
        self.has_closed = False
        self.peer = None
        self.has_received_termination_message = False
    
    def send(self, message_bytes):
        """Simulates sending the following bytes and returns the number of bytes sent"""
        bytes_to_send = message_bytes[:self.SENDING_LIMIT]
        self.internet.message_socket(self.peer.get_address(), bytes_to_send)
        return len(bytes_to_send)

    def recv(self, amount_of_bytes_to_receive: int):
        """Retrieves at most the amount of bytes to receive from the buffer. Returns None if the peer closes"""
        if self.has_closed:
            return None
        else:
            result = self.receive_buffer[:amount_of_bytes_to_receive]
            self.receive_buffer = self.receive_buffer[amount_of_bytes_to_receive:]
            return result
    
    def set_open_for_writing(self, value):
        self.open_for_writing = value

    def set_open_for_reading(self, value):
        self.open_for_reading = value

    def close(self):
        """Closes the connection"""
        self.send(b"")
        self.open_for_reading = False
        self.open_for_writing = False
        self.has_closed = True

    def connect_ex(self, address):
        """Connects to the specified address"""
        self.peer = self.internet.connect_to_listening_socket(address, self.address)

    def set_peer(self, peer):
        self.peer = peer

    def setblocking(self, value):
        pass

    def receive_message_from_socket(self, message):
        self.receive_buffer += message
        if message == b"":
            self.has_received_termination_message = True

    def get_address(self):
        return self.address

    def get_peer_address(self):
        return self.peer.get_address()

    def has_received_bytes(self):
        return len(self.receive_buffer) > 0 or self.has_received_termination_message

    def is_listening_socket(self):
        return False

    def is_open_for_writing(self):
        return self.open_for_writing


class MockListeningSocket:
    def __init__(self, internet: MockInternet, address):
        """Simulates a listening socket that creates connections"""
        self.internet = internet
        self.address = address
        self.internet.register_socket(self.address, self)
        self.last_port_used = self.address[1]
        self.is_listening = False
        self.is_open_for_reading = False
        self.open_for_writing = False
        self.created_sockets = []

    def set_open_for_reading(self, value):
        self.is_open_for_reading = value

    def set_open_for_writing(self, value):
        self.open_for_writing = value

    def setsockopt(self, *args):
        pass

    def bind(self, address):
        self.address = address

    def listen(self):
        self.is_listening = True

    def setblocking(self, value):
        pass

    def create_response_socket(self, address):
        if self.is_listening and self.is_open_for_reading:
            self.last_port_used += 1
            host = self.address[0]
            new_socket = MockTCPSocket(self.internet, (host, self.last_port_used))
            peer = self.internet.get_socket(address)
            new_socket.set_peer(peer)
            self.created_sockets.append(new_socket)
            return new_socket

    def accept(self):
        next_socket = self.created_sockets.pop()
        return next_socket, next_socket.get_peer_address()

    def has_received_bytes(self):
        return len(self.created_sockets) > 0

    def is_listening_socket(self):
        return False

    def is_open_for_writing(self):
        return self.open_for_writing

class MockKey:
    def __init__(self, data, socket):
        self.data = data
        self.fileobj = socket
        

    #The equality method and hash method must be implemented to use this as a dictionary key
    def __eq__(self, other) -> bool:
        return isinstance(other, MockKey) and self.fileobj == other.fileobj

    def __hash__(self):
        return hash(self.fileobj)

class MockSelector:
    def __init__(self):
        self.sockets = {}

    def select(self, timeout=None):
        results = []
        for key in self.sockets:
            socket = key.fileobj
            if socket.has_received_bytes():
                result_key = MockKey(None, None, socket) if socket.is_listening_socket() else key
                results.append((result_key, selectors.EVENT_READ))
            if socket.is_open_for_writing():
                results.append((key, selectors.EVENT_WRITE))
        return results

    def register(self, socket, flags, data: connection_handler.ConnectionHandler):
        key = MockKey(data, socket)
        self.modify(socket, flags, data)
        self.sockets[key] = data

    def apply_operation_on_key_corresponding_to_socket(self, socket, operation):
        for key in self.sockets:
            if key.fileobj == socket:
                return operation(key)

    def unregister(self, socket):
        def perform_un_registration(key):
            self.sockets.pop(key)
        self.apply_operation_on_key_corresponding_to_socket(perform_un_registration, socket)

    def modify(self, socket, mode, data):
        is_mode_matching_both = mode == selectors.EVENT_READ | selectors.EVENT_WRITE
        socket.set_open_for_reading(mode == selectors.EVENT_READ or is_mode_matching_both)
        socket.set_open_for_writing(mode == selectors.EVENT_WRITE or is_mode_matching_both)

    def close(self):
        pass

    def get_map(self):
        return self.sockets
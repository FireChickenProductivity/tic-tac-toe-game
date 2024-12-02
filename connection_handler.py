import selectors
from threading import Lock

import protocol
from protocol import Message
import protocol_definitions
import cryptography_boundary

RECEIVING_MESSAGE_LOG_CATEGORY = "receiving"
SENDING_MESSAGE_LOG_CATEGORY = "sending"

class MessageEvent:
    def __init__(self, message, address):
        """Represents a message associated with an address that was sent or received"""
        self.message = message
        self.address = address

    def __str__(self) -> str:
        return str(self.message) + ", " + str(self.address)

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return isinstance(other, MessageEvent) and \
            self.address == other.address and \
            self.message == other.message

class PeerDisconnectionException(Exception):
    pass

class ConnectionInformation:
    """Class for keeping track of a socket and address"""
    def __init__(self, sock, addr):
        self.sock = sock
        self.addr = addr
        ip_address, port = self.addr
        self.text_representation = f"{ip_address}:{port}"

def convert_every_n_bytes(conversion_function, n, input_bytes):
    i = 0
    result = b""
    while i < len(input_bytes):
        relevant_bytes = input_bytes[i:i + n]
        converted_bytes = conversion_function(relevant_bytes)
        result += converted_bytes
        i += n
    return result

class MessageSender:
    def __init__(self, logger, connection_information: ConnectionInformation, protocol_map, close_callback):
        """A message sender is responsible for transmitting a message as bytes to a connection peer
            logger: a logger object for logging errors and significant occurrences
            connection_information: the connection information to use for transmitting messages
            protocol_map: a protocol map for converting messages to bytes
            close_callback: the call back to call to close the current connection
        """
        self.logger = logger
        self.sock = connection_information.sock
        self.addr = connection_information.addr
        self.buffer = b""
        self.protocol_map = protocol_map
        self.close_callback = close_callback
        self.encryption_function = None
        self.block_size = 0

    def set_encryption_function(self, value, block_size):
        self.encryption_function = value
        self.block_size = block_size
    
    def write(self):
        """Writes bytes in the buffer to the connection socket"""
        if self.buffer:
            try:
                # Should be ready to write
                sent = self.sock.send(self.buffer)
            except BlockingIOError:
                # Resource temporarily unavailable (errno EWOULDBLOCK)
                pass
            except OSError as exception:
                print("Error: A Connection Failure Occurred!")
                self.logger.log_message(f"{exception} trying to connect to {self.addr}")
                self.close_callback()
            else:
                self.buffer = self.buffer[sent:]

    def send_message(self, message: Message):
        """Starts transmitting the message with specified type code and values to the connection peer"""
        message_bytes = self.protocol_map.pack_values_given_type_code(message.type_code, *message.values)
        encrypted_bytes = convert_every_n_bytes(self.encryption_function, self.block_size, message_bytes)
        self.buffer += encrypted_bytes
        self.logger.handle_debug_message(MessageEvent(message, self.addr), SENDING_MESSAGE_LOG_CATEGORY)

class MessageReceiver:
    def __init__(self, logger, connection_information: ConnectionInformation, receiving_protocol_map: protocol.ProtocolMap, close_callback, wait_before_handling_second_block=False):
        """
            Converts messages received over a connection into Message objects
            logger: a logger object for logging errors and significant occurrences
            connection_information: information on the connection used to receive bytes
            message_handler: a protocol map for handling received messages
            close_callback: a callback function to use to close the current connection
            wait_before_handling_second_block: does not let the receiver process the second block until it is told it is ready. This is usually set when the first block contains cryptographic information that must be processed before handling later blocks
        """
        self.logger = logger
        self.sock = connection_information.sock
        self.addr = connection_information.addr
        self.message_handler: protocol.MessageHandler = protocol.MessageHandler(receiving_protocol_map)
        self.encrypted_buffer = b""
        self.buffer = b""
        self.messages = []
        self.close_callback = close_callback
        self.decryption_function = None
        self.block_size = 0
        self.ready_for_second_block = not wait_before_handling_second_block
        self.has_handled_first_block = False
        self.read_lock = Lock()
        self.data_processing_lock = Lock()

    def can_now_handle_second_block(self):
        self.ready_for_second_block = True

    def set_decryption_function(self, value, block_size):
        self.decryption_function = value
        self.block_size = block_size

    def _read(self):
        """Puts data from the socket into the buffer"""
        try:
            # Should be ready to read
            data = self.sock.recv(4096)
        except BlockingIOError:
            # Resource temporarily unavailable (errno EWOULDBLOCK)
            pass
        except OSError as exception:
            print('Error: A Connection Failure Occurred!')
            self.logger.log_message(f"{exception} trying to connect to {self.addr}")
            self.close_callback()
            raise PeerDisconnectionException("Peer closed.")
        else:
            if data:
                self.encrypted_buffer += data
            else:
                raise PeerDisconnectionException("Peer closed.")

    def process_already_received_data(self):
        is_acquired = self.data_processing_lock.acquire(blocking=False)
        if is_acquired:
            #This loop is necessary because the selector will only call read when bytes are received, 
            #so this is needed to handle messages that arrived in the same chunk of bytes
            while len(self.encrypted_buffer) >= self.block_size and (self.ready_for_second_block or not self.has_handled_first_block):
                self.process_message()
                self.has_handled_first_block = True
            self.data_processing_lock.release()

    def read(self):
        """Processes newly received bytes"""
        try:
            is_acquired = self.read_lock.acquire(blocking=False)
            if is_acquired:
                self._read()
                self.process_already_received_data()
                self.read_lock.release()
        except Exception as e:
            self.read_lock.release()
            raise e
        
    def process_complete_message(self):
        """Finishes handling a completed message"""
        #Extract the information from the message handler
        values = self.message_handler.get_values()
        type_code = self.message_handler.get_protocol_type_code()
        content_length = self.message_handler.get_number_of_bytes_extracted()
        
        #Have the message handler prepare for receiving the next message
        self.message_handler.prepare_for_next_message()

        #Add the message to the queue to be processed
        message = Message(type_code, values)
        self.messages.append(message)

        self.logger.handle_debug_message(MessageEvent(message, self.addr), RECEIVING_MESSAGE_LOG_CATEGORY)

        #Remove the processed bytes from the buffer
        if len(self.buffer) > 0:
            self.buffer = self.buffer[content_length:]

    def process_message(self):
        """Converts bytes into messages"""
        encrypted_data = self.encrypted_buffer[0:self.block_size]
        self.buffer += self.decryption_function(encrypted_data)
        self.encrypted_buffer = self.encrypted_buffer[self.block_size:]
        self.message_handler.receive_bytes(self.buffer)
        if self.message_handler.is_done_obtaining_values():
            self.process_complete_message()
        else:
            self.buffer = b""

    def has_processed_messages(self):
        """Returns true if the bytes have been converted into at least one complete message"""
        return len(self.messages) > 0

    def extract_message(self) -> Message:
        """Extracts the next complete message. Messages are extracted in the order in which they are received."""
        message = self.messages.pop(0)
        return message

    def has_unprocessed_data(self):
        return self.encrypted_buffer

def compute_sending_and_receiving_protocol_maps(is_server):
    """Properly chooses which protocol map is for receiving and which is for sending based on if this is for the server or client"""
    if is_server:
        sending_protocol_map = protocol_definitions.CLIENT_PROTOCOL_MAP
        receiving_protocol_map = protocol_definitions.SERVER_PROTOCOL_MAP
    else:
        sending_protocol_map = protocol_definitions.SERVER_PROTOCOL_MAP
        receiving_protocol_map = protocol_definitions.CLIENT_PROTOCOL_MAP
    return sending_protocol_map, receiving_protocol_map
    

class ConnectionHandler:
    #* as an argument is not something you pass in. It just means that the following arguments must be named explicitly when giving them values
    def __init__(self, selector, connection_information: ConnectionInformation, logger, callback_handler: protocol.ProtocolCallbackHandler, asymmetric_key, *, is_server: bool=False, on_close_callback=None):
        """
            selector: the selector object that the connection handler is registered with
            connection_information: the information used to exchange information with the peer
            logger: a logger for logging noteworthy events and errors
            callback_handler: the callback handler is used to respond to request messages
            is_server: must be assigned values explicitly. Determines if this is for a client or server
            on_close_callback: must be assigned values explicitly. Called when the connection is closed using connection_information
            asymmetric_key: asymmetric key used for key exchange with the peer
        """
        self.selector = selector
        self.connection_information = connection_information
        self.is_server = is_server
        self.logger = logger
        self.callback_handler = callback_handler
        self.on_close_callback = on_close_callback

        #Pick the correct protocol maps based on if this is the client or the server
        sending_protocol_map, receiving_protocol_map = compute_sending_and_receiving_protocol_maps(is_server)
        self.receiving_protocol_map = receiving_protocol_map
        self.message_receiver = MessageReceiver(self.logger, self.connection_information, receiving_protocol_map, self.close, wait_before_handling_second_block=self.is_server)
        self.message_sender = MessageSender(self.logger, self.connection_information, sending_protocol_map, self.close)

        if self.is_server:
            self.message_receiver.set_decryption_function(lambda x: cryptography_boundary.decrypt_data_using_private_key(x, asymmetric_key), cryptography_boundary.RSA_BLOCK_SIZE)
        else:
            self.message_sender.set_encryption_function(lambda x: cryptography_boundary.encrypt_data_using_public_key(x, asymmetric_key), cryptography_boundary.RSA_BLOCK_SIZE)
            self._create_symmetric_key()

    def _create_symmetric_key(self):
        parameters = cryptography_boundary.create_symmetric_key_parameters()
        self.send_message(Message(protocol_definitions.SYMMETRIC_KEY_TRANSMISSION_PROTOCOL_TYPE_CODE, parameters))
        self.set_symmetric_key(parameters)

    def set_symmetric_key(self, parameters):
        encryption_function, decryption_function = cryptography_boundary.create_symmetric_key_encryptor_and_decryptor_from_number_and_input_vector(*parameters)
        self.message_receiver.set_decryption_function(decryption_function, cryptography_boundary.SYMMETRIC_BLOCK_SIZE)
        self.message_sender.set_encryption_function(encryption_function, cryptography_boundary.SYMMETRIC_BLOCK_SIZE - 1)
        self.message_receiver.can_now_handle_second_block()
        self.message_receiver.process_already_received_data()

    def _set_selector_events_mask(self, mode):
        """Set selector to listen for events."""
        self.selector.modify(self.connection_information.sock, mode, data=self)

    def respond_to_request(self, request: Message):
        """Responds to the request message"""
        if self.is_server:
            values = []
            values.extend(request.values)
            values.append(self.connection_information)
        else:
            values = request.values
        self.callback_handler.pass_values_to_protocol_callback(values, request.type_code)

    def respond_to_received_message(self):
        """This responds to a request by extracting the message from the message receiver and transmits any responses if needed"""
        request = self.message_receiver.extract_message()
        if self.callback_handler.has_protocol(request.type_code):
            self.respond_to_request(request)
        elif request.type_code == protocol_definitions.SYMMETRIC_KEY_TRANSMISSION_PROTOCOL_TYPE_CODE:
            self.set_symmetric_key(request.values)
        else:   
            print("Unidentified protocol received", request.type_code, f"values: {request.values}")
        
    def read(self):
        """Responds to the selector notifying the handler that bytes have been received from the peer"""
        self.message_receiver.read()
        while self.message_receiver.has_processed_messages():
            self.respond_to_received_message()

    def send_message(self, request: Message):
        """Sends a message to the peer"""
        self.message_sender.send_message(request)

    def process_events(self, mask):
        """Processes events from the selector managing the connection socket"""
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.message_sender.write()
    
    def close(self):
        """Cleans up the connection"""
        self.logger.log_message(f"closing connection to {self.connection_information.addr}")
        try:
            self.selector.unregister(self.connection_information.sock)
        except Exception as e:
            self.logger.log_message(f"error: selector.unregister() exception for {self.connection_information.addr}: {repr(e)}")
        try:
            if self.connection_information.sock is not None: 
                self.connection_information.sock.close()
        except OSError as e:
            self.logger.log_message(f"error: socket.close() exception for {self.connection_information.addr}: {repr(e)}")
        finally:
            # Delete reference to socket object for garbage collection
            self.connection_information.sock = None
            if self.on_close_callback is not None:
                self.on_close_callback(self.connection_information)
        
    def get_connection_information(self):
        return self.connection_information
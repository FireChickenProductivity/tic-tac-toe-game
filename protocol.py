#Provides code for dealing with protocols

from protocol_fields import *
from protocol_type_codes import *
from packing_utilities import *
from message_protocol import *

#Constants
USERNAME_LENGTH_FIELD_SIZE_IN_BYTES = 1
PASSWORD_LENGTH_FIELD_SIZE_IN_BYTES = 1

#Classes for dealing with protocols

class Message:
    def __init__(self, type_code, values=None):
        """Class for keeping track of type the code and message values for a message. Values can be omitted, a list, a tuple, or a single value"""
        self.type_code = type_code
        self.values = values
        if values is None:
            self.values = []
        elif type(self.values) not in [tuple, list]:
            self.values = (self.values,)

    def __str__(self):
        return f"Type Code: {self.type_code}, Values: {self.values}"

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return isinstance(other, Message) and \
            other.type_code == self.type_code and \
            other.values == self.values

class ProtocolMap:
    """Maps between type codes and protocols"""
    def __init__(self, protocols):
        """protocols: an iterable of MessageProtocols"""
        self.map = {}
        for protocol in protocols:
            self.map[protocol.get_type_code()] = protocol
        
    def get_protocol_with_type_code(self, code: int):
        """Returns the protocol with the associated type code"""
        return self.map[code]
    
    def has_protocol_with_type_code(self, code: int):
        """Returns true if the map has a protocol with the specified type code and false otherwise"""
        return code in self.map

    def pack_values_given_type_code(self, code: int, *values):
        """
            Packs values for a message protocol into bytes
            code: the type code for the protocol
            values: the values to pack
        """
        message_protocol = self.get_protocol_with_type_code(code)
        result = message_protocol.pack(*values)
        return result
    
class MessageHandler:
    """
        A message handler object is used to parse bytes being sent as part of a message utilizing a protocol map.
        This handles when are not all sent at the same time.
        protocol_map: a protocol map object containing message protocols that the handler should handle.
        How to use:
            Pass bytes to the message handler using the receive_bytes method.
            Figure out if the handler is done parsing the message or needs more bytes using the is_done_obtaining_values method.
            Get the parsed values as a list using the get_values method.
            Get the parsed type code using get_protocol_type_code.
            Get the number of bytes that were extracted as part of the message using the get_number_of_bytes_extracted method.
            Tell it to prepare for the next message using the prepare_for_next_message method after you extract these values.
    """
    def __init__(self, protocol_map: ProtocolMap):
        self.protocol_map = protocol_map
        self._initialize()
    
    def _initialize(self, protocol = None):
        self.bytes = None
        self.protocol: MessageProtocol = protocol
        self.values = []
        self.field_index = -1
        self.bytes_index = 0
        self.next_expected_size = None
        self.is_done = False

    def _update_bytes(self, input_bytes):
        if self.bytes:
            self.bytes += input_bytes
        else:
            self.bytes = input_bytes

    def _update_values_based_on_fieldless_protocol(self):
        self.values = []
        self.is_done = True

    def _update_next_expected_size(self):
        """
            Store the next expected field size if the field is fixed length.
            Otherwise, set the next expected size to None since the next field size needs to be parsed still.
        """
        if self.protocol.is_field_fixed_length(self.field_index):
            self.next_expected_size = self.protocol.compute_fixed_length_field_length(self.field_index)
        else:
            self.next_expected_size = None

    def _advance_field(self):
        """Starts parsing the next field"""
        if self.field_index >= 0 and self.field_index < self.protocol.get_number_of_fields():
            #Unpack the current field considering if it is fixed length
            if self.protocol.is_field_fixed_length(self.field_index):
                value = self.protocol.unpack_fixed_length_field(
                    self.field_index,
                    self.bytes,
                    self.bytes_index
                )
            else:
                value = self.protocol.unpack_variable_length_field(
                    self.field_index,
                    self.next_expected_size,
                    self.bytes,
                    self.bytes_index
                )
                
            self.values.append(value)
            self.bytes_index += self.next_expected_size
        self.field_index += 1
        if self.field_index >= self.protocol.get_number_of_fields():
            self.is_done = True
        else:
            self._update_next_expected_size()

    def _update_values_based_on_message_protocol_with_fields(self):
        """Parse as much of the message as possible"""
        #If no processing has been done yet, advance field to get information on the first field
        if self.field_index < 0:
            self._advance_field()
        data_is_left_that_can_be_processed = True
        while data_is_left_that_can_be_processed and not self.is_done:
            number_of_new_bytes = len(self.bytes) - self.bytes_index
            #If the expected size of the next field has not been identified yet, compute it first
            if not self.next_expected_size and number_of_new_bytes >= self.protocol.compute_variable_length_field_max_size(self.field_index):
                self.next_expected_size = self.protocol.unpack_field_length(
                    self.field_index,
                    self.bytes,
                    self.bytes_index
                )
                size_field_size_in_bytes = self.protocol.compute_variable_length_field_max_size(self.field_index)
                self.bytes_index += size_field_size_in_bytes
                number_of_new_bytes -= size_field_size_in_bytes
            #If the expected size of the next field has been identified, process the next field
            if self.next_expected_size and number_of_new_bytes >= self.next_expected_size:
                self._advance_field()
            else:
                data_is_left_that_can_be_processed = False

    def _update_values(self):
        if self.protocol.get_number_of_fields() == 0:
            self._update_values_based_on_fieldless_protocol()
        else:
            self._update_values_based_on_message_protocol_with_fields()

    def receive_bytes(self, input_bytes):
        if not self.protocol and len(input_bytes) >= TYPE_CODE_SIZE:
            self._update_protocol(input_bytes)
            input_bytes = compute_message_after_type_code(input_bytes)
        self._update_bytes(input_bytes)
        self._update_values()

    def _update_protocol(self, input_bytes):
        type_code = unpack_type_code_from_message(input_bytes)
        protocol = self.protocol_map.get_protocol_with_type_code(type_code)
        self._initialize(protocol)

    def is_done_obtaining_values(self):
        return self.is_done
    
    def get_protocol_type_code(self):
        return self.protocol.get_type_code()

    def prepare_for_next_message(self):
        self.protocol = None
        self.is_done = False

    def get_values(self):
        return self.values
    
    def get_number_of_bytes_extracted(self):
        return self.bytes_index + TYPE_CODE_SIZE

class ProtocolCallbackHandler:
    """Used to map between the callback functions to be called when a message corresponding to a protocol is received"""
    def __init__(self):
        self.callbacks = {}
    
    def register_callback_with_protocol(self, callback, protocol_type_code):
        """
            Registers a callback with a type code
            callback: a callback function that receives values corresponding to a message in the protocol in a dictionary
            mapping field names to values
            protocol_type_code: the type code for the corresponding protocol
        """
        self.callbacks[protocol_type_code] = callback
    
    def pass_values_to_protocol_callback(self, values, protocol_type_code):
        """
            Calls the specified callback with the corresponding values
            values: a list of values to pass to the callback in order
            protocol_type_code: the type code for the corresponding protocol
        """
        return self.callbacks[protocol_type_code](*values)

    def has_protocol(self, protocol_type_code):
        """
            Returns true if there is a callback in the handler corresponding to the protocol type code
            and false otherwise
            protocol_type_code: the type code for the corresponding protocol
        """
        return protocol_type_code in self.callbacks

#Functions for defining protocols

def create_text_message_protocol(type_code: int):
    """
        Returns a message protocol with the specified type code for messages having a single variable length string field
    """
    field = create_string_protocol_field(2)
    protocol = MessageProtocol(type_code, field)
    return protocol

def create_single_byte_nonnegative_integer_message_protocol(type_code: int):
    """
        Returns a message protocol with the specified type code for messages having a single nonnegative single byte integer field
    """
    field = create_single_byte_nonnegative_integer_protocol_field()
    protocol = MessageProtocol(type_code, field)
    return protocol

def create_username_and_password_message_protocol(type_code: int):
    """
        Returns a message protocol for a username and password field
    """
    user_name_field = create_string_protocol_field(USERNAME_LENGTH_FIELD_SIZE_IN_BYTES)
    password_field = create_string_protocol_field(PASSWORD_LENGTH_FIELD_SIZE_IN_BYTES)
    protocol = MessageProtocol(type_code, ((user_name_field, password_field)))
    return protocol

def create_username_message_protocol(type_code: int):
    """
        Returns a message protocol for communicating a username
    """
    user_name_field = creates_single_byte_length_field_string_protocol_field()
    protocol = MessageProtocol(type_code, user_name_field)
    return protocol

def create_fixed_length_string_message_protocol(type_code: int, length: int):
    """
        Returns a message protocol for communicating a fixed length string
        type_code: the protocol type code
        length: the length of fixed length strings obeying the protocol
    """
    field = create_fixed_length_string_protocol_field(length)
    protocol = MessageProtocol(type_code, field)
    return protocol

def create_nine_character_single_string_message_protocol(type_code: int):
    """
        Returns a message protocol for communicating a length 9 string
    """
    return create_fixed_length_string_message_protocol(type_code, 9)

def create_single_character_string_message_protocol(type_code: int):
    """
        Returns a message protocol for communicating a single character string
    """
    return create_fixed_length_string_message_protocol(type_code, 1)

def create_username_and_single_character_message_protocol(type_code: int):
    """
        Returns a message protocol for communicating a username followed by a single character
    """
    username_field = create_string_protocol_field(USERNAME_LENGTH_FIELD_SIZE_IN_BYTES)
    single_character_field = create_single_character_string_protocol_field()
    return MessageProtocol(type_code, [username_field, single_character_field])

def create_symmetric_key_message_protocol(type_code: int):
    initialization_vector_field = create_sixteen_byte_integer_protocol_field()
    number_field = create_thirty_two_byte_integer_protocol_field()
    return MessageProtocol(type_code, [number_field, initialization_vector_field])
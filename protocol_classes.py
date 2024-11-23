from packing_utilities import *
from protocol_type_codes import *
from protocol_fields import ProtocolField

class MessageProtocol:
    """
        A message protocol object defines how to convert between values associated with a message for the protocol
        type_code: an integer number used to distinguish between different message protocols. 
        Every MessageProtocol objects should have a unique type code.
        The type code is sent with every message conforming to the protocol.
        fields: an optional list of fields or a single field. 
        Every field object defines the type of value that should go in the field
        as well as the number of bytes the field can have. 
    """
    def __init__(self, type_code, fields=None):
        if not fields:
            fields = []
        elif isinstance(fields, ProtocolField):
            fields = [fields]
        self.type_code = type_code
        self.fields = fields
    
    def get_type_code(self):
        """Returns the type code for the message protocol"""
        return self.type_code

    def pack(self, *args):
        """Pacs values into a message conforming to the protocol"""
        args = [encode_value(value) for value in args]
        values_bytes = pack_type_code(self.type_code)
        for index, field in enumerate(self.fields):
            if field.is_fixed_length():
                field_bytes = struct.pack(">" + field.compute_struct_text(), args[index])
            else:
                field_bytes = struct.pack(">" + field.compute_struct_text_from_value(args[index]), args[index])
                size = len(field_bytes)
                size_bytes = struct.pack(">" + compute_format_representation_for_size(field.get_max_size()), size)
                field_bytes = size_bytes + field_bytes
            values_bytes += field_bytes
        return values_bytes
    
    def is_field_fixed_length(self, i):
        """Returns true if the field at index i is fixed length and false otherwise"""
        return self.fields[i].is_fixed_length()

    def compute_fixed_length_field_length(self, i):
        """Returns the field length for the field at index i assuming that it is fixed length"""
        field = self.fields[i]
        return field.get_size()
    
    def compute_variable_length_field_max_size(self, i):
        """Returns the maximum field length for the field at index i assuming that it is variable length"""
        field = self.fields[i]
        return field.get_max_size()
        
    def unpack_field_length(self, i, input_bytes, starting_index):
        """
            Unpacks a field length into an integer value
            i: the index of the corresponding field
            input_bytes: part of a message in bytes corresponding to the protocol
            starting_index: the start of the bytes in the message containing the field length
        """
        maximum_size = self.compute_variable_length_field_max_size(i)
        relevant_bytes = input_bytes[starting_index: starting_index + maximum_size]
        return struct.unpack(">" + compute_format_representation_for_size(maximum_size), relevant_bytes)[0]

    def unpack_variable_length_field(self, i, length, input_bytes, starting_index):
        """
            Unpacks a variable length field value
            i: the index for the field
            length: the length of the field value
            input_bytes: part of a message in bytes corresponding to the protocol
            starting_index: the start of the bytes in the message containing the value
        """
        field = self.fields[i]
        relevant_bytes = input_bytes[starting_index: starting_index + length]
        return decode_value(struct.unpack(">" + field.compute_struct_text(length), relevant_bytes)[0])
    
    def unpack_fixed_length_field(self, i, input_bytes, starting_index):
        """
            Unpacks bytes corresponding to a fixed length field
            i: the index for the field
            input_bytes: part of a message in bytes corresponding to the protocol
            starting_index: the start of the bytes in the message containing the value
        """
        field = self.fields[i]
        length = self.compute_fixed_length_field_length(i)
        relevant_bytes = input_bytes[starting_index: starting_index + length]
        return decode_value(struct.unpack(">" + field.compute_struct_text(), relevant_bytes)[0])
    
    def get_number_of_fields(self):
        """Returns the number of fields corresponding to the protocol"""
        return len(self.fields)
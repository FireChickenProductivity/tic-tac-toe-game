import struct
from packing_utilities import decode_value

class ProtocolField:
    """
        Interface definition for a protocol field. 
    """
    def compute_struct_text(self):
        """Gives the text used to represent the field in a struct.pack or struct.unpack call"""
        pass

    def is_fixed_length(self):
        """Returns true if the field is fixed length and false otherwise"""
        return True

class ConstantLengthProtocolField(ProtocolField):
    """
        Defines a constant length protocol field.
        struct_text: the text used with struct to pack and unpack values for this field
        size: the size of the field in bytes
        encoding_function: an optional function for encoding the value before packing
        decoding_function: an optional function for decoding the value after packing
    """
    
    def __init__(self, struct_text: str, size: int, encoding_function=None, decoding_function=decode_value):
        self.struct_text = struct_text
        self.size = size
        self.encoding_function = encoding_function
        self.decoding_function = decoding_function

    def pack(self, value):
        if self.encoding_function:
            value = self.encoding_function(value)
        return struct.pack(">" + self.compute_struct_text(), value)

    def unpack(self, input_bytes):
        value = struct.unpack(">" + self.compute_struct_text(), input_bytes)[0]
        if self.decoding_function:
            value = self.decoding_function(value)
        return value

    def compute_struct_text(self):
        """Returns the text used to pack or unpack values of this field with the struct module"""
        return self.struct_text
    
    def get_size(self):
        """Returns the size of the field in bytes"""
        return self.size
    
class VariableLengthProtocolField(ProtocolField):
    """
        Defines a variable length protocol field. 
        create_struct_text: a function that computes the appropriate text for packing and unpacking values for the field
        as a function of the field size in bytes.
        max_size: the maximum size of the field in bytes
    """
    def __init__(self, create_struct_text, max_size: int = 1):
        self.create_struct_text = create_struct_text
        self.max_size = max_size
    
    def compute_struct_text(self, size):
        """Returns the text for packing and unpacking values of the field is a function of the size"""
        return self.create_struct_text(size)
    
    def compute_struct_text_from_value(self, value):
        """Returns the text for packing and unpacking values of the field is a function of the value to pack or unpack"""
        return self.compute_struct_text(len(value))

    def get_max_size(self):
        """Returns the maximum size of the field in bytes"""
        return self.max_size
    
    def is_fixed_length(self):
        return False

def create_string_protocol_field(max_size_in_bytes):
    """
        Creates a protocol field for a string value as a function of the maximum size in bytes
        max_size_in_bytes: the maximum size of the field in bytes
    """
    def create_struct_text(size):
        return str(size) + "s"
    field = VariableLengthProtocolField(create_struct_text, max_size_in_bytes)
    return field

def creates_single_byte_length_field_string_protocol_field():
    """
        Creates a protocol field for a variable length string where the length is contained in a single byte field
    """
    return create_string_protocol_field(1)

def create_single_byte_nonnegative_integer_protocol_field():
    """
        Creates a protocol field for nonnegative integer values that fit in a single byte
    """
    field = ConstantLengthProtocolField("B", 1)
    return field

def create_fixed_length_string_protocol_field(size):
    """Creates a fixed length string protocol field with specified size"""
    if size > 1:
        size_text = str(size) + "s"
    else:
        size_text = "s"
    field = ConstantLengthProtocolField(size_text, size)
    return field

def create_single_character_string_protocol_field():
    return create_fixed_length_string_protocol_field(1)

def create_large_fixed_length_integer_protocol_field(size_in_bytes):
    pass
#Utility functions for packing and unpacking bytes

def compute_format_representation_for_size(size: int):
    """
        Computes the appropriate format string representation for the size of a field
        size: the desired size in number of bytes
        Currently only sizes 1, 2, 4 and 8 are supported.
    """
    if size == 1:
        return 'B'
    elif size == 2:
        return 'H'
    elif size == 4:
        return 'I'
    elif size == 8:
        return 'L'
    else:
        raise ValueError("Tried to create byte format string text for invalid size! Must be 1, 2, 4, or 8!")

def encode_value(value):
    """
        Encodes a value into an appropriate byte format for packing it
        value: a value to be packed into bytes
    """
    if type(value) == str:
        return value.encode("utf-8")
    return value

def decode_value(value):
    """
        Decodes a value unpacked if it is still in byte format
        value: an unpacked value that might still be in byte format and need to be decoded
    """
    if type(value) == bytes:
        return value.decode("utf-8")
    return value
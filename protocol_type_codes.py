import struct
TYPE_CODE_SIZE = 1
def pack_type_code(type_code: int):
    """
        Packs a type code into the an appropriate bite format for transmitting it
        type_code: the type code
    """
    return struct.pack(">B", type_code)

def unpack_type_code_from_message(message):
    """
        Takes a message in byte format and returns the type code for it
        message: bytes containing a message created using a message protocol
    """
    relevant_bytes = message[:TYPE_CODE_SIZE]
    type_code = struct.unpack(">B", relevant_bytes)[0]
    return type_code

def compute_message_after_type_code(message):
    """
        Returns the part of a message after its type code.
        message: bytes containing a message created using a message protocol
    """
    return message[TYPE_CODE_SIZE:]
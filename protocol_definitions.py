import protocol

class ProtocolTypeCodeAssigner:
    def __init__(self):
        self.next_code = 0

    def claim_next_code(self):
        result = self.next_code
        self.next_code += 1
        return result
type_code_assigner = ProtocolTypeCodeAssigner()

HELP_MESSAGE_PROTOCOL_TYPE_CODE = type_code_assigner.claim_next_code()
BASE_HELP_MESSAGE_PROTOCOL_TYPE_CODE = type_code_assigner.claim_next_code()
ACCOUNT_CREATION_PROTOCOL_TYPE_CODE = type_code_assigner.claim_next_code()
SIGN_IN_PROTOCOL_TYPE_CODE = type_code_assigner.claim_next_code()
TEXT_MESSAGE_PROTOCOL_TYPE_CODE = type_code_assigner.claim_next_code()
GAME_UPDATE_PROTOCOL_TYPE_CODE = type_code_assigner.claim_next_code()
JOIN_GAME_PROTOCOL_TYPE_CODE = type_code_assigner.claim_next_code()
QUIT_GAME_PROTOCOL_TYPE_CODE = type_code_assigner.claim_next_code()
CHAT_MESSAGE_PROTOCOL_TYPE_CODE = type_code_assigner.claim_next_code()
GAME_CREATION_PROTOCOL_TYPE_CODE = type_code_assigner.claim_next_code()
GAME_PIECE_PROTOCOL_TYPE_CODE = type_code_assigner.claim_next_code()
GAME_ENDING_PROTOCOL_TYPE_CODE = type_code_assigner.claim_next_code()

#For communicating with the client
CLIENT_PROTOCOL_MAP = protocol.ProtocolMap([
    protocol.create_text_message_protocol(BASE_HELP_MESSAGE_PROTOCOL_TYPE_CODE),
    protocol.create_text_message_protocol(HELP_MESSAGE_PROTOCOL_TYPE_CODE),
    protocol.create_text_message_protocol(TEXT_MESSAGE_PROTOCOL_TYPE_CODE),
    protocol.create_nine_character_single_string_message_protocol(GAME_UPDATE_PROTOCOL_TYPE_CODE),
    protocol.create_single_character_string_message_protocol(GAME_PIECE_PROTOCOL_TYPE_CODE),
    protocol.create_username_and_single_character_message_protocol(GAME_ENDING_PROTOCOL_TYPE_CODE)
])

#For communicating with the server
SERVER_PROTOCOL_MAP = protocol.ProtocolMap([
    protocol.MessageProtocol(BASE_HELP_MESSAGE_PROTOCOL_TYPE_CODE),
    protocol.create_text_message_protocol(HELP_MESSAGE_PROTOCOL_TYPE_CODE),
    protocol.create_username_and_password_message_protocol(ACCOUNT_CREATION_PROTOCOL_TYPE_CODE),
    protocol.create_username_and_password_message_protocol(SIGN_IN_PROTOCOL_TYPE_CODE),
    protocol.create_username_message_protocol(JOIN_GAME_PROTOCOL_TYPE_CODE),
    protocol.create_username_message_protocol(GAME_CREATION_PROTOCOL_TYPE_CODE),
    protocol.MessageProtocol(QUIT_GAME_PROTOCOL_TYPE_CODE),
    protocol.create_single_byte_nonnegative_integer_message_protocol(GAME_UPDATE_PROTOCOL_TYPE_CODE),
])
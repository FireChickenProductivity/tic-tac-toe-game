import protocol

HELP_MESSAGE_PROTOCOL_TYPE_CODE = 1
BASE_HELP_MESSAGE_PROTOCOL_TYPE_CODE = 0
ACCOUNT_CREATION_PROTOCOL_TYPE_CODE = 2
SIGN_IN_PROTOCOL_TYPE_CODE = 3
TEXT_MESSAGE_PROTOCOL_TYPE_CODE = 4
GAME_UPDATE_PROTOCOL_TYPE_CODE = 5
JOIN_GAME_PROTOCOL_TYPE_CODE = 6
QUIT_GAME_PROTOCOL_TYPE_CODE = 7
CHAT_MESSAGE_PROTOCOL_TYPE_CODE = 8
GAME_CREATION_PROTOCOL_TYPE_CODE = 9

#For communicating with the client
CLIENT_PROTOCOL_MAP = protocol.ProtocolMap([
    protocol.create_text_message_protocol(BASE_HELP_MESSAGE_PROTOCOL_TYPE_CODE),
    protocol.create_text_message_protocol(HELP_MESSAGE_PROTOCOL_TYPE_CODE),
    protocol.create_text_message_protocol(TEXT_MESSAGE_PROTOCOL_TYPE_CODE),
    protocol.create_nine_character_single_string_message_protocol(GAME_UPDATE_PROTOCOL_TYPE_CODE),
    protocol.create_text_message_protocol(CHAT_MESSAGE_PROTOCOL_TYPE_CODE)
])

#For communicating with the server
SERVER_PROTOCOL_MAP = protocol.ProtocolMap([
    protocol.create_protocol(BASE_HELP_MESSAGE_PROTOCOL_TYPE_CODE),
    protocol.create_text_message_protocol(HELP_MESSAGE_PROTOCOL_TYPE_CODE),
    protocol.create_username_and_password_message_protocol(ACCOUNT_CREATION_PROTOCOL_TYPE_CODE),
    protocol.create_username_and_password_message_protocol(SIGN_IN_PROTOCOL_TYPE_CODE),
    protocol.create_username_message_protocol(JOIN_GAME_PROTOCOL_TYPE_CODE),
    protocol.create_username_message_protocol(GAME_CREATION_PROTOCOL_TYPE_CODE),
    protocol.create_protocol(QUIT_GAME_PROTOCOL_TYPE_CODE),
    protocol.create_single_byte_nonnegative_integer_message_protocol(GAME_UPDATE_PROTOCOL_TYPE_CODE),
])
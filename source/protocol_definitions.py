import protocol

HELP_MESSAGE_PROTOCOL_TYPE_CODE = 1
BASE_HELP_MESSAGE_PROTOCOL_TYPE_CODE = 0
#For communicating with the client
CLIENT_PROTOCOL_MAP = protocol.ProtocolMap([
    protocol.create_text_message_protocol(BASE_HELP_MESSAGE_PROTOCOL_TYPE_CODE),
    protocol.create_text_message_protocol(HELP_MESSAGE_PROTOCOL_TYPE_CODE)
])

#For communicating with the server
SERVER_PROTOCOL_MAP = protocol.ProtocolMap([
    protocol.create_protocol(BASE_HELP_MESSAGE_PROTOCOL_TYPE_CODE),
    protocol.create_text_message_protocol(HELP_MESSAGE_PROTOCOL_TYPE_CODE)
])
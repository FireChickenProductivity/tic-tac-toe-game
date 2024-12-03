#The code in this file manages the relationship between connection handlers and data affiliated with their connections. This is used by the server to communicate with clients. 

from connection_handler import ConnectionHandler, ConnectionInformation
from protocol import Message

class ConnectionTableEntry:
    def __init__(self, connection_handler: ConnectionHandler, state):
        """
            Contains information associated with a connection
            connection_handler: the ConnectionHandler for communicating through the connection
            state: information to associate with the connection
        """
        self.connection_handler = connection_handler
        self.state = state

    def compute_table_representation(self):
        """Computes a unique text representation of the connection"""
        connection_information = self.connection_handler.get_connection_information()
        return connection_information.text_representation

    def send_message_through_connection(self, message: Message):
        """Sends the Message object the the connection"""
        self.connection_handler.send_message(message)

    def get_state(self):
        """Return state information associated with the connection"""
        return self.state

    def __str__(self):
        return f"{self.compute_table_representation()}->{self.get_state()}"

    def __repr__(self):
        return self.__str__()

class ConnectionTable:
    def __init__(self, usernames_to_connections):
        """A table for keeping track of connections"""
        self.usernames_to_connections = usernames_to_connections
        self.connections = {}

    def insert_entry(self, entry: ConnectionTableEntry):
        """Adds the ConnectionTableEntry to the table"""
        representation = entry.compute_table_representation()
        self.connections[representation] = entry

    def remove_entry(self, connection_information: ConnectionInformation):
        """Removes the entry with specified ConnectionInformation from the table if present and otherwise fails silently. This does not work with usernames for convenience."""
        representation = connection_information.text_representation
        if representation in self.connections:
            self.connections.pop(connection_information.text_representation)

    def get_connection_information_from_username(self, username: str):
        return self.usernames_to_connections.get(username, None)

    def get_entry(self, connection_information: ConnectionInformation):
        """Returns the ConnectionTableEntry corresponding to the ConnectionInformation. If a username is used instead of connection information, it is used to get the relevant connection information."""
        if type(connection_information) == str:
            connection_information = self.get_connection_information_from_username(connection_information)
        if connection_information is None:
            return None
        else:
            return self.connections.get(connection_information.text_representation, None)

    def get_entry_state(self, connection_information: ConnectionInformation):
        """Returns the state information associated with the ConnectionInformation"""
        entry = self.get_entry(connection_information)
        state = entry.get_state()
        return state

    def send_message_to_entry(self, message: Message, connection_information: ConnectionInformation):
        """Sends the message through the connection associated with the connection information if present and otherwise fails silently"""
        entry = self.get_entry(connection_information)
        if entry is not None:
            entry.send_message_through_connection(message)

    def __str__(self):
        return str(self.connections)
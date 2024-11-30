# How to Define a Message Protocol
1. Define a unique numeric type code for the protocol in protocol_definitions.py.

2. Check to see if any of the abstract protocol creation functions defined at the bottom of Protocol meet your requirements. These create a protocol with already defined fields given the type code. If none of them meet your needs, go to step 3. Otherwise, go to step 6.

3. Define any needed fields that meet your requirements. See the section on defining fields for details.

4. Create your message protocol object by using the MessageProtocol class with the type code and any needed fields as arguments. 

5. If the protocol requires any fields, create an abstract protocol creation function for the fields to make future development easier.

6. Add the protocol to the relevant protocol map in protocol_definitions.py. 


# How to Define a Message Protocol Field
1. See if a suitable message protocol field creation function exists at the bottom of protocol_fields.py. If one of them meets your needs, call it with the required parameters and go to step 5. Otherwise, go to step 2.

2. Decide if the field is going to be fixed length or variable length. If it is going to be fixed length, go to step 3. Otherwise, go to step 4.

3. Create a ConstantLengthProtocolField using the struct text for packing and unpacking the data (See [Format Characters Documentation](https://docs.python.org/3/library/struct.html#format-characters) for details). Go to step 5.

4. Create a VariableLengthProtocolField. A function that creates struct text for packing the object using the result of calling len on the object as an argument and the size of the length field that comes before your variable length field in bytes. 

5. Create a function for creating fields with the desired properties to make future work easier. The function should take if the field is variable length and the size of the length field in bytes.


# How to Make the Server Support a New Message Protocol
1. If the protocol is not already defined and registered with the necessary protocol maps, see the instructions for defining a message protocol.

2. Define a Server class method for responding to a message conforming to the protocol. This should take a dictionary containing the values and then the connection information as arguments. The values dictionary maps field names to their values. Values at this point have already been unpacked from the bytes. You can send a response back to the client using the connection_table's send_message_to_entry method using the message to send to the client and the connection information as arguments. (The message object is created using the type_code and the values as a list or tuple)

3. Register this method with the callback handler in server.py using protocol_callback_handler.register_callback_with_protocol. The arguments are the type code for the protocol and the message handling function.

# How to Add a New Command to the Client
1. Define a command handling function in commands.py that takes the client object and value, the command arguments as a string, as arguments. Return a string to indicate the presence of an error or a message to have it sent to the server.

2. Add an appropriate command object definition to the create_commands function at the bottom of commands.py. This will include the name of the command, the handling function, and the help message text.

# How to Make the Client Support Responding to a New Message Protocol
1. If the protocol is not already defined and registered with the necessary protocol maps, see the instructions for defining a message protocol.

2. Define a new method of the client.py Client class for responding to a message conforming to the protocol that takes a dictionary containing the values as its only argument (after the required self argument because this is a python method). The values dictionary maps field names to their values. Values at this point have already been unpacked from the bytes.  

3. Register this method with the callback handler in the Client _create_protocol_callback_handler method. The arguments are the type code for the protocol and the message handling method. Do not forget to refer to the registered method with self.method_name.
# Tic-Tac-Toe Game 

This is a simple Tic-Tac-Toe game project that is implemented using Python and sockets. 

## How to Play
You can play the game by doing the following:

1. **Start the server:** Run the `server.py` script: it requires the input -p (port number). The host can optionally be specified with -i (IP address). If unspecified, the server is started at address 0.0.0.0. These command line arguments specify the host and port location that the server will be hosted at. Sample usages: 'python server.py -p 65432' or 'python server.py -p 7745 -i localhost'. Running the server will generate a public encryption key inside the file "public_rsa.pem". Users must place this in the same directory as their client program for to be able to communicate successfully with the server. 
2. **Connect clients:** Run the `client.py` script on any desired number of different machines or terminals. This also requires command line arguments -i (host) -p (port).
3. **Play the game:** Players take turns entering their moves. The first player to get three in a row wins!

Use the register command documented below to create an account if you do not have one. Use the login command to login. You can start a game with the create command. You can join a game that you created or got invited to with the join command. After joining, you make moves with the move command.

Commands:
* **Register an account:** Upon successfully connecting to the server, you must register an account. To do this, type 'register' followed by your chosen username and password into the terminal, seperated by spaces.
* **Login to an account:** After you have created an account, you will need to login. Type 'login' followed by your registered username and password into the terminal, seperated by spaces.
* **Create a game:** To create a new game, type 'create' into the terminal followed by the username of your opponent.
* **Join a game:** To join a game, type 'join' followed by the user name of the other player. A game creator must join their game to make moves in it using the username of the other player. If you try to join a game that does not exist come the server creates it. 
* **Make a move:** To make a move, choose a space on the board and find it's corresponding coordinate. The rows are designated by 'a', 'b', or 'c'. The columns are '1', '2', or '3'. An example coordinate would be 'b3'. Type 'move' followed by the chosen coordinate into the terminal to make your move. You can only make a move on empty spaces.
* **Quit the game:** To quit a game, enter 'quit' into the terminal.
* **Help!:** If you'd like to see these commands during the game, type 'help', and the options will be displayed. Type 'help' followed by the command you would like more information about.
* **Exiting the program:** To exit the program, type 'exit'.

Reconnection:

When the client program detects a problem with the server connection, it tries to reconnect with the server. The amount of time that it waits after each subsequent reconnection attempt increases until it reaches the maximum waiting time of 30 seconds. If the client program receives a message from the server, it resets the waiting time back to the minimum. If the user has already tried to log in, the client tries to log in again using the previous credentials. If the user was previously in a game, the client tries to rejoin the same game.

## Game Message Protocol Specification
The game message protocol defines the structure and format of messages exchanged between the server and clients.
* Message format: A struct-based format is used for message serialization and deserialization.
* Message structure: type_code: a single byte unique identifier for the message type at the start of every message. Field 1, Field 2, ...: Additional data fields specific to the message type. Variable length fields are preceded by a field specifying its length.

Type codes are automatically generated and may consequently change between updates. 

Abstract protocols (used to define concrete message protocols):
* Text message protocol: Contains a type code followed by a 2 byte field giving the length of the last field, which is a string.
* Username and password message protocol: Contains a type code followed by a 1 byte field giving the length of the next field. The next field is a string containing the username. The following field contains one byte giving the length of the following field, which is a string field containing the password. 
* Single byte message protocol: Contains a type code followed by a single byte that gets decoded as an unsigned integer. 
* Small text message protocol: Contains a type code, then a 1 byte field giving the length of the next field, and then a string field.
* Game board message protocol: Contains a type code and then a fixed length 9 byte string representing a tictactoe game board. Each character represents a position on the board. 
* Fixed length string message protocol: Contains a type code and then a fixed length string.
* Single character message protocol: Contains a type code followed by single character in a single byte. 
* Single username and single character message protocol: Contains a type code and then a variable length string with its length determined by a single byte field. The last field is a single byte character.

Message Protocols for Communicating From the Client to the Server:
* Account creation request: A username and password protocol for requesting the creation of an account. The expected response is a text message response describing if the account could be created or already existed. 
* Login request: A username and password protocol for logging in. The expected response is a text message response describing if login was successful. 
* Game update request A single byte message protocol describing a move performed by the user. The number represents the tile to perform the move on. The expected response is either a game update response giving the new board state or a text message response explaining that the move was not permitted. If the move ends the game, a game ending message response is expected. 
* Join game request: a small text message protocol with the string giving the name of the other player in the game to join. Only one game is permitted between 2 players at a time. The expected response is a game piece update message describing the piece controlled by the player followed by a game update response giving the state of the board if successful and a text message response explaining what went wrong if unsuccessful.
* Quit game request: consists only of the type code .
* Game creation protocol: a small text message protocol with the string containing the name of the player to invite to the game. The expected response is a text message explaining if the game creation was successful. 
* Symmetric encryption key message protocol: communicates a symmetric encryption key to the server through asymmetric encryption to be used for further communications between the client and server. Consists of a type code followed by the 32 byte encryption key and a 16 byte initialization vector.

Message Protocols for Communicating From the Server to the Client:
* Text message response: a text message protocol with for giving miscellaneous updates to the client. 
* Game update response: a game board message protocol. This gives the board for the active game and is sent when a player joins a game or after a move is made.
* Chat message response: a text message protocol sending a text message to the desired recipient. 
* Game ending protocol: a single username and single character message protocol. This is sent at the end of a game. The single character at the end describes if the game ended in a win, loss, or tie for the notified player. The username contains the name of the opponent to allow distinguishing between games.
* Game piece protocol: a single character message protocol containing the game piece belonging to the messaged player. This is sent when a player joins a game.

## Requirements to Run The Project
* Python3.11
* Python Cryptography library: the project was tested with cryptography version 43.0.0 and may not work with other versions of the library.

## Logging
Logs are utilized to document errors as well as client and server connect/disconnect events. These are located in the 'logs' directory under 'client.log' and 'server.log'. 

# Additional Resources
* [Link to Python Documentation](https://docs.python.org/3/)
* [Link to Sockets Documentation](https://docs.python.org/3/library/socket.html#example)
* [Link to Socket Tutorial](https://docs.python.org/3/howto/sockets.html)
* [Statement of Work](https://github.com/FireChickenProductivity/tic-tac-toe-game/blob/main/StatementOfWork.md)
* [Python Cryptography Library](https://cryptography.io/en/43.0.0/)

# Security Risk/Evaluation
* Passwords are stored directly in the database, which means that anyone who steals the database obtains the passwords. This should get addressed using password hashes with salt values.
* The system permits fast, repeated log in attempts, which would make compromising passwords a lot easier. This could be addressed by enforcing a time delay in between login requests from the same source IP address and possibly limiting the number of accepted login requests for a user in a given amount of time.
* The protocol does not include message authentication, which could allow not only interference in the middle but also packets with spoofed source address to allow impersonating another user. This could be addressed using encrypted message hashes.
* The encryption scheme does not protect the private key, so anyone who steals it could decrypt the initial symmetric key transmission message. This could be addressed by protecting the private key with a password.
* Someone in the middle could pretend that the correct public key is theirs. This could be addressed by getting a certificate from a certificate authority.
* The encryption scheme relies on a single symmetric key for every client session, which could potentially allow cryptanalysis attacks as it is not random what messages get sent when during a session. This could be addressed by updating the symmetric key using a key derivation function after every message. Uncovering the first key would uncover the rest, but that itself could be addressed by starting over with a new random symmetric key periodically.
* The server has no special protections against denial of service attacks. Properly addressing this is beyond the scope of the server code itself.
* Someone could launch a denial of service attack against the server by trying to fill memory with games as the server never removes them. That could greatly reduce the number of traffic that would have to be used against the server to deny service. To address this, the server could remove inactive games after a certain amount of time.
* A denial of service attack could try to fill disk memory by filling the database with accounts or filling the log with events. To address this, the logging code could stop adding to the file after it reaches a certain size. The server could require email verification of accounts before creating them to avoid filling the database with excess accounts and remove accounts after a certain amount of time if they were never used to play any games.


# Mock Socket Testing Framework
Interactions between the server and clients can be tested with a custom unit testing framework that simulates sockets and selectors. See mock_socket.py and testing_utilities.py for the code. Tests written in this framework can be seen in test_communication.py. 

Sample test:

```python
        expected_message = Message(0, {'text': help_messages[""]})
        testcase = TestCase()
        testcase.create_client("Bob")
        testcase.buffer_client_command("Bob", "help")
        testcase.buffer_client_command("Bob", 1)
        testcase.run()
        output = testcase.get_output("Bob")
        print('output', output)
        testcase.assert_received_values_match_log([expected_message], 'Bob')
        testcase.assert_values_match_output([ContainsMatcher("Help")], 'Bob')
```

The expected message is the message expected from the server to the client. A test case object is created for the test. A client named "Bob" is created inside this test case (Note: clients no longer need to be explicitly created as they will get implicitly created by the buffer_client_commands method). It buffers the commands "help" and 1. This means that this will stimulate Bob running the help command and then wait until the total number of received messages at this simulated client is at least 1 before proceeding. This prevents the client from terminating before it has finished receiving messages. A number is used here to decide how many messages must be received before proceeding. A timeout throws an exception if this takes too long. This is useful for making the simulated client receive responses from prior messages or messages that result from other simulated clients before executing the following instructions.

The test case is ran with the run method. The output obtained is the output to the client's simulated terminal. The first assertion statement asserts that the received messages are as expected. The second assertion asserts that that the simulated client terminal output consists of a single message containing the text "Help" somewhere inside it. 

The object SkipItem() can be used in one of the assertion lists to mean that whatever is in that position can be ignored.

The following test uses should_perform_automatic_login=True to specify that clients should be automatically logged into the server. The corresponding identities are generated automatically if nonexistent. The clients wait for the login responses before performing any actions. The login response is skipped with a SkipItem() in the below test. Note that the total number of messages received for waiting must include the initial login response even with automatic login. 

```python
        testcase = TestCase(should_perform_automatic_login=True)
        testcase.create_client("Bob")
        testcase.create_client("Alice")
        testcase.buffer_client_commands("Bob", ["create Alice", 2, "join Alice", 4, 'quit', 5])
        testcase.buffer_client_commands("Alice", [4, 'join Bob', 6])
        testcase.run()
        expected_alice_messages = [
            SkipItem(),
            create_text_message("Bob invited you to a game!"),
            create_text_message("Bob has joined your game!"),
            create_text_message("Bob has left your game!"),
            PLAYING_O_MESSAGE,
            EMPTY_GAME_BOARD_MESSAGE,
        ]
        testcase.assert_received_values_match_log(expected_alice_messages, "Alice")
```

The testing_utilities.py WaitingCommand objects can be used to wait for other conditions before letting a simulated client continue. 

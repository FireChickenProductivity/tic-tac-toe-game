import time
from threading import Thread
import selectors
from client import Client, create_socket_from_address
from server import Server, create_listening_socket
from logging_utilities import PrimaryMemoryLogger
from mock_socket import MockSelector, MockInternet

class TimeoutException(Exception):
    """An exception indicating that something timed out"""
    pass


def wait_until_true_or_timeout(condition_function, timeout_message = "", time_to_wait = 10, starting_wait_time = 0.0001):
    """
        Repeatedly checks the condition function to see if it is true. If so, the function returns True. 
        If the time_to_wait is exceeded, a TimeoutException is raised.
        The function uses sleep statements to avoid using too much CPU time.
        condition_function: the condition function to check
        timeout_message: a message to display on timeout
        time_to_wait: how many seconds to wait before timing out
        starting_wait_time: the initial amount of time to sleep in between invoking the condition function
    """
    time_waited = 0
    waiting_time = starting_wait_time
    while True:
        if condition_function():
            return True
        elif time_waited >= time_to_wait:
            raise TimeoutException(f"Timed out with time to wait {time_to_wait}! " + timeout_message)
        else:
            time.sleep(waiting_time)
            time_waited += waiting_time
            waiting_time = min(time_to_wait - time_waited, waiting_time*2)

class Credentials:
    def __init__(self, username, password=""):
        self.username = username
        self.password = password

    def __str__(self):
        return self.username + " " + self.password

class TestClientHandler:
    def __init__(self, host, port, selector, socket_creation_function, credentials: Credentials=None):
        """
            Manages a client and associated data used for testing
            host: the server host address
            port: the server port address
            selector: the selector
            socket_creation_function: the socket creation function
        """
        self.logger = PrimaryMemoryLogger()
        self.output = []
        self.selector = selector
        output_text_function=lambda x: self.output.append(x)
        self.client = Client(
            host,
            port,
            selector,
            self.logger,
            output_text_function=output_text_function,
            socket_creation_function=socket_creation_function
        )
        self.credentials = credentials

    def perform_command(self, command: str):
        request = self.client.create_request_from_text_input(command)
        self.client.send_message(request)

    def send_message(self, message):
        self.client.send_message(message)
    
    def login(self):
        self.perform_command("login " + str(self.credentials))

    def register(self):
        self.perform_command("register " + str(self.credentials))

    def close(self):
        self.client.close()

    def run_selector_loop_without_blocking(self):
        client_selector_thread = Thread(target=self.client.run_selector_loop)
        client_selector_thread.start()

    def get_output(self):
        return self.output[:]

    def get_log(self, category=None):
        return self.logger.get_log(category)

    def get_username(self):
        return self.credentials.username

class TestServerHandler:
    def __init__(self, host, port, selector, database_path, listening_socket_creation_function):
        self.logger = PrimaryMemoryLogger()
        self.server = Server(host, port, selector, self.logger, database_path, listening_socket_creation_function)

    def listen_for_socket_events_without_blocking(self):
        server_listening_thread = Thread(target=self.server.listen_for_socket_events)
        server_listening_thread.start()

    def get_log(self, category=None):
        return self.logger.get_log(category)

    def close(self):
        self.server.close()

class TestingFactory:
    def __init__(self, server_host, server_port, *, should_use_real_sockets=False):
        self.server_host = server_host
        self.server_port = server_port
        self.should_use_real_sockets=should_use_real_sockets
        if not self.should_use_real_sockets:
            self.internet = MockInternet()
            self.client_port = 5001
            self.client_ip_address = 90

    def create_real_client(self, credentials: Credentials=None):
        return TestClientHandler(
            self.server_host,
            self.server_port,
            selectors.DefaultSelector(),
            create_socket_from_address,
            credentials
        )

    def create_mock_client(self, credentials: Credentials=None):
        client_address = (str(self.client_ip_address), self.client_port)
        self.client_ip_address += 1
        return TestClientHandler(
            self.server_host,
            self.server_port,
            MockSelector(),
            lambda x: self.internet.create_socket_from_address(client_address, x),
            credentials,
        )

    def create_client(self, credentials: Credentials=None):
        if self.should_use_real_sockets:
            return self.create_real_client(credentials)
        else:
            return self.create_mock_client(credentials)

    def create_real_server(self, database_path):
        return TestServerHandler(
            self.server_host,
            self.server_port,
            selectors.DefaultSelector(),
            database_path,
            create_listening_socket
            )

    def create_mock_server(self, database_path):
        return TestServerHandler(
            self.server_host,
            self.server_port,
            MockSelector(),
            database_path,
            self.internet.create_listening_socket_from_address
        )

    def create_server(self, database_path='testing.db'):
        if self.should_use_real_sockets:
            return self.create_real_server(database_path)
        else:
            return self.create_mock_server(database_path)
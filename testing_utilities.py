import time
import selectors
from client import Client, create_socket_from_address
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

    
    
class TestClientHandlerFactory:
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

    def create_client(self, credentials: Credentials):
        if self.should_use_real_sockets:
            return self.create_real_client(credentials)
        else:
            return self.create_mock_client(credentials)

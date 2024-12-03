#Automated tests for the primary memory logger used during testing

from logging_utilities import PrimaryMemoryLogger

import unittest

SIMPLE_MESSAGES = ["simple", "messages"]
SECONDARY_CATEGORY = "category"
SECONDARY_MESSAGES = [7, None, 'secondary']

def store_messages_in_log(messages, log, category = None):
    for message in messages:
        log.log_message(message, category)

def store_primary_messages_in_log(log):
    store_messages_in_log(SIMPLE_MESSAGES, log)

def store_secondary_messages_in_log(log):
    store_messages_in_log(SECONDARY_MESSAGES, log, SECONDARY_CATEGORY)

class TestPrimaryMemoryLogger(unittest.TestCase):
    def test_starts_with_nothing(self):
        logger = PrimaryMemoryLogger()
        primary_log = logger.get_log()
        expected_primary_log = []
        self.assertEqual(expected_primary_log, primary_log)
        category_log = logger.get_log("category")
        expected_category_log = []
        self.assertEqual(expected_category_log, category_log)

    def _assert_has_primary_messages(self, logger):
        expected = SIMPLE_MESSAGES[:]
        actual = logger.get_log()
        self.assertEqual(expected, actual)

    def _assert_has_secondary_messages(self, logger):
        expected = SECONDARY_MESSAGES[:]
        actual = logger.get_log(SECONDARY_CATEGORY)
        self.assertEqual(expected, actual)

    def test_handles_primary_messages(self):
        logger = PrimaryMemoryLogger()
        store_primary_messages_in_log(logger)
        self._assert_has_primary_messages(logger)

    def test_handles_secondary_messages(self):
        logger = PrimaryMemoryLogger()
        store_secondary_messages_in_log(logger)
        self._assert_has_secondary_messages(logger)

    def test_handles_primary_and_secondary_messages(self):
        logger = PrimaryMemoryLogger()
        store_primary_messages_in_log(logger)
        store_secondary_messages_in_log(logger)
        self._assert_has_primary_messages(logger)
        self._assert_has_secondary_messages(logger)

        
if __name__ == '__main__':
    unittest.main()
import unittest
from cryptography_boundary import *

PUBLIC_TESTING_KEY_NAME = "test_public.pem"
PRIVATE_TESTING_KEY_NAME = "test_private.pem"

class TestEncryption(unittest.TestCase):
    def test_asymmetric_encryption(self):
        public, private = create_public_private_key_pair(PUBLIC_TESTING_KEY_NAME, PRIVATE_TESTING_KEY_NAME)
        initial_data = b"This is a message"
        encrypted = encrypt_data_using_public_key(initial_data, public)
        print(len(encrypted))
        decrypted = decrypt_data_using_private_key(encrypted, private)
        self.assertEqual(initial_data, decrypted)

if __name__ == '__main__':
    unittest.main()
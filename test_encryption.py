import unittest
from cryptography_boundary import *

PUBLIC_TESTING_KEY_NAME = "test_public.pem"
PRIVATE_TESTING_KEY_NAME = "test_private.pem"

class TestEncryption(unittest.TestCase):
    def test_asymmetric_encryption(self):
        public, private = obtain_public_private_key_pair(PUBLIC_TESTING_KEY_NAME, PRIVATE_TESTING_KEY_NAME)
        initial_data = b"This is a message"
        encrypted = encrypt_data_using_public_key(initial_data, public)
        print(len(encrypted))
        decrypted = decrypt_data_using_private_key(encrypted, private)
        self.assertEqual(initial_data, decrypted)

    def test_symmetric_encryption(self):
        parameters = create_symmetric_key_parameters()
        encryption_function, decryption_function = create_symmetric_key_encryptor_and_decryptor_from_number_and_input_vector(*parameters)
        initial_data = b"'A'M3@ 6+$jQvLU"
        encrypted = encryption_function(initial_data)
        print(len(encrypted))
        decrypted = decryption_function(encrypted)
        self.assertEqual(initial_data, decrypted)
        second_encryption = encryption_function(initial_data)
        second_decryption = decryption_function(second_encryption)
        self.assertEqual(second_decryption, decrypted)

if __name__ == '__main__':
    unittest.main()
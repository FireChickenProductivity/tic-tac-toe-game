# This is what the rest of the system uses for dealing with encryption

import os
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import asymmetric
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from file_utilities import read_bytes_at_path, write_bytes_at_path

# Code for dealing with asymmetric encryption

RSA_KEY_SIZE = 4096
RSA_PUBLIC_EXPONENT = 65537
RSA_BLOCK_SIZE = 256

RSA_PUBLIC_KEY_PATH = "public_rsa.pem"
RSA_PRIVATE_KEY_PATH = "private_rsa.pem"

def load_private_key(name):
    key_bytes = read_bytes_at_path(name)
    key = serialization.load_pem_private_key(key_bytes, password=None)
    return key

def load_public_key(name=RSA_PUBLIC_KEY_PATH):
    key_bytes = read_bytes_at_path(name)
    key = serialization.load_pem_public_key(key_bytes)
    return key

def store_public_key_at_path(key, path):
    representation = key.public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo)
    write_bytes_at_path(representation, path)

def store_private_key_at_path(key, path):
    representation = key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.TraditionalOpenSSL, encryption_algorithm=serialization.NoEncryption())
    write_bytes_at_path(representation, path)

def create_public_private_key_pair(public_key_name, private_key_name):
    private_key = rsa.generate_private_key(public_exponent=65537,key_size=2048)
    public_key = private_key.public_key()
    store_public_key_at_path(public_key, public_key_name)
    store_private_key_at_path(private_key, private_key_name)
    return public_key, private_key

def load_public_private_key_pair(public_key_name, private_key_name):
    public_key = load_public_key(public_key_name)
    private_key = load_private_key(private_key_name)
    return public_key, private_key

def obtain_public_private_key_pair(public_key_name=RSA_PUBLIC_KEY_PATH, private_key_name=RSA_PRIVATE_KEY_PATH):
    if os.path.exists(public_key_name) and os.path.exists(private_key_name):
        return load_public_private_key_pair(public_key_name, private_key_name)
    return create_public_private_key_pair(public_key_name, private_key_name)

def _create_padding_algorithm():
    return asymmetric.padding.OAEP(
            mgf=asymmetric.padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )

def encrypt_data_using_public_key(data, key):
    return key.encrypt(data, _create_padding_algorithm())

def decrypt_data_using_private_key(data, key):
    return key.decrypt(data, _create_padding_algorithm())

# Code for dealing with symmetric key encryption

SYMMETRIC_BLOCK_SIZE = 16
SYMMETRIC_BLOCK_SIZE_IN_BITS = SYMMETRIC_BLOCK_SIZE*8

def perform_symmetric_cryptographic_operation(data, operator):
    return operator.update(data) + operator.finalize()

def perform_double_symmetric_cryptographic_operation(data, first_operator, second_operator):
    data = perform_symmetric_cryptographic_operation(data, first_operator)
    data = perform_symmetric_cryptographic_operation(data, second_operator)
    return data

class PaddingEncryptor:
    def __init__(self, cipher):
        self.cipher = cipher
    
    def __call__(self, data):
        encryptor = self.cipher.encryptor()
        padder = padding.PKCS7(SYMMETRIC_BLOCK_SIZE_IN_BITS).padder()
        return perform_double_symmetric_cryptographic_operation(data, padder, encryptor)

class PaddingDecryptor:
    def __init__(self, cipher):
        self.cipher = cipher

    def __call__(self, data):
        decryptor = self.cipher.decryptor()
        unpadder = padding.PKCS7(SYMMETRIC_BLOCK_SIZE_IN_BITS).unpadder()
        return perform_double_symmetric_cryptographic_operation(data, decryptor, unpadder)

def create_symmetric_key_encryptor_and_decryptor_from_number_and_input_vector(number, input_vector):
    cipher = Cipher(algorithms.AES(number), modes.CBC(input_vector))
    encryptor = PaddingEncryptor(cipher)
    decryptor = PaddingDecryptor(cipher)
    return encryptor, decryptor

def create_symmetric_key_parameters():
    number = os.urandom(32)
    input_vector = os.urandom(16)
    return number, input_vector




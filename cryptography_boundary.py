# This is what the rest of the system uses for dealing with encryption

import os
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes



RSA_KEY_SIZE = 4096
RSA_PUBLIC_EXPONENT = 65537

# Convenience functions

def _read_bytes_at_path(path):
    with open(path, "rb") as file:
        return file.read()

def _write_bytes_at_path(data, path):
    with open(path, "wb") as file:
        file.write(data)

# Functions for dealing with a symmetric encryption

def load_private_key(name):
    key_bytes = _read_bytes_at_path(name)
    key = serialization.load_pem_private_key(key_bytes, password=None)
    return key

def load_public_key(name):
    key_bytes = _read_bytes_at_path(name)
    key = serialization.load_pem_public_key(key_bytes)
    return key

def store_public_key_at_path(key, path):
    representation = key.public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo)
    _write_bytes_at_path(representation, path)

def store_private_key_at_path(key, path):
    representation = key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.TraditionalOpenSSL, encryption_algorithm=serialization.NoEncryption())
    _write_bytes_at_path(representation, path)

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

def obtain_public_private_key_pair(public_key_name, private_key_name):
    if os.path.exists(public_key_name) and os.path.exists(private_key_name):
        return load_public_private_key_pair(public_key_name, private_key_name)
    return create_public_private_key_pair(public_key_name, private_key_name)

def _create_padding_algorithm():
    return padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )

def encrypt_data_using_public_key(data, key):
    return key.encrypt(data, _create_padding_algorithm())

def decrypt_data_using_private_key(data, key):
    return key.decrypt(data, _create_padding_algorithm())

# Functions for dealing with symmetric key encryption

BLOCK_SIZE = 16

def create_symmetric_key_encryptor_and_decryptor_from_number_and_input_vector(number, input_vector):
    cipher = Cipher(algorithms.AES(number), modes.CBC(input_vector))
    encryptor = cipher.encryptor()
    decryptor = cipher.decryptor()
    return encryptor, decryptor

def create_symmetric_key_parameters():
    number = os.urandom(32)
    input_vector = os.urandom(16)
    return number, input_vector

def perform_symmetric_cryptographic_operation(data, operator):
    return operator.update(data) + operator.finalize()


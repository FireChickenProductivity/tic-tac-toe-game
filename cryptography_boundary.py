from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

RSA_KEY_SIZE = 4096
RSA_PUBLIC_EXPONENT = 65537

def _read_bytes_at_path(path):
    with open(path, "rb") as file:
        return file.read()

def load_private_key(name):
    key_bytes = _read_bytes_at_path(name)
    key = serialization.load_pem_private_key(key_bytes, password=None)
    return key

def load_public_key(name):
    key_bytes = _read_bytes_at_path(name)
    key = serialization.load_pem_public_key(key_bytes)
    return key

def _write_bytes_at_path(data, path):
    with open(path, "wb") as file:
        file.write(data)

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

BLOCK_SIZE = 64

def create_symmetric_key():
    pass

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

def encrypt_data_using_symmetric_key(data, key):
    pass

def decrypt_data_using_symmetric_key(data, key):
    pass
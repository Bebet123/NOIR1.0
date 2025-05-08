from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

data = b'messaggio segretessimo scemo chi legge'

key = b"passwordpassword"
print(key)

cipher = AES.new(key, AES.MODE_EAX)

ciphertext, tag = cipher.encrypt_and_digest(data)

nonce = cipher.nonce
print(ciphertext,tag)

cipher = AES.new(key, AES.MODE_EAX, nonce)

data = cipher.decrypt_and_verify(ciphertext, tag)

print(str(data))

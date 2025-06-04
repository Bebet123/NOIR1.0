from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
import base64



with open("keys.txt", "r", encoding="utf-8") as file:
    contenuto = file.read()

dbkey = contenuto

# Funzione per criptare
def cripta_aes_chiave_testo(chiave: bytes, testo: str) -> str:
    iv = get_random_bytes(16)  # Initialization vector (16 byte)
    cipher = AES.new(chiave, AES.MODE_CBC, iv)
    dati_criptati = cipher.encrypt(pad(testo.encode(), AES.block_size))
    return base64.b64encode(iv + dati_criptati).decode()

# Funzione per decriptare
def decripta_aes_chiave_testo(chiave: bytes, testo_criptato: str) -> str:
    dati = base64.b64decode(testo_criptato)
    iv = dati[:16]
    dati_criptati = dati[16:]
    cipher = AES.new(chiave, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(dati_criptati), AES.block_size).decode()

# Esempio d'uso
if __name__ == "__main__":
    chiave = bytes(dbkey.encode('UTF-8'))
    messaggio = "Test segreto AES"

    criptato = cripta_aes_chiave_testo(chiave, messaggio)
    print("Criptato:", criptato)

    decriptato = decripta_aes_chiave_testo(chiave, criptato)
    print("Decriptato:", decriptato)

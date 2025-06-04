from Crypto.Cipher import AES


data = b'messaggio segretessimo scemo chi legge'

dbkey = "chiavatasegretaa"

def temp(_str):
    if(len(_str) > 16):
        return _str[0:16]
    elif(len(_str) < 16):
        a = 16 // len(_str)
        newStr = _str * a
        newStr += _str[0:16-len(_str)*a]
        return newStr
    else:
        return _str 


keystr = (temp("key"))


key = bytes(dbkey.encode('UTF-8'))
print(key)

cipher = AES.new(key, AES.MODE_EAX)

ciphertext, tag = cipher.encrypt_and_digest(data)

nonce = cipher.nonce
print(ciphertext,tag)

cipher = AES.new(key, AES.MODE_EAX, nonce)

data = cipher.decrypt_and_verify(ciphertext, tag)

print(str(data.decode('UTF-8')))

def cripta(testo):
    
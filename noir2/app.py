from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO, emit, join_room
import json
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Struttura per memorizzare utenti e le loro chiavi pubbliche
users = {}
# Struttura per memorizzare i messaggi
messages = {}

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Chat Crittografata RSA</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jsencrypt/3.3.2/jsencrypt.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .container {
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            width: 90%;
            max-width: 800px;
            height: 90vh;
            display: flex;
            flex-direction: column;
        }
        .header {
            background: #667eea;
            color: white;
            padding: 20px;
            border-radius: 10px 10px 0 0;
            text-align: center;
        }
        .login-screen, .chat-screen {
            display: none;
            flex-direction: column;
            height: 100%;
        }
        .login-screen.active, .chat-screen.active {
            display: flex;
        }
        .login-form {
            padding: 40px;
            display: flex;
            flex-direction: column;
            gap: 20px;
            justify-content: center;
            flex: 1;
        }
        input {
            padding: 15px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
        }
        button {
            padding: 15px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            transition: background 0.3s;
        }
        button:hover {
            background: #5568d3;
        }
        .chat-header {
            padding: 15px 20px;
            background: #f8f9fa;
            border-bottom: 1px solid #ddd;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: #f8f9fa;
        }
        .message {
            margin-bottom: 15px;
            padding: 10px 15px;
            border-radius: 10px;
            max-width: 70%;
            word-wrap: break-word;
        }
        .message.sent {
            background: #667eea;
            color: white;
            margin-left: auto;
        }
        .message.received {
            background: white;
            border: 1px solid #ddd;
        }
        .message .sender {
            font-weight: bold;
            margin-bottom: 5px;
            font-size: 14px;
        }
        .message .time {
            font-size: 12px;
            opacity: 0.7;
            margin-top: 5px;
        }
        .input-area {
            padding: 20px;
            background: white;
            border-top: 1px solid #ddd;
            display: flex;
            gap: 10px;
        }
        .input-area input {
            flex: 1;
        }
        .status {
            font-size: 12px;
            color: #666;
        }
        .error {
            color: red;
            text-align: center;
            padding: 10px;
        }
        .info {
            color: #666;
            font-size: 14px;
            text-align: center;
            padding: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 Chat Crittografata RSA</h1>
        </div>

        <div class="login-screen active">
            <div class="login-form">
                <h2 style="text-align: center; margin-bottom: 20px;">Accedi alla Chat</h2>
                <input type="text" id="username" placeholder="Il tuo username">
                <input type="text" id="recipientUsername" placeholder="Username destinatario">
                <button onclick="login()">Entra</button>
                <div id="loginError" class="error"></div>
                <div class="info">
                    La tua chiave privata verrà salvata nel browser.<br>
                    I messaggi sono crittografati end-to-end con RSA.
                </div>
            </div>
        </div>

        <div class="chat-screen">
            <div class="chat-header">
                <div>
                    <strong id="currentUser"></strong>
                    <span class="status"> → Chat con <span id="recipientUser"></span></span>
                </div>
                <button onclick="logout()" style="padding: 8px 15px;">Esci</button>
            </div>
            <div class="messages" id="messages"></div>
            <div class="input-area">
                <input type="text" id="messageInput" placeholder="Scrivi un messaggio..." 
                       onkeypress="if(event.key==='Enter') sendMessage()">
                <button onclick="sendMessage()">Invia</button>
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        let currentUsername = '';
        let recipientUsername = '';
        let privateKey = '';
        let publicKey = '';
        let recipientPublicKey = '';

        // Genera coppia di chiavi RSA
        function generateKeyPair() {
            const crypt = new JSEncrypt({default_key_size: 2048});
            crypt.getKey();
            return {
                publicKey: crypt.getPublicKey(),
                privateKey: crypt.getPrivateKey()
            };
        }

        // Carica o genera chiavi
        function loadOrGenerateKeys() {
            let keys = localStorage.getItem('rsa_keys');
            if (!keys) {
                keys = generateKeyPair();
                localStorage.setItem('rsa_keys', JSON.stringify(keys));
            } else {
                keys = JSON.parse(keys);
            }
            return keys;
        }

        function login() {
            const username = document.getElementById('username').value.trim();
            const recipient = document.getElementById('recipientUsername').value.trim();
            
            if (!username || !recipient) {
                document.getElementById('loginError').textContent = 
                    'Inserisci entrambi gli username';
                return;
            }

            if (username === recipient) {
                document.getElementById('loginError').textContent = 
                    'Non puoi chattare con te stesso';
                return;
            }

            currentUsername = username;
            recipientUsername = recipient;

            // Carica o genera chiavi
            const keys = loadOrGenerateKeys();
            privateKey = keys.privateKey;
            publicKey = keys.publicKey;

            // Registra utente con la sua chiave pubblica
            socket.emit('register', {
                username: currentUsername,
                publicKey: publicKey,
                recipient: recipientUsername
            });
        }

        socket.on('registered', (data) => {
            if (data.success) {
                recipientPublicKey = data.recipientPublicKey;
                
                document.querySelector('.login-screen').classList.remove('active');
                document.querySelector('.chat-screen').classList.add('active');
                document.getElementById('currentUser').textContent = currentUsername;
                document.getElementById('recipientUser').textContent = recipientUsername;
                
                // Carica messaggi precedenti
                loadMessages();
            } else {
                document.getElementById('loginError').textContent = data.message;
            }
        });

        function loadMessages() {
            const messagesDiv = document.getElementById('messages');
            messagesDiv.innerHTML = '';
        }

        function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            
            if (!message) return;

            // Critta il messaggio con la chiave pubblica del destinatario
            const encrypt = new JSEncrypt();
            encrypt.setPublicKey(recipientPublicKey);
            const encryptedMessage = encrypt.encrypt(message);

            if (!encryptedMessage) {
                alert('Errore nella crittografia del messaggio');
                return;
            }

            socket.emit('send_message', {
                from: currentUsername,
                to: recipientUsername,
                encrypted: encryptedMessage,
                timestamp: new Date().toISOString()
            });

            // Mostra il messaggio inviato
            displayMessage(currentUsername, message, new Date().toISOString(), true);
            input.value = '';
        }

        socket.on('new_message', (data) => {
            // Decritta il messaggio con la chiave privata
            const decrypt = new JSEncrypt();
            decrypt.setPrivateKey(privateKey);
            const decryptedMessage = decrypt.decrypt(data.encrypted);

            if (decryptedMessage) {
                displayMessage(data.from, decryptedMessage, data.timestamp, false);
            } else {
                console.error('Impossibile decrittare il messaggio');
            }
        });

        function displayMessage(sender, text, timestamp, isSent) {
            const messagesDiv = document.getElementById('messages');
            const messageEl = document.createElement('div');
            messageEl.className = `message ${isSent ? 'sent' : 'received'}`;
            
            const time = new Date(timestamp).toLocaleTimeString('it-IT', {
                hour: '2-digit',
                minute: '2-digit'
            });

            messageEl.innerHTML = `
                ${!isSent ? `<div class="sender">${sender}</div>` : ''}
                <div>${text}</div>
                <div class="time">${time}</div>
            `;

            messagesDiv.appendChild(messageEl);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        function logout() {
            socket.emit('logout', {username: currentUsername});
            currentUsername = '';
            recipientUsername = '';
            document.querySelector('.chat-screen').classList.remove('active');
            document.querySelector('.login-screen').classList.add('active');
            document.getElementById('username').value = '';
            document.getElementById('recipientUsername').value = '';
            document.getElementById('messages').innerHTML = '';
        }

        socket.on('user_offline', (data) => {
            console.log('Utente offline:', data.username);
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('register')
def handle_register(data):
    username = data['username']
    public_key = data['publicKey']
    recipient = data['recipient']
    
    # Salva utente e chiave pubblica
    users[username] = {
        'public_key': public_key,
        'sid': request.sid
    }
    
    # Unisciti alla stanza per la comunicazione diretta
    room = get_room_name(username, recipient)
    join_room(room)
    
    # Controlla se il destinatario è online
    if recipient in users:
        recipient_public_key = users[recipient]['public_key']
        emit('registered', {
            'success': True,
            'recipientPublicKey': recipient_public_key
        })
    else:
        emit('registered', {
            'success': False,
            'message': f'Utente {recipient} non trovato. Attendi che si connetta.'
        })

@socketio.on('send_message')
def handle_message(data):
    sender = data['from']
    recipient = data['to']
    encrypted_msg = data['encrypted']
    timestamp = data['timestamp']
    
    # Salva messaggio
    room = get_room_name(sender, recipient)
    if room not in messages:
        messages[room] = []
    
    messages[room].append(data)
    
    # Invia al destinatario se online
    if recipient in users:
        emit('new_message', data, room=users[recipient]['sid'])

@socketio.on('logout')
def handle_logout(data):
    username = data['username']
    if username in users:
        del users[username]
    emit('user_offline', {'username': username}, broadcast=True)

def get_room_name(user1, user2):
    """Crea un nome stanza univoco per due utenti"""
    return '-'.join(sorted([user1, user2]))

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
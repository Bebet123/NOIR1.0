import os
import json
import base64
from flask import Flask, render_template, request, session, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()
socketio = SocketIO(app, cors_allowed_origins="*")

# Almacén de usuarios (en producción debería estar en una base de datos)
users = {}
# Almacén de claves públicas
public_keys = {}
# Mensajes por sala (en producción debería estar en una base de datos)
room_messages = {}

@app.route('/')
def index():
    """Ruta para la página principal."""
    return render_template('index.html')

@app.route('/generate_keys', methods=['POST'])
def generate_keys():
    """Genera un par de claves RSA y devuelve la clave pública."""
    # Generar par de claves RSA
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    
    # Obtener la clave pública
    public_key = private_key.public_key()
    
    # Serializar las claves para enviarlas al cliente
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    return jsonify({
        'privateKey': private_pem,
        'publicKey': public_pem
    })

@app.route('/chat')
def chat():
    """Ruta para la página de chat."""
    username = request.args.get('username', '')
    room = request.args.get('room', '')
    
    if not username or not room:
        return "Se requiere nombre de usuario y sala", 400
    
    return render_template('chat.html', username=username, room=room)

@socketio.on('connect')
def handle_connect():
    """Maneja la conexión de un usuario."""
    print('Cliente conectado', request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    """Maneja la desconexión de un usuario."""
    for room in list(users.keys()):
        if request.sid in users[room]:
            username = users[room][request.sid]
            leave_room(room)
            emit('user_leave', {'username': username}, room=room)
            del users[room][request.sid]
            if not users[room]:  # Si la sala está vacía
                del users[room]
                if room in room_messages:
                    del room_messages[room]
                if room in public_keys:
                    del public_keys[room]

@socketio.on('join')
def handle_join(data):
    """Maneja la unión de un usuario a una sala."""
    username = data['username']
    room = data['room']
    public_key = data['publicKey']
    
    # Unirse a la sala
    join_room(room)
    
    # Inicializar usuarios y mensajes de la sala si no existen
    if room not in users:
        users[room] = {}
    if room not in room_messages:
        room_messages[room] = []
    if room not in public_keys:
        public_keys[room] = {}
    
    # Almacenar usuario y clave pública
    users[room][request.sid] = username
    public_keys[room][username] = public_key
    
    # Notificar a todos en la sala sobre el nuevo usuario
    emit('user_join', {
        'username': username,
        'users': list(users[room].values()),
        'publicKeys': public_keys[room]
    }, room=room)
    
    # Enviar historial de mensajes al usuario que se une
    emit('message_history', room_messages[room])

@socketio.on('leave')
def handle_leave(data):
    """Maneja cuando un usuario abandona una sala."""
    username = data['username']
    room = data['room']
    
    leave_room(room)
    
    if room in users and request.sid in users[room]:
        del users[room][request.sid]
        
        if room in public_keys and username in public_keys[room]:
            del public_keys[room][username]
        
        emit('user_leave', {'username': username}, room=room)
        
        if not users[room]:  # Si la sala está vacía
            del users[room]
            if room in room_messages:
                del room_messages[room]
            if room in public_keys:
                del public_keys[room]

@socketio.on('send_message')
def handle_message(data):
    """Maneja el envío de mensajes encriptados."""
    room = data['room']
    sender = data['sender']
    encrypted_messages = data['encryptedMessages']
    
    # Guardar el mensaje en el historial
    message_id = str(uuid.uuid4())
    timestamp = data.get('timestamp', 0)
    
    message_data = {
        'id': message_id,
        'sender': sender,
        'encryptedMessages': encrypted_messages,
        'timestamp': timestamp
    }
    
    if room in room_messages:
        room_messages[room].append(message_data)
    
    # Enviar mensaje a todos en la sala
    emit('receive_message', message_data, room=room)

@socketio.on('request_users')
def handle_users_request(data):
    """Envía la lista de usuarios y sus claves públicas en la sala."""
    room = data['room']
    
    if room in users and room in public_keys:
        emit('users_list', {
            'users': list(users[room].values()),
            'publicKeys': public_keys[room]
        })

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
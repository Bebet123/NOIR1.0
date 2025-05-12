from flask import Flask, render_template, request, redirect, session, url_for
from flask_socketio import SocketIO, emit, join_room
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import eventlet


from flask import jsonify
app = Flask(__name__)
app.secret_key = 'supersegreto'
socketio = SocketIO(app, cors_allowed_origins='*')

# In-memory map: username -> socket sid
online_users = {}








def get_db():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
        encrypted_private_key TEXT,
        iv TEXT,     
        salt TEXT
        
    )""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT NOT NULL,
        receiver TEXT NOT NULL,
        message TEXT NOT NULL,
        encrypted INTEGER DEFAULT 0,
        delivered BOOLEAN DEFAULT 0,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT NOT NULL,
        contact TEXT NOT NULL,
        UNIQUE(user, contact)
    )""")

   
    db.commit()
    db.close()



@app.route('/')
def index():
    if 'username' in session:  # Se l'utente è loggato
        return redirect(url_for('chat'))  # Reindirizza alla pagina chat
    return render_template('index.html')  # Altrimenti, mostra la pagina di landing (index)


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        db = get_db()
        try:
            db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            db.commit()
            session['username'] = username
            return redirect(url_for('chat'))
        except sqlite3.IntegrityError:
            error = "Username già esistente."
    return render_template('register.html', error=error)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            return redirect(url_for('chat'))
        error = "Credenziali errate."
    return render_template('login.html', error=error)



@app.route('/history/<contact>')
def history(contact):
    if 'username' not in session:
        return {}, 403
    user = session['username']
    db = get_db()
    msgs = db.execute("""
        SELECT sender, message, timestamp FROM messages
        WHERE (sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?)
        ORDER BY timestamp ASC
    """, (user, contact, contact, user)).fetchall()
    return [{'sender': m['sender'], 'message': m['message'], 'timestamp': m['timestamp']} for m in msgs]


@app.route('/chat')
def chat():
    if 'username' not in session:
        return redirect(url_for('index'))
    db = get_db()
    username = session['username']

    # Ottieni contatti + conteggio nuovi messaggi
    contacts = db.execute("""
        SELECT c.contact, COUNT(m.id) AS unread 
        FROM contacts c
        LEFT JOIN messages m 
            ON c.contact = m.sender 
            AND m.receiver = ? 
            AND m.delivered = 0
        WHERE c.user = ?
        GROUP BY c.contact
    """, (username, username)).fetchall()

    error = request.args.get("error")
    return render_template('chat.html', username=username, contacts=contacts, error=error)






@app.route('/add_contact', methods=['POST'])
def add_contact():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    contact = request.form['contact']
    current_user = session['username']
    
    if contact == current_user:
        return redirect(url_for('chat', error="Non puoi aggiungere te stesso."))

    db = get_db()
    user_exists = db.execute("SELECT * FROM users WHERE username = ?", (contact,)).fetchone()

    if not user_exists:
        return redirect(url_for('chat', error="Utente non trovato."))

    try:
        db.execute("INSERT INTO contacts (user, contact) VALUES (?, ?)", (current_user, contact))
        db.commit()
    except sqlite3.IntegrityError:
        pass  # Già presente

    return redirect(url_for('chat'))


  

@socketio.on('connect')
def handle_connect():
    username = session.get('username')
    
    if username:
        online_users[username] = request.sid
        join_room(username)
    
        # Invia messaggi non letti
        db = get_db()
        messages = db.execute("SELECT * FROM messages WHERE receiver = ? AND delivered = 0", (username,)).fetchall()
        for msg in messages:
            emit('private_message', {
                'sender': msg['sender'],
                'message': msg['message']
            }, room=username)
            db.execute("UPDATE messages SET delivered = 1 WHERE id = ?", (msg['id'],))
        db.commit()

@socketio.on('send_private')
def handle_private(data):
    sender = session.get('username')
    receiver = data['receiver']
    message = data['message']
    if not sender or not receiver:
        return

    db = get_db()

    # Aggiungi il contatto per il mittente
    try:
        db.execute("INSERT INTO contacts (user, contact) VALUES (?, ?)", (sender, receiver))
    except sqlite3.IntegrityError:
        pass

    # Aggiungi il mittente ai contatti del destinatario
    try:
        db.execute("INSERT INTO contacts (user, contact) VALUES (?, ?)", (receiver, sender))
    except sqlite3.IntegrityError:
        pass
    

    # Notifica il ricevente che ha un nuovo contatto
    emit('new_contact', {'contact': sender}, room=receiver)


    # Salva il messaggio
    db.execute("INSERT INTO messages (sender, receiver, message) VALUES (?, ?, ?)", (sender, receiver, message))
    db.commit()

    # Invia se online
    if receiver in online_users:
        emit('private_message', {'sender': sender, 'message': message}, room=receiver)


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/utente')
def utente():
    if 'username' not in session:
        return redirect(url_for('login'))

    db = get_db()
    contacts = db.execute('SELECT contact FROM contacts WHERE user = ?', (session['username'],)).fetchall()
    return render_template('utente.html', contacts=contacts)

@app.route('/delete_contact', methods=['POST'])
def delete_contact():
    if 'username' not in session:
        return redirect(url_for('login'))

    contact = request.form.get('contact')
    if contact:
        db = get_db()
        db.execute('DELETE FROM contacts WHERE user = ? AND contact = ?', (session['username'], contact))
        db.commit()

    return redirect(url_for('chat'))

if __name__ == '__main__':
    init_db()
    socketio.run(app, host='0.0.0.0', port=5000)

const socket = io();
const username = USERNAME_FROM_TEMPLATE;
let currentContact = null;
const messages = {};  // { contact: [{sender, text}] }

let notificationSound;  // Dichiarazione globale della variabile per il suono

document.addEventListener('DOMContentLoaded', () => {
    // Inizializza l'audio della notifica al primo click
    document.body.addEventListener('click', () => {
        if (!notificationSound) {
            notificationSound = new Audio('/static/notification.mp3');
        }
    }, { once: true });

    const form = document.getElementById('message-form');
    const input = document.getElementById('message-input');

    form.addEventListener('submit', e => {
        e.preventDefault();
        const msg = input.value.trim();
        if (msg && currentContact) {
            socket.emit('send_private', {
                receiver: currentContact,
                message: msg
            });
            storeMessage(currentContact, username, msg);
            appendMessage(username, msg);
            input.value = '';
        }
    });
});


// Seleziona un contatto dalla lista
function selectContact(contact) {
    currentContact = contact;
    updateNotification(contact, false);
    
        document.getElementById("no-chat").style.display = "none";
        document.getElementById("messages").style.display = "block";
        document.getElementById("message-form").style.display = "flex";
    
       
    
    document.getElementById('messages').innerHTML = '';

    if (messages[contact]) {
        messages[contact].forEach(msg => appendMessage(msg.sender, msg.text));
    }

    loadHistory(contact);
}

// Ricezione messaggio privato
socket.on('private_message', data => {
    const { sender, message } = data;
    storeMessage(sender, sender, message);

    if (currentContact === sender) {
        appendMessage(sender, message);
        playNotification();
    } else {
        updateNotification(sender, true);
        playNotification();  // Riproduce la notifica
    }
});

// Carica la cronologia dei messaggi da Flask
function loadHistory(contact) {
    fetch(`/history/${contact}`)
        .then(res => res.json())
        .then(data => {
            messages[contact] = [];
            document.getElementById('messages').innerHTML = '';
            data.forEach(msg => {
                storeMessage(contact, msg.sender, msg.message);
                appendMessage(msg.sender, msg.message);
            });
        });
}

// Aggiunge un messaggio all'interfaccia
function appendMessage(sender, text) {
    const msgBox = document.getElementById('messages');
    const msg = document.createElement('div');
    msg.className = 'message';
    msg.innerHTML = `<strong>${sender}:</strong> ${text}`;
    msgBox.appendChild(msg);
    msgBox.scrollTop = msgBox.scrollHeight;
}

// Salva il messaggio in memoria
function storeMessage(contact, sender, text) {
    if (!messages[contact]) messages[contact] = [];
    messages[contact].push({ sender, text });
}

// Evidenzia un contatto se ci sono messaggi non letti
function updateNotification(contact, show) {
    const contacts = document.querySelectorAll('#contacts .contact');
    contacts.forEach(li => {
        if (li.textContent.trim() === contact) {
            li.style.fontWeight = show ? 'bold' : 'normal';
        }
    });
}

// Riproduce il suono di notifica
function playNotification() {
    if (notificationSound) {
        notificationSound.play().catch(err => console.warn("Audio non riprodotto:", err));
    }
}


function selectChat(chatId) {
    // logica per caricare i messaggi
    document.getElementById("chat-box").classList.remove("hidden");
    document.getElementById("no-chat-message").style.display = "none";
}

// All'avvio (nessuna chat selezionata)
document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("chat-box").classList.add("hidden");
    document.getElementById("no-chat-message").style.display = "block";
});


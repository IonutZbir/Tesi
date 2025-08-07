import socket
import random
import json
from message import MessageType, ErrorType

users = {}  # memorizza username -> public_key
sessions_data = {}  # memorizza connessione -> dati temporanei per autenticazione

GROUPS = {
    "modp-1536": {
        "p": int(
            "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
            "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
            "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
            "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
            "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D"
            "C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F"
            "83655D23DCA3AD961C62F356208552BB9ED529077096966D"
            "670C354E4ABC9804F1746C08CA237327FFFFFFFFFFFFFFFF",
            16,
        ),
        "g": 2,
    },
    "mymod": {
        "p": 23,
        "g": 2,
    }
}

def send_json(conn, message):
    try:
        conn.sendall(json.dumps(message).encode())
    except BrokenPipeError:
        print("[SERVER] Errore: connessione chiusa dal client durante l'invio")

def receive_json(conn):
    try:
        data = conn.recv(4096)
        if not data:
            return None
        return json.loads(data.decode())
    except (ConnectionResetError, json.JSONDecodeError):
        return None

def handle_registration(conn, msg):
    username = msg.get("username")
    pk = msg.get("public_key")
    if username in users:
        err_msg = {"type": MessageType.ERROR.value, "error": ErrorType.USERNAMEALEARYEXISTS.value}
        send_json(conn, err_msg)
        print(f"[SERVER] Registrazione fallita: username '{username}' già esistente")
    else:
        users[username] = {"pk": pk}
        success_msg = {"type": MessageType.REGISTERED.value}
        send_json(conn, success_msg)
        print(f"[SERVER] Utente registrato: {username}")

def handle_auth_request(conn, msg, q):
    username = msg.get("username")
    user = users.get(username)
    if not user:
        err_msg = {"type": MessageType.ERROR.value, "error": ErrorType.USERNAMENOTFOUND.value}
        send_json(conn, err_msg)
        print(f"[SERVER] Autenticazione fallita: username '{username}' non trovato")
        return

    challenge = random.randint(0, q - 1)
    sessions_data[conn] = {
        "u_t": msg.get("temp"),
        "pk": user["pk"],
        "challenge": challenge,
    }
    challenge_msg = {"type": MessageType.CHALLENGE.value, "challenge": challenge}
    send_json(conn, challenge_msg)
    print(f"[SERVER] Sfida inviata a {username}: {challenge}")

def handle_auth_response(conn, msg, p, g):
    session = sessions_data.get(conn)
    if not session:
        print("[SERVER] Risposta di autenticazione senza sessione attiva")
        return

    alpha_z = msg.get("response")
    u_t = session["u_t"]
    pk = session["pk"]
    challenge = session["challenge"]

    left = pow(g, alpha_z, p)
    right = (u_t * pow(pk, challenge, p)) % p

    if left == right:
        accepted_msg = {"type": MessageType.ACCEPTED.value}
        send_json(conn, accepted_msg)
        print("[SERVER] Autenticazione accettata")
    else:
        rejected_msg = {"type": MessageType.REJECTED.value}
        send_json(conn, rejected_msg)
        print("[SERVER] Autenticazione rifiutata")

def handle_associate_request(conn, msg, p, g):
    print(f"[SERVER] Ricevuta richiesta di connessione da parte di: {conn} - {msg}")
    msg = {"messaggio": "ricevuto"}
    send_json(conn, msg)

def main():
    HOST = "192.168.1.168"
    PORT = 65432

    group = "modp-1536"
        
    p = GROUPS[group]["p"]
    g = GROUPS[group]["g"]
    q = (p - 1) // 2

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()


        while True:
            print(f"[SERVER] In ascolto su {HOST}:{PORT}")
            conn, addr = s.accept()
            print(f"[SERVER] Connessione da {addr}")

            # Fase handshake: invio gruppo crittografico
            handshake_msg = {"type": MessageType.GROUP_SELECTION.value, "group_id": group}
            send_json(conn, handshake_msg)
            res = receive_json(conn)
            if res is None:
                    print("[SERVER] Connessione chiusa dal client o messaggio non valido")
                    break
            if res["status"] == "received":
                print("[SERVER] Handshake riuscito")
            # Qui puoi gestire la ricezione iniziale di conferma handshake se serve

            while True:
                msg = receive_json(conn)
                if msg is None:
                    print("[SERVER] Connessione chiusa dal client o messaggio non valido")
                    break

                msg_type = msg.get("type")
                if msg_type == MessageType.REGISTER.value:
                    handle_registration(conn, msg)
                elif msg_type == MessageType.AUTH_REQUEST.value:
                    handle_auth_request(conn, msg, q)
                elif msg_type == MessageType.AUTH_RESPONSE.value:
                    handle_auth_response(conn, msg, p, g)
                    conn.close()
                    sessions_data.pop(conn, None)
                    break
                    # continua a navigare.... oppure chiudi la connessione
                elif msg_type == MessageType.ASSOCIATE_REQUEST.value:
                    handle_associate_request(conn, msg, p, g)
                else:
                    print(f"[SERVER] Tipo messaggio sconosciuto: {msg_type}")

            conn.close()
            sessions_data.pop(conn, None)

if __name__ == "__main__":
    main()

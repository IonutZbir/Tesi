import socket
import json
import random
import sys
from message import MessageType, ErrorType

HOST = '127.0.0.1'
PORT = 65432

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

def load_private_key(username):
    try:
        with open(f"{username}_privkey.txt", "r") as f:
            return int(f.read())
    except FileNotFoundError:
        print("[CLIENT] Errore: chiave privata non trovata. Registrati prima di autenticarti.")
        sys.exit(1)

def save_private_key(username, alpha):
    with open(f"{username}_privkey.txt", "w") as f:
        f.write(str(alpha))

def receive_json(sock):
    data = sock.recv(4096)
    if not data:
        print("[CLIENT] Connessione chiusa dal server")
        sys.exit(1)
    return json.loads(data.decode())

def send_json(sock, message):
    sock.sendall(json.dumps(message).encode())

def registration(sock, p, g, q):
    username = input("Inserisci uno username per la registrazione: ").strip()
    alpha = random.randint(1, q - 1)

    public_key = pow(g, alpha, p)
    msg = {"type": MessageType.REGISTER.value, "username": username, "public_key": public_key}
    send_json(sock, msg)

    response = receive_json(sock)
    if response.get("type") == MessageType.ERROR.value:
        val = response.get('error')
        print(f"[CLIENT] Errore dal server: {ErrorType.message(val)}")
    elif response.get("type") == MessageType.REGISTERED.value:
        print("[CLIENT] Registrazione completata con successo.")
        print(f"[CLIENT] Chiave segreta generata e salvata localmente.")
        save_private_key(username, alpha)
    else:
        print("[CLIENT] Risposta inattesa dal server:", response)

def authentication(sock, p, g, q):
    username = input("Inserisci uno username per l'autenticazione: ").strip()
    alpha = load_private_key(username)

    alpha_t = random.randint(1, q - 1)
    u_t = pow(g, alpha_t, p)
    auth_request = {"type": MessageType.AUTH_REQUEST.value, "temp": u_t, "username": username}
    send_json(sock, auth_request)

    response = receive_json(sock)
    if response.get("type") == MessageType.ERROR.value:
        print(f"[CLIENT] Errore dal server: {response.get('error')}")
        return

    if response.get("type") != MessageType.CHALLENGE.value:
        print("[CLIENT] Risposta inattesa dal server durante autenticazione.")
        return

    c = response["challenge"]
    print(f"[CLIENT] Ricevuto challenge: {hex(c)[:20]}")

    alpha_z = (alpha_t + alpha * c) % q
    auth_response = {"type": MessageType.AUTH_RESPONSE.value, "response": alpha_z}
    send_json(sock, auth_response)

    final_response = receive_json(sock)
    if final_response.get("type") == MessageType.ACCEPTED.value:
        print("[CLIENT] Autenticazione riuscita!")
    elif final_response.get("type") == MessageType.REJECTED.value:
        print("[CLIENT] Autenticazione fallita.")
    else:
        print("[CLIENT] Risposta inattesa dal server dopo autenticazione.")

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))

        # Fase handshake
        handshake_msg = receive_json(sock)
        print(f"[CLIENT] Fase di handshake - scelta del gruppo: {handshake_msg}")

        # Rispondiamo al server per confermare ricezione
        send_json(sock, {"status": "received"})

        group = handshake_msg.get("group_id")
        if group not in GROUPS:
            print("[CLIENT] Gruppo crittografico non supportato dal client.")
            sys.exit(1)

        p = GROUPS[group]["p"]
        g = GROUPS[group]["g"]
        q = (p - 1) // 2

        print(f"[CLIENT] Parametri gruppo:\n p = {hex(p)[:20]}... (troncato)\n g = {g}\n q = {hex(q)[:20]}... (troncato)")
        # print(f"[CLIENT] Parametri gruppo:\n p = {p}\n g = {g}\n q = {q}")

        # Scelta dell'azione da parte dell'utente
        while True:
            ans = input("Premi R per registrarti o A per autenticarti (Q per uscire): ").strip().upper()
            if ans == "R":
                registration(sock, p, g, q)
            elif ans == "A":
                authentication(sock, p, g, q)
            elif ans == "Q":
                print("[CLIENT] Uscita dal client.")
                break
            else:
                print("Input non valido, riprova.")

if __name__ == "__main__":
    main()

import socket
import json
import random
import sys
from utils.message import MessageType, ErrorType
from utils.groups import GROUPS
from pathlib import Path
from utils.utils import get_linux_device_model

import platform

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

HOST = '127.0.0.1'
PORT = 65432

CONFIG_PATH = Path.home() / ".config"

def load_private_key(username):
    schnorr_dir = CONFIG_PATH / "schnorr"
    schnorr_dir.mkdir(parents=True, exist_ok=True)
    
    privkey_path = schnorr_dir / f"{username}_privkey.txt"
    
    # if privkey_path.exists():
        
    try:
        with open(privkey_path, "r") as f:
            print(f"[CLIENT] INFO: lettura chiave privata da {privkey_path}.")
            return int(f.read())
    except FileNotFoundError:
        print("[CLIENT] Errore: chiave privata non trovata. Registrati prima di autenticarti.")
        sys.exit(1)

def save_private_key(username, alpha):
    schnorr_dir = CONFIG_PATH / "schnorr"
    schnorr_dir.mkdir(parents=True, exist_ok=True)
    privkey_path = schnorr_dir / f"{username}_privkey.txt"
    with open(privkey_path, "w") as f:
        f.write(str(alpha))
        print(f"[CLIENT] INFO: chiave privata memorizzata in {privkey_path}.")

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

    manuf, _ = get_linux_device_model()

    device_name =  manuf + " " + platform.system() + " " + platform.machine()

    public_key = hex(pow(g, alpha, p))
    msg = {"type": MessageType.REGISTER.value, "username": username, "public_key": public_key, "device": device_name}
    send_json(sock, msg)

    response = receive_json(sock)
    if response.get("type") == MessageType.ERROR.value:
        val = response.get('error')
        print(f"[CLIENT] Errore dal server: {ErrorType.message(val)}")
    elif response.get("type") == MessageType.REGISTERED.value:
        print(f"[CLIENT] INFO: Registrazione dal dispositivo: {device_name}")
        print("[CLIENT] Registrazione completata con successo.")
        print(f"[CLIENT] Chiave segreta generata e salvata localmente.")
        save_private_key(username, alpha)
    else:
        print("[CLIENT] Risposta inattesa dal server:", response)

def authentication(sock, p, g, q):
    username = input("Inserisci uno username per l'autenticazione: ").strip()
    alpha = load_private_key(username)

    alpha_t = random.randint(1, q - 1)
    u_t = hex(pow(g, alpha_t, p))
    auth_request = {"type": MessageType.AUTH_REQUEST.value, "temp": u_t, "username": username}
    send_json(sock, auth_request)

    response = receive_json(sock)
    if response.get("type") == MessageType.ERROR.value:
        val = response.get('error')
        print(f"[CLIENT] Errore dal server: {ErrorType.message(val)}")
        return

    if response.get("type") != MessageType.CHALLENGE.value:
        print("[CLIENT] Risposta inattesa dal server durante autenticazione.")
        return

    c = response["challenge"]
    print(f"[CLIENT] Ricevuto challenge: {c[:20]}")

    c = int(c, 16)

    alpha_z = (alpha_t + alpha * c) % q
    auth_response = {"type": MessageType.AUTH_RESPONSE.value, "response": hex(alpha_z)}
    send_json(sock, auth_response)

    final_response = receive_json(sock)
    if final_response.get("type") == MessageType.ACCEPTED.value:
        print("[CLIENT] Autenticazione riuscita!")
    elif final_response.get("type") == MessageType.REJECTED.value:
        print("[CLIENT] Autenticazione fallita.")
    else:
        print("[CLIENT] Risposta inattesa dal server dopo autenticazione.")

def association(sock, p, g, q):
    manuf, _ = get_linux_device_model()

    device_name =  manuf + " " + platform.system() + " " + platform.machine() # + random.randint(0, 10000)
    
    alpha = random.randint(1, q - 1)

    public_key = hex(pow(g, alpha, p))
    
    assoc_req = {"type": MessageType.ASSOC_REQUEST.value, "device": device_name, "pk": public_key}
    send_json(sock, assoc_req)
    
    print("[CLIENT] Inviata richiesta di associazione del dispositivo")
    
    res = receive_json(sock) # il server invia al client un token temporaneo, usato dal client principale per associare il nuovo dispositivo
    
    if res.get("type") == MessageType.TOKEN_ASSOC.value:
        token = res.get("token") # TODO: il token verrà cifrato con SHA256 e poi inviato
        print(f"[CLIENT] Token ricevuto dal server: {token}")
    elif res.get("type") == MessageType.ERROR.value:
        val = res.get('error')
        print(f"[CLIENT] Errore dal server {ErrorType.message(val)}")
        return
    
    # save_private_key(username, alpha)

def confirm_association(sock, p, g, q):
    ans = input("[CLIENT] Inserisci codice di abbinamento\n")
    

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))

        # Fase handshake
        handshake_msg = receive_json(sock)
        print(f"[CLIENT] Fase di handshake...")

        # Rispondiamo al server per confermare ricezione
        send_json(sock, {"status": "received"})

        group = handshake_msg.get("group_id")
        if group not in GROUPS:
            print("[CLIENT] Gruppo crittografico non supportato dal client.")
            sys.exit(1)

        print(f"[CLIENT] Handshake andato a buon fine...")

        p = GROUPS[group]["p"]
        g = GROUPS[group]["g"]
        q = (p - 1) // 2

        # print(f"[CLIENT] Parametri gruppo:\n p = {hex(p)[:20]}... (troncato)\n g = {g}\n q = {hex(q)[:20]}... (troncato)")
        # print(f"[CLIENT] Parametri gruppo:\n p = {p}\n g = {g}\n q = {q}")

        # Scelta dell'azione da parte dell'utente
        while True:
            menu_message = (
                "\n[CLIENT] Seleziona un'opzione:\n"
                "  [R] Registrati\n"
                "  [A] Autenticati\n"
                "  [B] Richiedi abbinamento dispositivo\n"
                "  [C] Conferma abbinamento dispositivo\n"
                "  [Q] Esci\n"
            )
            print(menu_message)
            ans = input("[CLIENT] Inserisci la tua scelta: ").strip().upper()
            if ans == "R":
                registration(sock, p, g, q)
            elif ans == "A":
                authentication(sock, p, g, q)
                
                # ans = input("Vuoi scegliere il nome utente? Ricorda che sarà visibile pubblicamente: S/N\n")
                # if ans == "S":
                #     pass
                # elif ans == "N":
                #     pass
            elif ans == "B":
                association(sock, p, g, q)
            elif ans == "B":
                confirm_association(sock, p, g, q)
            elif ans == "Q":
                print("[CLIENT] Uscita dal client.")
                break
            else:
                print("[CLIENT] Input non valido, riprova.")

if __name__ == "__main__":
    main()

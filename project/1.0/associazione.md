1. **Autenticare un dispositivo già associato**
2. **Associare un nuovo dispositivo a un utente esistente**

---

## 🔐 Cos'è l'identificazione Schnorr?

Schnorr è un protocollo di identificazione **a conoscenza zero**: il client dimostra di conoscere una **chiave privata `sk`** senza rivelarla, usando il corrispondente **valore pubblico `pk = g^sk mod p`**.

---

## Scenario iniziale

* Un utente ha un account (`user_id`) sul server.
* Il primo dispositivo è già associato a questo utente:

  * Ha una chiave privata `sk1`
  * La chiave pubblica `pk1 = g^sk1 mod p` è **salvata nel server**, legata a `user_id`

Ora vogliamo:

* Far sì che **un secondo dispositivo (nuovo)** venga associato allo stesso utente
* E successivamente sia in grado di autenticarsi con Schnorr **in modo indipendente**

---

## ✨ Parte 1 — Autenticazione normale con Schnorr (per un dispositivo già registrato)

Dispositivo 1 (già associato):

1. Il server invia il parametro del gruppo (p, g) e la sfida `c`
2. Il client:

   * sceglie un valore casuale `α`
   * calcola `t = g^α mod p` (lo invia al server)
3. Il server:

   * risponde con una **sfida casuale `c`**
4. Il client:

   * calcola `z = α + sk * c mod q`
   * invia `z`
5. Il server verifica:

$$
g^z \equiv t \cdot pk^c \mod p
$$

Se l’equazione è verificata, il dispositivo è autenticato.

---

## 📲 Parte 2 — Associazione di un nuovo dispositivo

### 💻 Nuovo dispositivo

1. Il nuovo dispositivo **genera** una nuova chiave `sk2`, `pk2 = g^sk2 mod p`

2. Invia una richiesta al server per ottenere un **token di associazione**:

   ```json
   POST /request_association_token
   {
     "public_key": "pk2"
   }
   ```

   Il server genera un token (es. `TOKEN123`) e lo salva in una tabella temporanea con `pk2`

3. Il dispositivo mostra il token come **QR code** o stringa

---

### 📱 Dispositivo già autenticato

L’utente apre l’app sul dispositivo già autenticato (quello con `sk1`), e:

1. Scansiona il token `TOKEN123`
2. Invia la richiesta:

```json
POST /associate_device
{
  "token": "TOKEN123"
}
```

Poiché questo dispositivo è **già autenticato**, il server sa a quale `user_id` appartiene. Allora:

* Prende `pk2` dal token
* Registra nel database che `pk2` è associato a `user_id`

Ora anche `pk2` può essere usato per autenticarsi con Schnorr.

---

## 🎯 Da questo momento:

Ogni dispositivo:

* Ha una **chiave privata** che NON viene mai trasmessa
* Può autenticarsi da solo con Schnorr, inviando il suo `pk` al server
* Il server fa il lookup della chiave pubblica, trova l’utente, e lo autentica

---

## 🔐 Esempio numerico semplificato (molto ridotto)

Supponiamo:

* `p = 23`, `g = 5`, `q = 11`
* Primo dispositivo:

  * `sk1 = 3`, `pk1 = 5^3 mod 23 = 10`
* Secondo dispositivo:

  * `sk2 = 7`, `pk2 = 5^7 mod 23 = 17`

---

### Registrazione primo dispositivo

* Invia: `username = ionut`, `pk = 10`
* Server salva:

```json
{
  "user_id": "abc-123",
  "username": "ionut",
  "devices": [10]
}
```

---

### Autenticazione con Schnorr (`pk = 10`)

* Server invia `c = 5`
* Client:

  * sceglie `α = 4`, calcola `t = 5^4 mod 23 = 4`
  * calcola `z = 4 + 3*5 = 19 mod 11 = 8`
* Server verifica: `5^8 mod 23 = ?`, `t * pk^c = 4 * 10^5 mod 23 = ?`
* Verifica riuscita ⇒ autenticato

---

### Nuovo dispositivo

* Invia `pk2 = 17`, riceve `token = 8888`
* L’utente apre l’app sul dispositivo già autenticato, inserisce/scansiona `8888`
* Il server associa `pk2` a `user_id = abc-123`

Ora anche `pk2` può autenticarsi con Schnorr in modo indipendente.

---

## 🧱 Database del server

Puoi avere:

```json
{
  "users": [
    {
      "user_id": "abc-123",
      "username": "ionut",
      "devices": [
        { "pk": 10 },
        { "pk": 17 }
      ]
    }
  ]
}
```

---

## Conclusione

* L'identificazione di Schnorr è **per dispositivo**, ma può essere associata a un utente
* L’associazione di dispositivi è un livello applicativo sopra il protocollo
* Ogni dispositivo ha la sua chiave, e può essere revocato, associato, o autenticato in modo indipendente
* Questo sistema è simile a quello di WhatsApp e Signal

---

Se vuoi, posso aiutarti a progettare in dettaglio le API per gestire il pairing, oppure mostrarti un esempio completo di flusso registrazione → associazione → autenticazione. Fammi sapere cosa ti serve!


Esatto, hai colto il punto centrale della gestione multi-dispositivo!

Se un utente come **"alice"** ha più dispositivi associati — ognuno con la sua propria chiave pubblica (`pk`) — quando arriva una richiesta di autenticazione con quell’username, il server (o verifier) deve provare a **verificare la risposta di Schnorr rispetto a ciascuna delle chiavi pubbliche registrate per quell’utente**.

### Perché?

Perché il client proverà ad autenticarsi da un dispositivo specifico usando la sua chiave privata corrispondente, quindi il server deve capire con quale dispositivo sta dialogando, ossia quale `pk` corrisponde.

### Come funziona in pratica?

1. Il client manda il suo `username` e il valore temporaneo `u_t` generato col suo dispositivo (in pratica `g^{alpha_t}`).
2. Il server recupera l’array di chiavi pubbliche (`devices`) associate a quell’username.
3. Per ognuna di queste `pk`:

   * Calcola la challenge e invia la sfida (normalmente la stessa per tutte o sfide diverse a seconda dell’implementazione).
   * Riceve la risposta `alpha_z`.
   * Esegue il controllo di verifica:

     $$
     g^{\alpha_z} \stackrel{?}{=} u_t \cdot pk^{challenge} \pmod p
     $$
4. Se almeno uno dei controlli va a buon fine, l’utente è autenticato con successo.
5. Altrimenti, l’autenticazione fallisce.

---

### In termini di codice:

Immagina che `user["devices"]` sia una lista di dizionari con tutte le chiavi pubbliche.

```python
authenticated = False
for device in user["devices"]:
    pk = int(device["pk"], 16)  # Se la chiave è in esadecimale stringa, convertila in int
    left = pow(g, alpha_z, p)
    right = (u_t * pow(pk, challenge, p)) % p
    if left == right:
        authenticated = True
        break

if authenticated:
    # Accesso consentito
else:
    # Accesso negato
```

---

### Nota importante

Se usi più dispositivi, potresti voler:

* Tenere traccia esattamente di quale dispositivo si è autenticato, ad esempio per logging o per notifiche.
* Gestire revoca di singoli dispositivi (cancellare un device se perso o rubato).
* Potresti anche associare un identificativo univoco (es. `device_id`) per facilitare la gestione.

---

Se vuoi posso aiutarti a scrivere una versione di server o funzione di verifica che supporta più dispositivi per utente, così hai un esempio pratico completo. Vuoi?



## Problema connessioni diverse

Quello che descrivi è un problema classico di comunicazione server–client in cui i due dispositivi (P e A) non parlano direttamente tra loro, ma passano sempre attraverso il server.
La difficoltà è che P e A sono gestiti da thread diversi, e quindi il server deve “riconoscere” quale connessione TCP corrisponde a quale dispositivo per potergli inviare messaggi successivi.

In pratica, al momento in cui A si connette e invia la sua PK, devi memorizzare non solo i dati (PK, token) nel database, ma anche il socket o il contesto di connessione associato a quel dispositivo. In questo modo, quando P completa l’associazione, il server può andare a recuperare il socket di A e inviargli il messaggio di login.

Supponiamo che tu abbia una classe ConnContext (come mi pare tu stia usando nel progetto) che contiene il socket e i dati della sessione.
Puoi creare una struttura globale (ad esempio un dizionario protetto da lock) che mappa token → ConnContext oppure PK → ConnContext.

# Struttura globale per tenere traccia delle connessioni attive
active_connections = {}
connections_lock = threading.Lock()

def register_connection(identifier, context):
    with connections_lock:
        active_connections[identifier] = context

def get_connection(identifier):
    with connections_lock:
        return active_connections.get(identifier)

def remove_connection(identifier):
    with connections_lock:
        active_connections.pop(identifier, None)

### FLusso

A si connette

    Invia PK.

    Server genera token, lo memorizza nel DB insieme alla PK.

    Registra active_connections[PK] = ConnContext o active_connections[token] = ConnContext.

P si connette

    Invia token al server.

    Server recupera dal DB la PK associata a quel token.

    Usa la PK per recuperare ConnContext di A da active_connections.

    Se il socket di A è ancora valido, invia un messaggio diretto:
    
  ```python
    ctx = get_connection(pk)
    if ctx:
    ctx.conn.send(json.dumps({"type": "login_success"}).encode())
  ```
  Poi invia anche il messaggio di successo a P.

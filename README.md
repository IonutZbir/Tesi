# Progetto di Tesi - Protocollo d'identificazione di Schnorr

## schnorr_cs_auth_project

In questa cartella sono presenti server e client che comunicano mediante protocollo di schnorr.

- Installare i requisiti/moduli necessari con `pip3 install -r requiments.txt`.
- Installare `MongoDB` se si vuole eseguire il server in locale.

- Per eseguire il server `(schnorr_cs_auth_project/server/server.py)`, specificare nel file `schnorr_cs_auth_project/server/config.json` l'indirizzo IP e la porta di ascolto. Poi nel terminale eseguire `python3 server.py`.
- Per eseguire il client `(schnorr_cs_auth_project/client/client.py)`, eseguire nel terminale `python3 client.py -i IP -p PORTA`, oppure `python3 client.py -h` per maggiori informazioni.

!!! info
    Server online 7/24: `51.210.242.104:65432`

## mobile_auth_app

Installare l'apk fornito.

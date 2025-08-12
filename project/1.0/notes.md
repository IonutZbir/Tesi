# NOTE

- [X] aggiungere in mongo, per l utente i seguenti attributi: data di creazione, dire quale dispositivo è quello principale e quale dispositivo è collegato attualemente.
- [X] sessione lato client
- [X] una volta fatto l 'accoppiamento nel database, sul disopositivo accoppoiato, salvare la pk nel file.
- [X] Poter fare l'abbinamento solo con il dispositivo principale, e inoltre deve essere loggato.
- nell app mobile, implementare schnorr
- refactoring server - rendere tutto modulare
- documentare il protocollo
- annulla abbinamento in corso

Centralizzazione delle risposte di errore
Invece di ripetere ctx.send_error(...) in vari punti, potresti avere una funzione handle_error(ctx, error_type, debug_message=None) che fa logging e invio del messaggio in un colpo solo.
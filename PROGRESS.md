# Stato

## Backlog

**P0, collaudo**

- [x] `tools/smoke.py` come da Bootstrap.
- [ ] Test delle rotte con `app.test_client()`: codici di stato, e verifica che l'HTML del
      fascicolo non contenga nessuno dei valori di risposta delle nove schede.
- [ ] Test dell'API `/api/verifica` e `/api/parola` con payload malformati: campo mancante,
      numero di scheda inesistente, array risposte piu' corto del numero di campi, JSON non
      valido, tipi sbagliati. Nessuno deve produrre un 500.
- [ ] Test di `storage.py`: creazione del database, conteggio tentativi, percentuali di errore
      corrette, comportamento con database vuoto.
- [ ] Test di escaping: inserisci un valore con caratteri HTML in un campo e verifica che la
      pagina non lo interpreti.
- [ ] Verifica che due richieste concorrenti a `/api/verifica` non producano errori di lock
      SQLite. Se succede, correggi la gestione della connessione.

**P1, usabilita'**

- [ ] Invio con tasto Invio su ogni campo, e focus che resta dove serve dopo la verifica.
- [ ] Controllo del layout a 360 pixel di larghezza: nessun overflow orizzontale, campi e
      bottoni raggiungibili con il pollice.
- [ ] Messaggio di errore quando la verifica fallisce per rete assente, distinto da risposta
      sbagliata.
- [ ] Stampa: il fascicolo su carta deve restare leggibile e senza elementi interattivi.
- [ ] Contatore di schede risolte in cima al fascicolo.

**P2, nuovi generatori, uno per iterazione**

Ogni generatore va aggiunto con: modulo in `crypto_puzzles/`, tre difficolta', tre aiuti,
`steps` da esame, `meta_value` e `meta_label`, registrazione in `GENERATORS`, property test
dedicati.

- [ ] Diffie-Hellman: verifica di radice primitiva, logaritmo discreto in Z11 o Z13, chiave
      condivisa.
- [ ] Cifrario affine: chiave da due corrispondenze note, validita' del parametro a, cifratura
      composta.
- [ ] Rete di Feistel a due round con funzione di round elementare, su otto bit.
- [ ] Cifrario di Hill due per due: validita' della matrice e cifratura di una parola breve.
- [ ] El Gamal in Z11: chiave pubblica, cifratura e decifratura con k piccolo.

**P3, solo dopo che P0 e P1 sono chiusi**

- [ ] Pagina di ripasso che estrae gli esercizi delle famiglie con piu' errori nel registro.
- [ ] Esportazione del fascicolo in un file stampabile.
- [ ] Cronometro per scheda, con confronto rispetto al tempo dichiarato.

## Proposte scartate per vincolo di dipendenze

Nessuna finora.

## Diario

### Iterazione 1, 2026-08-13
Task: Bootstrap (`PROGRESS.md` mancante).
Fatto:
- `git init` nella cartella (non era un repository) e primo commit di tutto lo stato attuale.
- `.gitignore` per `instance/`, `__pycache__/`, `.DS_Store`, virtualenv, `*.db` e il file di
  stato locale del loop, cosi' il divieto sui file spuri e' rispettato in automatico.
- Creato `PROGRESS.md` col backlog iniziale copiato voce per voce.
- Creato `tools/smoke.py`: usa `app.test_client()`, nessun server e nessun comando di shell.
  Controlla 302 sulla home, 200 sulla home dopo redirect, 200 su fascicolo corrente, soluzioni,
  archivio e statistiche, 404 su `1970-W01` e sulle sue soluzioni. Esce con codice 1 se
  qualcosa fallisce.
Rilevato per le prossime iterazioni (non toccato, il Bootstrap vieta altro lavoro):
- `storage.py` apre e chiude una connessione SQLite nuova a ogni chiamata, senza `timeout`.
  E' il sospetto numero uno per la voce P0 sul lock in concorrenza.
- `/api/verifica` fa `payload.get("answers") or []` e passa il valore grezzo a `check_puzzle`.
  Se arriva un tipo non iterabile o un dict, il 500 e' plausibile: da coprire con la voce P0
  sui payload malformati.
- `/api/verifica` accetta `number` via `int(...)` protetto, ma `build_issue(payload.get("issue", ""))`
  riceve qualunque tipo: verificare che un `issue` non stringa non esploda.
Gate: `python -m unittest discover -s tests -v` 14 test OK, `python tools/smoke.py` 8 check OK.
Commit: be12838 "Initial state", poi il commit "Bootstrap: PROGRESS.md backlog and tools/smoke.py".

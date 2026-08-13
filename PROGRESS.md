# Stato

## Backlog

**P0, collaudo**

- [x] `tools/smoke.py` come da Bootstrap.
- [x] Test delle rotte con `app.test_client()`: codici di stato, e verifica che l'HTML del
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

### Iterazione 2, 2026-08-13
Task: test delle rotte, e l'HTML del fascicolo non deve contenere le risposte.
Fatto: `tests/test_routes.py`, 14 test. Codici di stato di tutte le rotte piu' 404 su fascicolo
inesistente e su rotta inesistente; content type del service worker; sette test di non-fuga
su 52 fascicoli.
Trovato, e corretto: **i placeholder rivelavano la risposta**.
- `coincidence.py` usava esempi fissi `es. 2/21` e `es. 3/49`. Sono valori di IC realmente
  raggiungibili, quindi per certi semi il campo mostrava in grigio esattamente la risposta.
  Ora `frazione, es. n/d`, senza cifre: non puo' piu' collidere.
- `secret_sharing.py` usava `numero fra 0 e {p-1}`, e `p-1` **e'** il segreto quando il segreto
  e' massimo. Ora `resto in Z{p}`: p e' il modulo, e in Z_p le risposte stanno fra 0 e p-1,
  quindi la collisione e' impossibile per costruzione, non per caso.
Verificato che il test non passa a vuoto: reintrodotto il placeholder difettoso, il test
fallisce su 2026-W27; ripristinato, torna verde. E confrontate risposte e parola su 52
fascicoli prima e dopo la modifica: identiche, l'invariante 2 regge (ho toccato solo un
suggerimento di formato, mai un valore).

Tentativi falliti, da non ripetere:
1. Primo test scritto come "nessuna risposta compare nell'HTML". **Non funziona**: le risposte
   sono numeri di una cifra, e `3` compare 31 volte per motivi legittimi (moduli, enunciati,
   id del fascicolo). Non riscrivere questo test in forma globale.
2. Scansione di tutti gli attributi: falso positivo su `data-number="3"`, che e' il numero
   della scheda #3, non la risposta della #9. Sostituito da una **whitelist**: sul fascicolo
   possono esistere solo `data-issue`, `data-number`, `data-index`, e i loro valori devono
   essere ordinali. Garanzia piu' forte, perche' non dipende dai valori.
3. Test "la parola della settimana non compare nella pagina": falso positivo su `segreto`,
   che e' l'etichetta del campo di Shamir. `META_WORDS` e' lessico crittografico
   (`modulo`, `chiave`, `segreto`, `inverso`...), parole che ricorrono per forza negli
   enunciati: la collisione e' sistemica. La parola e' protetta dalla chiave di Cesare, non
   dalla propria assenza. Il test ora copre solo commenti, script e attributi dati/value.
   Non reintrodurre il controllo sul testo visibile: e' irrisolvibile senza cambiare
   `META_WORDS`, e cambiarla riscriverebbe tutti gli arretrati.
4. Nota: il mio primo placeholder sostitutivo era `resto modulo {p}`, che ha fatto fallire il
   test della parola su 2026-W30, dove la parola e' MODULO. Da qui la scelta della notazione Z,
   che oltretutto e' gia' quella usata in `given`.
Confermato non-fuga: `steps` (la soluzione ragionata) non compare mai nel fascicolo, solo nella
pagina soluzioni. Gli aiuti contengono numeri che a volte coincidono con la risposta, ma e'
voluto: l'invariante 3 chiede che il terzo aiuto sia quasi-soluzione.
Gate: unittest 28 test OK, smoke OK. Albero pulito.

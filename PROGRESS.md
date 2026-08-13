# Stato

## Backlog

**P0, collaudo**

- [x] `tools/smoke.py` come da Bootstrap.
- [x] Test delle rotte con `app.test_client()`: codici di stato, e verifica che l'HTML del
      fascicolo non contenga nessuno dei valori di risposta delle nove schede.
- [x] Test dell'API `/api/verifica` e `/api/parola` con payload malformati: campo mancante,
      numero di scheda inesistente, array risposte piu' corto del numero di campi, JSON non
      valido, tipi sbagliati. Nessuno deve produrre un 500.
- [x] Test di `storage.py`: creazione del database, conteggio tentativi, percentuali di errore
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

### Iterazione 3, 2026-08-13
Task: API con payload malformati, nessun 500.
Fatto: `tests/test_api.py`, 17 test (con subTest, circa 60 payload distinti).
Trovato: **tre cause distinte di 500**, non una. Sondato prima con uno script, poi fissato nei test.
1. Body che non e' un oggetto JSON (`[1,2]`, `"ciao"`, `42`, `true`): `payload.get` su una lista
   dava `AttributeError`. Colpiva **entrambe** le rotte. Nota: `get_json(silent=True) or {}`
   sembra difensivo ma non lo e', perche' una lista non vuota e' truthy e passa il filtro.
2. `issue` di tipo non stringa (`123`, `[]`, `{}`): `build_issue` andava in `TypeError` sul
   match della regex, e con `{}` in `unhashable type` perche' e' memoizzata. Entrambe le rotte.
3. `answers` non lista (`5`, `{"0":"1"}`, `true`): `check_puzzle` fa `len(answers)` e
   `answers[i]`, quindi `TypeError` con un intero e `KeyError` con un dict. Solo `/api/verifica`.
   Anche qui `payload.get("answers") or []` non bastava: un dict non vuoto passa.
Corretto in `app.py` con due helper, `_payload()` e `_issue_from()`, piu' un controllo di tipo
su `answers`. Fix al confine dell'API: `crypto_puzzles/core.py` resta pulito, non l'ho reso
difensivo perche' il contratto di `check_puzzle` e' "ricevi una lista" e il chiamante ora lo
rispetta.
Verificato: ri-eseguita la sonda, 50 richieste malformate, 0 risposte 5xx. `/api/verifica`
risponde solo 200/400/404, `/api/parola` solo 200/404. Aggiunti test di happy path che
verificano tutte e nove le schede con le risposte giuste, cosi' l'hardening non puo' aver
rotto il flusso normale.
I test spostano `storage.DB_PATH` su una cartella temporanea in `setUpModule`: senza questo
ogni run sporcava le statistiche reali del giocatore con centinaia di tentativi falsi.
Scelte deliberate, per non cambiarle a caso in futuro:
- JSON malformato risponde 404 "fascicolo inesistente", non 400. E' la conseguenza del body
  vuoto, ed e' coerente con `issue` mancante. Un 400 sarebbe piu' preciso: candidato per
  quando si tocchera' la gestione errori lato client (voce P1 sul messaggio di rete).
- `issue` di tipo sbagliato risponde 404 e non 400, per coerenza con `issue` inesistente.
- `answers` di tipo sbagliato risponde 200 con tutti i campi a false, come `answers` mancante.
Gate: unittest 45 test OK, smoke OK. Albero pulito.

### Iterazione 4, 2026-08-13
Task: test di `storage.py`.
Fatto: `tests/test_storage.py`, 24 test su creazione del db, log dei tentativi, schede risolte,
statistiche, e database vuoto. Ogni test ha il suo database temporaneo via `addCleanup`.
Trovato, e corretto, due difetti reali:
1. **Percentuali di errore incoerenti.** `round()` in Python arrotonda i mezzi al pari, quindi
   1 errore su 8 dava 12 (da 12.5) ma 3 su 8 dava 38 (da 37.5). Due margini identici che
   arrotondano in direzioni opposte, su una pagina che serve a capire dove si sbaglia di piu'.
   Aggiunta `storage.percentage(part, whole)` con half-up in aritmetica intera:
   `(200*part + whole) // (2*whole)`. Niente `Decimal`, niente float, nessuna dipendenza.
   Verificata **esaustivamente** contro `ROUND_HALF_UP`: 80199 coppie con denominatore fino a
   399, zero discordanze, e risultato sempre fra 0 e 100.
2. **`DB_PATH` senza cartella faceva crashare l'app.** `connect()` chiamava
   `os.makedirs(os.path.dirname(DB_PATH))`, e per un nome file semplice il dirname e' `""`,
   che alza `FileNotFoundError`. Ora la creazione e' condizionata alla presenza di una cartella.
   Non e' teorico: e' la configurazione naturale se si vuole il database nella cartella corrente.
Tentativo fallito: la prima versione di `percentage` la avevo scritta con `Decimal` e mi e'
uscita una riga malformata, con `quantize` applicata al denominatore invece che al quoziente.
L'aritmetica intera e' piu' corta, esatta e non importa nulla: usare quella.
Annotato per la **prossima voce** (lock SQLite in concorrenza), gia' visto leggendo il codice:
`solved_numbers` e `stats_by_kind` non chiudono la connessione se la query alza un'eccezione,
perche' il `close()` non e' in un `finally`. Con SQLite una connessione che resta aperta
trattiene il lock: e' il primo posto da guardare. Inoltre `sqlite3.connect` e' chiamata senza
`timeout`, quindi il default e' 5 secondi e poi "database is locked".
Gate: unittest 69 test OK, smoke OK. Albero pulito.

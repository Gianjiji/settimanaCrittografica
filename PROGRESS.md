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
- [x] Test di escaping: inserisci un valore con caratteri HTML in un campo e verifica che la
      pagina non lo interpreti.
- [x] Verifica che due richieste concorrenti a `/api/verifica` non producano errori di lock
      SQLite. Se succede, correggi la gestione della connessione.

**P1, usabilita'**

- [x] Invio con tasto Invio su ogni campo, e focus che resta dove serve dopo la verifica.
- [x] Controllo del layout a 360 pixel di larghezza: nessun overflow orizzontale, campi e
      bottoni raggiungibili con il pollice.
- [x] Messaggio di errore quando la verifica fallisce per rete assente, distinto da risposta
      sbagliata.
- [x] Stampa: il fascicolo su carta deve restare leggibile e senza elementi interattivi.
- [x] Contatore di schede risolte in cima al fascicolo.
- [x] `aria-invalid` sui campi errati. Aggiunta nell'iterazione 7: oggi l'errore su un campo
      e' comunicato solo dal colore, quindi non arriva a chi usa uno screen reader.

**P2, nuovi generatori, uno per iterazione**

Ogni generatore va aggiunto con: modulo in `crypto_puzzles/`, tre difficolta', tre aiuti,
`steps` da esame, `meta_value` e `meta_label`, registrazione in `GENERATORS`, property test
dedicati.

- [~] Diffie-Hellman: verifica di radice primitiva, logaritmo discreto in Z11 o Z13, chiave
      condivisa. Modulo e property test fatti; **registrazione bloccata**, vedi `## Bloccato`.
- [~] Cifrario affine: chiave da due corrispondenze note, validita' del parametro a, cifratura
      composta. Modulo e property test fatti; **registrazione bloccata**, vedi `## Bloccato`.
- [ ] Rete di Feistel a due round con funzione di round elementare, su otto bit.
- [ ] Cifrario di Hill due per due: validita' della matrice e cifratura di una parola breve.
- [ ] El Gamal in Z11: chiave pubblica, cifratura e decifratura con k piccolo.

**P3, solo dopo che P0 e P1 sono chiusi**

- [ ] Pagina di ripasso che estrae gli esercizi delle famiglie con piu' errori nel registro.
- [ ] Esportazione del fascicolo in un file stampabile.
- [ ] Cronometro per scheda, con confronto rispetto al tempo dichiarato.

## Bloccato

**P2, registrazione dei nuovi generatori in `GENERATORS`.** Il modulo Diffie-Hellman e' scritto
e testato, ma **non registrato**, perche' registrarlo violerebbe l'invariante 2.

Cosa ho provato: aggiungere un quarto modulo a `GENERATORS`.

L'errore esatto, misurato simulando l'aggiunta di un quarto generatore su `2026-W33`:

```
con 3 generatori -> 9 schede
con 4 generatori -> 12 schede
schede diverse fra le prime 9: 9 su 9
```

Il motivo e' in `_build_puzzles`: il fascicolo e' il prodotto `3 sezioni x len(GENERATORS)`,
e dentro ogni sezione c'e' `rng.shuffle(order)`. Un quarto elemento cambia sia il numero di
schede sia il consumo del generatore casuale, quindi **tutti gli arretrati verrebbero
riscritti**. L'invariante 2 lo vieta in modo esplicito, e l'invariante dice che se un
cambiamento la viola e' il cambiamento a essere sbagliato. Sono anche in conflitto il titolo
"Nove schede e una parola" e la chiave finale come somma delle nove risposte.

Due strade alternative, **entrambe da decidere fuori da questo loop** perche' cambiano il
prodotto, non il codice:

1. **Rotazione a numero costante.** Tenere nove schede scegliendo tre generatori su N per
   fascicolo. Richiede comunque un criterio che lasci intatti gli arretrati, per esempio
   fissare l'insieme dei tre generatori per tutti gli `issue_id` fino a una settimana di
   taglio e usare la rotazione solo dopo. Costo: la logica di selezione diventa condizionale
   sulla data, cosa che il PROMPT scoraggia ("non cambiare la logica del seme settimanale").
2. **Fascicolo piu' lungo dichiarato.** Accettare dodici schede e aggiornare titolo, istruzioni
   e chiave finale. Costo: gli arretrati cambiano comunque, quindi va accettato che i
   fascicoli gia' risolti non siano piu' riproducibili. E' una decisione editoriale.

Finche' non si sceglie, il modulo resta pronto e verificato ma inattivo. Le altre quattro voci
P2 sono nella stessa condizione: scriverle e' utile, registrarle no.

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

### Iterazione 5, 2026-08-13
Task: test di escaping.
Fatto: `tests/test_escaping.py`, 14 test, sette payload ostili piu' `{{7*7}}`.
**Nessun difetto trovato: l'escaping era gia' corretto.** Jinja autoescapa, `app.js` scrive
solo con `textContent`, nessun template usa `|safe`, e le rotte API non riflettono mai
l'input. Iterazione di sola copertura, ed e' un esito legittimo.
Metodo, la parte che conta: **la prima versione del test era sbagliata e dava sette falsi
positivi**. Cercavo nella pagina i frammenti `<...>` estratti dal payload, ma ogni pagina
contiene legittimamente `</script>` (per `app.js`) e `</td>` (le celle della tabella), quindi
il test "trovava" injection ovunque. Non riscrivere il test in quella forma.
Sostituito con un confronto strutturale: parsifico la pagina con `html.parser` e confronto la
sequenza di tag della pagina ostile con quella della stessa pagina resa con un valore benigno.
Se l'escaping funziona il payload produce **zero tag**, quindi le due firme sono identiche.
E' preciso e non ha falsi positivi: `javascript:alert(1)` e `';alert(1);//` non contengono tag
e infatti non vengono segnalati, correttamente.
Aggiunto anche il controllo opposto, che il payload compaia nel **testo visibile**: senza,
un template che cancella il valore invece di escaparlo passerebbe il test.
Verificato che la suite non e' vacua: introdotto `|safe` su `{{ row.kind }}` in `stats.html`,
falliscono 8 subtest fra comportamentali e strutturali; rimosso, torna tutto verde.
Superficie coperta: valori dal database resi in `/statistiche` (unico punto dove un dato
memorizzato finisce in una pagina), payload in tutti i campi delle due API, `issue_id` ostile
nell'URL e nel path, query string, piu' tre guardie sorgente (nessun `|safe` nei template,
nessun `innerHTML` in `app.js`, autoescape attivo).
Nota: oggi nessun input utente raggiunge il database, perche' `kind` e' sempre derivato dal
puzzle lato server. I test su `/statistiche` iniettano il valore ostile chiamando
`storage.log_attempt` direttamente: servono a garantire che se un domani un dato utente
arrivasse fin li', il template lo neutralizzi comunque.
Gate: unittest 83 test OK, smoke OK. Albero pulito.

### Iterazione 6, 2026-08-13
Task: concorrenza su `/api/verifica`, nessun errore di lock SQLite. **Ultima voce P0.**
Fatto: `tests/test_concurrency.py`, 9 test. Corretti **quattro** difetti in `storage.py`.
Attenzione: il primo stress test con 16 thread passava senza errori. Il difetto non si vedeva
perche' le transazioni sono minuscole e il timeout di default da 5 secondi le assorbe. Non
fidarsi di quel risultato: sono serviti scenari mirati.
1. **Journal mode `delete`: un lettore blocca lo scrittore.** Dimostrato con un lettore che
   tiene aperta una transazione mentre un'altra connessione scrive: fallisce con
   "database is locked". E' il caso reale dell'app, dove ogni pagina legge il registro e ogni
   risposta lo scrive. Passato a WAL, dove lo stesso scenario riesce.
2. **Connessioni non chiuse se la query alza un'eccezione.** `solved_numbers`, `stats_by_kind`
   e `log_attempt` chiudevano fuori da un `finally`. Con un'eccezione il traceback trattiene
   il frame, e con esso la connessione, che resta aperta con i suoi lock.
3. **`connect()` perdeva la connessione se la preparazione falliva**, cioe' se la PRAGMA o lo
   SCHEMA andavano in errore dopo la `sqlite3.connect`. Ora chiude e rilancia.
4. **La correzione (1) ha introdotto un difetto nuovo, ed e' la parte piu' importante.**
   Messa la PRAGMA WAL su ogni `connect()`, i test sono diventati **intermittenti, circa il 25%
   di fallimenti**, sempre con "database is locked". Causa: cambiare journal mode richiede un
   lock esclusivo e, a differenza delle scritture normali, ritorna SQLITE_BUSY **subito**,
   senza rispettare il busy timeout. Con 12 thread che creano il database insieme, vanno tutti
   in contesa proprio li'. Risolto eseguendo la PRAGMA **una volta per percorso**, con un
   `threading.Lock` e un set `_WAL_READY`. Lo `SCHEMA` resta invece su ogni connessione: e'
   idempotente, rispetta il busy timeout, e cosi' la tabella si ricrea se il file sparisce.
Verificato con mutation testing, una regressione alla volta: tolto WAL falliscono 2 test;
tolto il `finally` fallisce `test_no_attempt_is_lost`; tolta la chiusura in `connect()`
fallisce il test dedicato.
Tentativo fallito da non ripetere: la prima versione di quel test verificava solo che il
database restasse scrivibile dopo il fallimento. **Era vacua**: CPython chiude comunque la
connessione per refcount, quindi passava anche col difetto presente. Ora il test intercetta
`sqlite3.connect`, tiene l'oggetto e verifica che sia chiuso davvero, aspettandosi
`ProgrammingError` all'uso.
Prove finali: suite completa 5 volte di fila tutta verde, e stress separato con 32 thread,
4800 POST e 9600 GET su 5 prove, zero errori e 960/960 righe scritte a ogni prova.
Nota: WAL crea i file `-wal` e `-shm` accanto al database, dentro `instance/`, gia' ignorata.
Gate: unittest 92 test OK, smoke OK. Albero pulito.

**Stato: tutte le voci P0 sono chiuse.** Restano le cinque P1, quindi niente stringa di
completamento.

### Iterazione 7, 2026-08-13
Task: invio con Invio su ogni campo, e focus dopo la verifica. Prima voce P1.
Trovato subito: **l'invio con Invio funzionava gia'**, per submission implicita del browser.
Ogni form ha un `<button type="submit">`, e questo basta perche' Invio da un campo di testo
invii il form. Non serviva codice: serviva un test che impedisse di perdere la proprieta'.
Fatto: `tests/test_keyboard.py`, 12 test. Sette fissano il contratto del markup che rende
possibile l'invio con Invio: un solo bottone submit per form, nessun input fuori dal suo form,
tutti i campi di tipo text, nessuna textarea (che si terrebbe l'Invio per andare a capo),
e il caso delle schede a due campi.
Il difetto vero era il **focus**: dopo una verifica sbagliata restava sull'ultimo campo
digitato, non sul primo campo errato, quindi per correggere si doveva tornare col mouse.
Aggiunti `firstWrongInput` e `focusForRetry` in `app.js`: su risposta sbagliata il focus va
sul primo campo errato e ne seleziona il testo, cosi' il tasto successivo inizia la correzione.
Scelte: su risposta **giusta** il focus non viene spostato, e su **errore del server** non
viene rubato. Saltare alla scheda successiva sarebbe stato piu' invadente che utile, e
sposterebbe la pagina sotto gli occhi di chi sta leggendo l'esito.
Limite onesto di questi test, da tenere presente: i gate girano senza browser, quindi i
quattro test sul focus sono **strutturali**, guardano il sorgente di `app.js`. Non provano il
comportamento.
Per avere una prova vera ho scritto un banco separato in
`scratchpad/domharness.js`: un DOM minimo e un `fetch` finto che caricano `static/app.js` con
node ed esercitano davvero i rami. Sei scenari verdi: secondo campo errato, primo campo
errato, risposta giusta, parola errata senza array `fields`, errore dal server, messaggio
mostrato. Poi mutation test: tolta la chiamata a `focusForRetry`, 4 scenari su 6 diventano
rossi, quindi il banco non e' compiacente.
**Il banco resta fuori dal repository di proposito.** I gate devono restare cross platform e
senza dipendenze, e node non e' garantito su tutte le macchine. Se una prossima iterazione
tocca `app.js`, il banco va rifatto: sono una sessantina di righe.
Proposta annotata, non implementata per non accorpare voci: i campi errati oggi sono segnalati
solo dal colore (classe `errato`). Andrebbe aggiunto `aria-invalid`, che e' la stessa
informazione resa disponibile a chi non vede il colore. Una riga in `markFields`.
Gate: unittest 104 test OK, smoke OK. Albero pulito.

### Iterazione 8, 2026-08-13
Task: layout a 360 pixel, nessun overflow orizzontale, controlli raggiungibili col pollice.
Fatto: `tests/test_layout.py`, 8 test. Corretti i bersagli tattili in `static/style.css`.
**Overflow orizzontale: non c'e', e ora e' misurato invece che supposto.** Il token piu' lungo
prodotto dai generatori su 52 fascicoli e' di 17 caratteri, contro un budget di 28 caratteri
monospace nella larghezza utile di una scheda a 360px. Il test lo ricalcola dai generatori
veri, quindi un domani un generatore che emettesse una stringa lunga lo farebbe fallire.
**Difetto trovato e corretto: i controlli erano troppo piccoli per il pollice.** Il minimo
ragionevole e' 44px. Erano: campi di risposta circa 37px, bottoni circa 34px, e soprattutto i
`summary` degli aiuti circa 18px, perche' sono solo testo a 0.72rem senza padding. Sono i
controlli che si toccano di piu' in tutta la pagina. Aggiunte tre regole nel blocco
`@media (max-width: 640px)` con `min-height: 44px`, piu' padding sui summary.
Verificato con mutation testing: tolta una qualunque delle tre regole il test relativo passa
al rosso, e abbassando il valore a 30px il test lo segnala col numero esatto.
**Errore mio, da non ripetere: ho affermato che non c'erano media query.** Le avevo cercate
con un grep il cui output era troncato. Il foglio di stile ha gia' un blocco
`max-width: 640px` che a schermo stretto libera le colonne fisse da 9rem e manda il bottone a
tutta larghezza. Prima di dire che una cosa manca, leggere il file.
Sulla verifica col browser, perche' non riprovarla a vuoto: ho avviato l'app e provato a
misurare con Chrome. **Non funziona in questo ambiente**, per due motivi indipendenti.
Primo, Chrome non scende sotto la sua larghezza minima di finestra, quindi un viewport da
360px non si ottiene ridimensionando. Secondo, e decisivo, Chrome non raggiunge il server
locale: sia `127.0.0.1` sia `localhost` danno "connessione negata", mentre `curl` risponde
200. Il tool di navigazione riporta comunque "Navigated to", quindi il fallimento e' muto.
Ci sono cascato: **ho misurato e riportato "zero overflow" su quella che era la pagina di
errore di Chrome**. Il campanello d'allarme era `location.origin` uguale a `null` e zero
input trovati in una pagina che ne ha venti. Se una prossima iterazione prova col browser,
verificare **sempre** l'identita' del documento prima di misurare, per esempio con
`document.querySelector('form.risposta')`, e non fidarsi dell'esito del navigate.
Conseguenza onesta: i test di questa voce sono statici, ragionano sul CSS dichiarato e sui
dati dei generatori. Le altezze reali dipendono anche dal font di sistema, quindi il
controllo a occhio su un telefono vero resta da fare.
Gate: unittest 112 test OK, smoke OK. Albero pulito.

### Iterazione 9, 2026-08-13
Task: messaggio di rete assente distinto dalla risposta sbagliata.
Fatto: `tests/test_client_errors.py`, 10 test. Riscritta la gestione errori in `app.js`.
Trovato: il difetto era piu' largo di come e' scritto nel backlog. `post()` **non guardava mai
`response.ok`**, e il `.catch` finale attribuiva a "offline" qualunque fallimento. Quindi un
errore del server finiva nel ramo della risposta sbagliata e mostrava "Non torna. Rileggi
l'aiuto 2", cioe' **il lettore veniva accusato di un errore che non aveva fatto**.
Precisazione, perche' prima l'avevo detta male: con un 500 i campi non venivano dipinti di
rosso. `data.fields` e' `undefined`, e `markFields` in quel caso ripulisce invece di segnare.
Il danno era solo, ma seriamente, nel messaggio.
Ora tre esiti separati: risposta sbagliata (verdetto vero), richiesta mai arrivata al server
(`OFFLINE`), server che risponde qualcosa di inutilizzabile (`SERVER`). I due messaggi di
fallimento dicono esplicitamente che la risposta **non e' stata verificata**, e i marchi sui
campi vengono ripuliti, perche' un rosso rimasto da un tentativo precedente si leggerebbe
come verdetto. Un 404 o 400 che porta con se' `{"error": ...}` resta trattato come risposta
legittima e mostra quel messaggio: e' un rifiuto motivato, non un guasto.
Verifica vera con node, stesso metodo dell'iterazione 7, banco in `scratchpad/errharness.js`:
11 controlli su 6 scenari (rete assente, 500 con HTML, 500 con JSON vuoto, 404 con `error`,
risposta sbagliata, risposta giusta). **Confronto prima/dopo sulla stessa versione del banco:
4 controlli rossi sul codice precedente, 0 su quello attuale.** Il banco resta fuori dal
repository, come l'altro: node non e' garantito e i gate devono restare senza dipendenze.
Due errori miei in questa iterazione, entrambi corretti:
1. Ho scritto "undici scenari verdi" **prima di aver letto l'esito**, che era troncato
   nell'output. Ricontrollato contando le righe: era giusto, ma l'ho affermato senza saperlo.
   Contare, non dedurre.
2. Due test cercavano il `.catch` del gestore usando `rindex(".catch(")` sull'intero file, che
   trova invece quello della registrazione del service worker. Ora isolano prima la regione
   del gestore submit. Se servono altri test sul client, isolare sempre la regione.
Il service worker intercetta solo le GET, quindi non maschera i fallimenti delle POST all'API:
verificato prima di toccare il codice.
Gate: unittest 122 test OK, smoke OK. Albero pulito.

### Iterazione 10, 2026-08-13
Task: stampa leggibile e senza elementi interattivi.
Fatto: `tests/test_print.py`, 7 test. Una riga di CSS aggiunta.
Il blocco `@media print` c'era gia' e nascondeva correttamente menu, form, aiuti e link alle
soluzioni. Ho incrociato i selettori nascosti col DOM vero delle due pagine stampabili: **109
elementi interattivi sul fascicolo, tutti coperti**. Nessun controllo sfugge.
Trovato invece un difetto di leggibilita' che nessuno vedrebbe finche' non stampa:
**`.scheda-numero` aveva fondo blu e testo bianco.** I browser non stampano i colori di sfondo
per default, quindi sul foglio restava bianco su bianco e **il numero della scheda spariva**.
Su un fascicolo di nove esercizi numerati e' esattamente l'informazione che serve. Corretto
nel blocco print con fondo trasparente, testo scuro e un bordo che tiene la forma del riquadro.
Cercate altre occorrenze dello stesso schema: solo `.risposta button`, che pero' sta dentro
`.risposta`, gia' nascosta in stampa. Il test lo verifica in generale, non caso per caso:
qualunque regola con testo bianco deve essere nascosta in stampa oppure avere un colore
esplicito nel blocco print.
Il test piu' utile e' quello che deriva i selettori nascosti **dal CSS** e li verifica contro
gli antenati di ogni elemento interattivo **del DOM**: non elenca i controlli a mano, quindi
un controllo aggiunto domani fuori dai contenitori nascosti lo fa fallire da solo.
Errore mio: la prima versione pretendeva che ogni pagina stampabile avesse controlli da
nascondere, e falliva sulla pagina delle soluzioni, che giustamente non ne ha. Ora la
non-vacuita' e' un test separato sul solo fascicolo.
Verificato con mutation testing: tolta la correzione di `.scheda-numero` il test la segnala;
tolto `.risposta` dai selettori nascosti diventano rossi form, input e button separatamente.
Non toccato di proposito: il timbro "risolto" continua a stamparsi. E' informazione utile su
carta, sapere quali schede erano gia' chiuse, e non e' un elemento interattivo.
Gate: unittest 129 test OK, smoke OK. Albero pulito.

### Iterazione 11, 2026-08-13
Task: contatore di schede risolte in cima al fascicolo.
Fatto: `tests/test_counter.py`, 12 test. Una riga nel template, una funzione in `app.js`.
Voce di sola aggiunta: non c'era niente di rotto da correggere.
Lato server il contatore si calcola nel frontespizio filtrando `issue.puzzles` su `solved`.
**Non uso `solved | length`**, che sarebbe la scrittura ovvia e sarebbe **sbagliata**: la
parola della settimana viene registrata come scheda numero 0, quindi risolvendo la parola il
contatore direbbe "1 di 9" senza che nessuna scheda sia stata risolta. Filtrando sui puzzle
veri il numero 0 non puo' entrare. C'e' un test dedicato, e la mutazione a `solved | length`
lo fa fallire.
Lato client la pagina non si ricarica mai, quindi `refreshCounter()` riconta `.scheda.risolta`
nel DOM a ogni scheda chiusa. **Ricontare invece di incrementare un totale** e' voluto: non
esiste un contatore separato che possa sfasarsi rispetto a quello che si vede.
Verifica vera con node, banco in `scratchpad/countharness.js`: 6 controlli, parte da 0 di 9,
sale a 1 e 2, **risolvere due volte la stessa scheda resta 2 di 9**, arriva a 9 di 9, e una
risposta sbagliata non lo muove. Tutti verdi.
Aggiunto `role="status"` al contatore, cosi' l'aggiornamento viene annunciato: senza, chi usa
uno screen reader non saprebbe mai che il numero e' cambiato, perche' la pagina non ricarica.
Errore mio, corretto: un test verificava `assertIn("Counter", solved_branch + self.source)`.
Concatenando l'intero sorgente **passava sempre**, qualunque cosa facesse il codice. Ora
isola la riga che aggiunge `risolta` e pretende la chiamata sulla stessa riga, cosi' marcare
la scheda e ricontare non possono separarsi. Attenzione a questa forma di test finto: era la
seconda volta in poche iterazioni.
Gate: unittest 141 test OK, smoke OK. Albero pulito.

### Iterazione 12, 2026-08-13
Task: `aria-invalid` sui campi errati. **Ultima voce P1.**
Fatto: `tests/test_field_state.py`, 6 test, piu' otto righe in `markFields`.
Un campo sbagliato era segnalato solo dalla classe `errato`, cioe' solo dal colore. Ora porta
anche `aria-invalid="true"`, e l'attributo viene **rimosso** quando il campo torna corretto.
Messo dentro `markFields`, nello stesso punto che decide il colore: due posti che decidono la
stessa cosa si sfaserebbero. C'e' un test che verifica che `aria-invalid` non compaia altrove.
Verifica con node, banco in `scratchpad/ariaharness.js`, 7 controlli verdi. Il caso che conta
di piu' e' l'ultimo: **quando la rete cade lo stato di invalidita' viene ripulito su tutti i
campi**, perche' nessun verdetto e' stato emesso. Senza, un campo sarebbe rimasto annunciato
come sbagliato per una verifica che non e' mai avvenuta. Funziona perche' l'iterazione 9 ha
messo `markFields(form, null)` nel ramo di fallimento: le due voci si incastrano.
Verificato anche che una pagina appena servita non contenga `aria-invalid`: e' lo stato di un
verdetto, non una proprieta' del campo.

## Riepilogo, dodici iterazioni

Tutte le voci **P0 e P1 sono chiuse**: 12 su 20. Restano aperte le 5 voci P2, i nuovi
generatori, e le 3 voci P3.

Difetti reali trovati e corretti, in ordine di gravita':
1. **I placeholder rivelavano la risposta** (iter. 2). Gli esempi fissi del coincidenzario
   coincidevano con l'IC vero per certi semi, e il campo di Shamir mostrava `0..p-1`, dove
   `p-1` e' il segreto quando e' massimo. Violava l'invariante 4.
2. **Tre cause distinte di 500 nell'API** (iter. 3), tutte dalla stessa radice: `x or {}` non
   filtra, perche' una lista o un dict non vuoti sono truthy. Serviva un controllo di tipo.
3. **Errori di lock SQLite in concorrenza** (iter. 6), quattro difetti, fra cui uno
   **introdotto dalla correzione stessa**: la PRAGMA WAL su ogni connessione causava un 25%
   di fallimenti intermittenti.
4. **Un errore del server veniva mostrato come risposta sbagliata** (iter. 9): `post()` non
   guardava `response.ok`.
5. **Percentuali di errore incoerenti** (iter. 4): `round()` arrotonda i mezzi al pari, quindi
   12.5 dava 12 e 37.5 dava 38.
6. **Il numero della scheda spariva in stampa** (iter. 10): bianco su fondo scuro, e i browser
   non stampano gli sfondi.
7. **Controlli troppo piccoli per il pollice** (iter. 8): gli aiuti erano alti 18px contro 44.
8. **`DB_PATH` senza cartella faceva crashare l'app** (iter. 4).
9. Focus non spostato sul campo da correggere (iter. 7), contatore assente (iter. 11),
   invalidita' comunicata solo dal colore (iter. 12).

Due voci non hanno prodotto correzioni, ed e' un esito legittimo: l'escaping era gia' corretto
(iter. 5) e l'invio con Invio funzionava gia' per submission implicita (iter. 7).

Da 14 test iniziali a 147, piu' `tools/smoke.py`. Ogni correzione e' stata verificata con
mutation testing, rimettendo il difetto e controllando che il test diventasse rosso.

Cose da sapere per chi continua:
- **I test sul client sono strutturali**, guardano il sorgente di `app.js`. I gate girano
  senza browser e node non e' garantito. Le prove comportamentali vere le ho fatte con quattro
  banchi DOM sotto node, tenuti **fuori dal repository** in `scratchpad/`: `domharness.js`,
  `errharness.js`, `countharness.js`, `ariaharness.js`. Se tocchi `app.js`, vanno rifatti.
- **Chrome non raggiunge il server locale in questo ambiente** e non scende sotto la sua
  larghezza minima di finestra. Non riprovarci senza prima verificare l'identita' del
  documento: ci sono cascato e ho riportato misure prese sulla pagina di errore.
- Il layout a 360px e le altezze dei controlli sono verificati **staticamente**. Un controllo
  a occhio su un telefono vero resta da fare.
- La parola della settimana compare come testo normale nelle pagine, perche' `META_WORDS` e'
  lessico crittografico. Non e' una fuga: e' protetta dalla chiave di Cesare. Non tentare di
  "correggerlo" cambiando `META_WORDS`, riscriverebbe tutti gli arretrati.
Gate: unittest 147 test OK, smoke OK. Albero pulito.

### Iterazione 13, 2026-08-13
Task: prima voce P2, generatore Diffie-Hellman.
Fatto: `crypto_puzzles/diffie_hellman.py` con tre difficolta', `DH_MODULI` e `PRIMITIVE_ROOTS`
in `tables.py`, e `tests/test_diffie_hellman.py` con 20 test su 400 semi per difficolta'.
**Non registrato in `GENERATORS`, ed e' il punto centrale dell'iterazione.** Prima di scrivere
una riga ho controllato `_build_puzzles` e verificato sul campo cosa succede con un quarto
generatore: 12 schede invece di 9, e **tutte e nove le schede esistenti cambiano**. Il
fascicolo e' `3 sezioni x len(GENERATORS)`, e lo `rng.shuffle` interno consuma casualita'
diversa. Violerebbe l'invariante 2 e smentirebbe il titolo "Nove schede e una parola".
Dettagli e due strade alternative nella sezione `## Bloccato`. La decisione e' editoriale, non
tecnica: o si accetta che gli arretrati cambino, o si introduce una selezione condizionata
alla data, che il PROMPT scoraggia. Non e' una scelta che spetta a questo loop.
Le tre schede: chiave condivisa (facile), logaritmo discreto (media), riconoscere quale di due
basi e' radice primitiva piu' l'ordine dell'altra (difficile, due campi).
I test non controllano solo la forma ma **la matematica**: la chiave condivisa deve coincidere
con quella che calcola Bob, l'esponente deve risolvere davvero la sua equazione, la base del
logaritmo deve essere un generatore, esattamente uno dei due candidati deve esserlo, e
l'ordine dichiarato deve dividere p-1 e riportare la base a 1. Verificato con mutation
testing: tre sabotaggi distinti del generatore, ognuno colto su tutti e 400 i semi.
Ristretto a Z11 e Z13 come indica il backlog: la tabella delle potenze resta di dieci o dodici
righe, costruibile a mano. Con Z23 sarebbero ventidue righe, fuori dal "calcolo a mente".
Errore mio, gia' visto nell'iterazione 2 e ripetuto: il test "il primo aiuto non da' la
risposta" cercava il valore come sottostringa e dava 30 falsi positivi, perche' il numero nel
primo aiuto e' la **base** e ogni tanto coincide col risultato. Ora la regola e' precisa: un
numero gia' stampato nell'enunciato non e' una fuga, perche' non aggiunge informazione; lo
sarebbe solo un numero che compare per la prima volta nel primo aiuto.
Aggiunto un test che verifica che il modulo **non** sia in `GENERATORS` e che il fascicolo
faccia ancora nove schede: se qualcuno lo registrasse per distrazione, il gate lo ferma.
Gate: unittest 167 test OK, smoke OK. 52 fascicoli arretrati verificati, tutti a 9 schede.

### Iterazione 14, 2026-08-13
Task: seconda voce P2, cifrario affine. Stesso blocco sulla registrazione dell'iterazione 13.
Fatto: `crypto_puzzles/affine.py` e `tests/test_affine.py`, 26 test su 400 semi per difficolta'.
Le tre schede seguono le tre parti chieste dal backlog: quale dei due moltiplicatori e'
ammissibile piu' una cifratura (facile), chiave ricavata da due corrispondenze note (media),
due cifrari in cascata ridotti a uno solo piu' una cifratura (difficile, tre campi).
Una trappola matematica che ho dovuto gestire nella scheda media: **due corrispondenze non
sempre determinano la chiave**. Il sistema si riduce a `a (x1 - x2) = y1 - y2 mod 26`, che ha
soluzione unica solo se `x1 - x2` e' invertibile modulo 26. Sorteggiando le posizioni a caso,
circa la meta' delle coppie darebbe un esercizio con piu' chiavi valide, cioe' senza risposta
univoca. Il generatore risorteggia finche' la differenza non e' coprima con 26, e c'e' un test
che lo verifica su tutti i semi. Togliendo quella condizione il test produce 14 errori.
Verificato con mutation testing, cinque sabotaggi distinti: A composto sbagliato (800
fallimenti), B composto sbagliato (367), coppie non determinanti (14 errori), moltiplicatore
non ammissibile (400), lettera composta sbagliata (400).
Il test piu' forte e' quello sulla composizione: non confronta una formula con se' stessa, ma
verifica su **tutte e 26 le lettere** che il cifrario composto dia lo stesso risultato di
applicare i due cifrari in sequenza. E' il motivo per cui il sabotaggio su A produce 800
fallimenti invece di 400.
Gate: unittest 193 test OK, smoke OK. 52 arretrati ancora a 9 schede.

# Ralph loop, La Settimana Crittografica

Sei un ingegnere che collauda e migliora questa applicazione, una iterazione alla volta.
Questo file viene re-iniettato identico a ogni iterazione: **la memoria del loop sta su disco,
non nel contesto**. Prima di qualunque decisione leggi `PROGRESS.md`.

## Cosa e' l'applicativo

Flask. Genera un fascicolo settimanale di nove esercizi di crittografia da risolvere a mente,
piu' una parola finale cifrata con Cesare la cui chiave e' la somma delle nove risposte modulo 26.
Il seme e' la settimana ISO, quindi ogni fascicolo e' riproducibile per sempre.

```
app.py                 rotte e API di verifica
storage.py             log tentativi su SQLite
crypto_puzzles/        core.py, tables.py, coincidence.py, rsa_chain.py, secret_sharing.py, fascicle.py
templates/ static/     Jinja, CSS, service worker
tests/                 property test sugli invarianti
```

## Regola d'oro

**Una sola voce di backlog per iterazione.** Non accorpare, non anticipare. Meglio dieci
iterazioni piccole e verificate che una grande e rotta.

Sequenza obbligatoria di ogni iterazione:

1. Leggi `PROGRESS.md`. Se non esiste, esegui il Bootstrap qui sotto e fermati.
2. Esegui i gate di verifica. Se un gate fallisce, **il task dell'iterazione e' quel fallimento**,
   qualunque cosa dica il backlog.
3. Se i gate passano, prendi la prima voce non chiusa del backlog in `PROGRESS.md`.
4. Implementa. Scrivi prima il test che fallisce, poi il codice che lo fa passare.
5. Riesegui tutti i gate.
6. Aggiorna `PROGRESS.md`, committa, esci.

## Bootstrap (solo se `PROGRESS.md` manca)

- `git init` se non e' gia' un repository, poi commit iniziale di tutto lo stato attuale.
- Crea `PROGRESS.md` con il backlog della sezione "Backlog iniziale" copiato voce per voce,
  ognuna con stato `[ ]`, piu' una sezione `## Diario` vuota.
- Crea `tools/smoke.py`: usa `app.test_client()` (niente server, niente curl, niente bash
  specifico) e verifica che rispondano 200 la home dopo redirect, il fascicolo corrente,
  le soluzioni, l'archivio, le statistiche, e 404 un fascicolo inesistente.
- Non implementare altro. Committa e esci.

## Gate di verifica

Tutti da riga di comando, tutti cross platform:

```
python -m unittest discover -s tests -v
python tools/smoke.py
```

Un'iterazione non e' chiusa se anche solo uno dei due fallisce, o se hai lasciato file
temporanei, database `instance/` o `__pycache__` nel commit.

## Invarianti non negoziabili

Se un cambiamento li viola, il cambiamento e' sbagliato, non l'invariante.

1. **Calcolo a mente.** Moduli solo fra 11, 13, 17, 19, 23, 26. Moduli RSA sotto 221.
   Esponente pubblico fino a 17, chiave privata fino a 33. Numeratori IC e MIC sotto 30,
   parole di massimo nove lettere. Ogni nuovo generatore deve avere un property test che
   verifica i suoi limiti su almeno 400 semi.
2. **Riproducibilita'.** Stesso `issue_id`, stesso fascicolo, sempre. Non toccare lo schema
   del seme: romperebbe tutti gli arretrati gia' risolti.
3. **Aiuti progressivi.** Tre aiuti per scheda, in ordine procedura, passo bloccante, quasi
   soluzione. Mai la risposta al primo aiuto.
4. **La pagina del fascicolo non contiene le risposte.** Ne' nel markup, ne' negli attributi
   dati, ne' nei commenti HTML. La verifica avviene solo lato server. Questo e' un test, non
   una raccomandazione.
5. **Ogni scheda dichiara `meta_label`**, cioe' quale numero porta alla parola finale.
6. **Fedelta' all'esame.** Gli esercizi imitano la forma degli appelli del corso: dati piccoli,
   procedura esplicita, passaggi che varrebbero punti. I `steps` sono la soluzione ragionata,
   non solo il risultato.
7. **Lingua.** Codice, nomi e commenti in inglese. Testo mostrato all'utente in italiano.
   Commenti solo dove il codice non si spiega da solo.
8. **Niente emoji e niente caratteri decorativi** nel codice e nell'interfaccia.
9. **Dipendenze.** Solo libreria standard piu' Flask. Niente framework frontend, niente CDN,
   niente build step. Se una feature richiede una dipendenza nuova, non farla: annotala in
   `PROGRESS.md` come proposta e passa oltre.

## Backlog iniziale

Ordinato per rapporto valore su rischio. Non riordinarlo di tua iniziativa: se trovi qualcosa
di piu' urgente, aggiungilo in cima con una riga di motivazione nel Diario.

**P0, collaudo**

- [ ] `tools/smoke.py` come da Bootstrap.
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

## Formato di `PROGRESS.md`

```
# Stato

## Backlog
- [x] P0 voce chiusa
- [ ] P0 voce successiva
...

## Diario
### Iterazione 7, 2026-08-20
Task: test API con payload malformati.
Fatto: aggiunto tests/test_api.py, 6 casi.
Trovato: /api/verifica andava in 500 con answers non lista. Corretto in app.py.
Gate: unittest 20 test OK, smoke OK.
Commit: a1b2c3d
```

Il Diario e' la parte importante: e' l'unica cosa che la prossima iterazione sa di te.
Scrivi anche i tentativi falliti e il motivo, cosi' non li ripete.

## Divieti

- Non riscrivere l'architettura, non introdurre un framework, non spostare i file.
- Non modificare i vincoli numerici per far passare un test: il test ha ragione.
- Non cambiare la logica del seme settimanale.
- Non committare `instance/`, `__pycache__`, ambienti virtuali.
- Non lasciare il repository con i test rossi alla fine di un'iterazione. Se non riesci a
  chiudere il task, ripristina lo stato pulito con git e annota il blocco nel Diario.

## Condizione di uscita

Emetti la stringa di completamento **solo** quando tutte le voci P0 e P1 sono chiuse e
entrambi i gate passano. Prima di emetterla, scrivi nel Diario un riepilogo di cosa e'
cambiato e cosa resta aperto.

Stringa da emettere in quel caso, da sola su una riga:

```
<promise>FASCICOLO-OK</promise>
```

Se dopo dieci iterazioni consecutive lo stesso task resta aperto, non emettere niente:
scrivi in `PROGRESS.md` una sezione `## Bloccato` con cosa hai provato, l'errore esatto e due
strade alternative, poi passa alla voce successiva del backlog.

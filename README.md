# La Settimana Crittografica

Fascicolo settimanale di esercizi di crittografia da risolvere a mente, generati sui temi
ricorrenti degli appelli. Nove schede a difficoltà crescente più una parola finale che si
scopre solo se le nove risposte sono tutte giuste.

## Avvio rapido (PowerShell)

```powershell
cd $HOME\settimana-crittografica
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Poi apri http://localhost:5000

### Usarlo dal telefono sulla stessa rete

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.PrefixOrigin -ne "WellKnown" } | Select-Object IPAddress, InterfaceAlias
New-NetFirewallRule -DisplayName "Settimana Crittografica" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
```

Dal telefono apri http://INDIRIZZO-IP:5000

Attenzione: su http semplice il service worker non si registra, quindi niente installazione
come app e niente uso offline. I browser considerano contesto sicuro solo https e localhost.
Per avere la PWA vera servono https (dominio con certificato, un tunnel tipo Cloudflare Tunnel,
oppure Tailscale con il suo certificato). Il sito resta comunque usabile via http.

## Struttura

```
app.py                     rotte Flask e API di verifica
storage.py                 log dei tentativi su SQLite, alimenta il registro errori
crypto_puzzles/
  core.py                  modello Puzzle, aritmetica modulare, controllo risposte
  tables.py                liste chiuse di parole, primi, moduli, inversi
  coincidence.py           IC, MIC, Kasiski
  rsa_chain.py             Euclide esteso, esponenziazione veloce, fattorizzazione da phi
  secret_sharing.py        schemi (n,n) e Shamir (k,n)
  fascicle.py              monta il fascicolo settimanale e la parola finale
templates/                 pagine Jinja
static/                    stile, script, service worker, manifest
tests/                     property test sugli invarianti
```

## Le regole che tengono in piedi il progetto

1. Moduli ammessi soltanto 11, 13, 17, 19, 23, 26. Moduli RSA sotto 221.
2. Esponente pubblico fino a 17, chiave privata fino a 33.
3. Numeratori di IC e MIC sotto 30, parole di massimo nove lettere.
4. Ogni scheda espone tre aiuti progressivi, mai la soluzione al primo tocco.
5. Ogni scheda dichiara quale numero porta alla parola finale.

Gli invarianti non sono commenti, sono test: `tests/test_generators.py` genera centinaia di
puzzle per ogni famiglia e verifica che nessuno esca dai limiti. Se un generatore nuovo li
viola, la suite fallisce.

```powershell
python -m unittest discover -s tests -v
```

## Aggiungere una famiglia di esercizi

1. Crea `crypto_puzzles/nuova_famiglia.py` con una funzione `generate(rng, difficulty)` che
   ritorna un `Puzzle`.
2. Compila sempre `hints` (tre), `steps` (la procedura da esame), `meta_value` e `meta_label`.
3. Aggiungi il modulo alla lista `GENERATORS` in `fascicle.py`.
4. Aggiungi i test degli invarianti in `tests/test_generators.py`.

Il fascicolo prende tre schede per famiglia, una per grado di difficoltà, quindi ogni nuova
famiglia allunga il fascicolo di tre schede.

## Perché i fascicoli sono riproducibili

Il seme è il numero della settimana ISO, quindi `2026-W33` genera sempre le stesse nove schede,
su qualunque macchina e in qualunque momento. Non c'è niente da salvare: gli arretrati si
ricostruiscono al volo. L'unica cosa che finisce nel database sono i tentativi, che servono a
compilare il registro degli errori.

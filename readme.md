
# Music Player

Web player per ascoltare la propria musica dal browser. Supporta file `.mp3` e
`.flac`, copertine, testi, accordi, download da YouTube e Google Home.

## Requisiti

- Python 3
- FFmpeg installato e disponibile nel `PATH`
- Una o piu' cartelle contenenti la musica

## Installazione locale

Dalla cartella del progetto eseguire:

```bash
pip install -r requirements.txt
```

Configurare poi `config.yaml` e avviare il server:

```bash
python server.py
```

Aprire [http://localhost](http://localhost) nel browser. Il server usa la
porta `80` per impostazione predefinita.

## Configurazione

Il file `config.yaml` contiene le cartelle musicali e le impostazioni del
player:

```yaml
Cartelle:
  "Tha Supreme": "X:\\Musica\\Tha Supreme"
  "YouTube": "YT_FOLDER"

ALBUM_ORDER:
  - "23 6451"
  - "CASA GOSPEL"

ALBUM_FINTI:
  - "Beat"
  - "Acustiche"

IP_per_google_home: "192.168.1.8"
PORT: 80
```

- `Cartelle`: associa il nome mostrato nell'app al percorso della cartella.
- `YouTube`: deve rimanere nella configurazione. Il percorso `YT_FOLDER` puo'
  essere modificato, ma il nome `YouTube` no.
- `ALBUM_ORDER`: definisce l'ordine degli album.
- `ALBUM_FINTI`: indica gli album da trattare come raccolte di brani singoli.
- `IP_per_google_home`: indirizzo IP del dispositivo Google Home.
- `PORT`: porta del server.

## Accordi

Gli accordi delle canzoni possono essere inseriti in `chords.json`:

```json
{
  "Babydoll.flac": ["1Dm", "2A", "1Gm"]
}
```

In `1Dm`, `1` indica una forma dell'accordo, `D` e' la nota e `m` indica un
accordo minore.

## Avvio con Docker

Con Docker installato, avviare il progetto con:

```bash
docker compose up -d
```

La configurazione Docker usa `import_docker` come cartella della musica e
pubblica il player sulla porta 80. Per fermarlo:

```bash
docker compose down
```
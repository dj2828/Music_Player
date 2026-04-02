
# Music Player

## config.yaml

`Cartelle` Nome e Path della cartella

Es: `Cartelle:
  "Tha Supreme": "X:\\cartelllla\\canz\\fr\\thasup"`

**NON CANCELLATE `"YouTube": "YT_FOLDER"`**

`ALBUM_ORDER: {Ordine album}"`
  Es: 
  ```yaml
  ALBUM_ORDER:
  - "23 6451"
  - "c@ra++ere spec!@le"
  - "sFaCioLaTe miXTaPe"
  - "CASA GOSPEL"
  ```
`ALBUM_ORDER: {Album finti(quelli con le copertine diverse da canzone a canzone)}"`
  Es: 
  ```yaml
  ALBUM_FINTI:
  - "Beat"
  - "Acustiche"
  - "Sparse"
  - "Freestyle"
  ```
`IP_per_google_home: {Indirizzo IP locale}` Es: `IP_per_google_home: "192.168.1.8"`

`PORT: {Porta}` Default: 80

## chords.json
```json
{
    "Fr/Babydoll.flac": {
        "D": "minor",
        "A": "major",
        "1G": "minor"
    }
}
```
(`1G` 1 è un' altra forma dell' accordo)

# Per startare
apri `server.py`
## [Link sulla porta 80](http://localhost)

(serve anche ffmpeg bel path)
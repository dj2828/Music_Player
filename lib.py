import pychromecast, os, yt_dlp, difflib, tempfile, subprocess, hashlib, re
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, USLT
from requests import get
import yaml, json

# Inizializziamo la variabile globale per evitare errori di "NameError"
chromecast = None
DEVICE_NAME = "Studio_mini" # Nome del dispositivo da cercare

def init_google_home():
    global chromecast
    try:
        print("Scansione dispositivi Chromecast in corso...")
        # FIX: Aggiunto blocking=True come nel main.py, altrimenti non trova nulla
        devices, browser = pychromecast.get_chromecasts(blocking=True)
        
        # Debug: mostra i dispositivi trovati
        for cc in devices:
            print(f"- Trovato: {cc.name}")

        # Cerca il dispositivo (case insensitive)
        chromecast = next(
            (cc for cc in devices if DEVICE_NAME.lower() in cc.name.lower()), 
            None
        )

        if chromecast:
            chromecast.wait()
            print(f"✅ Connesso con successo a: {chromecast.name}")
            return True
        else:
            print(f"❌ Dispositivo '{DEVICE_NAME}' non trovato nella lista.")
            return False

    except Exception as e:
        print(f"❌ Errore durante l'inizializzazione: {e}")
        return False

def playG(url):
    global chromecast
    
    # Controllo di sicurezza: se non siamo connessi, proviamo a riconnetterci
    if chromecast is None:
        print("⚠️ Chromecast non connesso. Tento la connessione...")
        if not init_google_home():
            return

    try:
        mc = chromecast.media_controller
        
        if url == "play":
            print("▶️ Play su Google Home")
            mc.play()
        elif url == "pause":
            print("⏸️ Pausa su Google Home")
            mc.pause()
        elif url == "stop":
            print("⏹️ Google Home stop")
            mc.stop()
        else:
            print(f"🎵 Avvio riproduzione: {url}")
            mc.play_media(url, "audio/mp3")
            mc.block_until_active()
            mc.play()
    except Exception as e:
        print(f"Errore nel comando playG: {e}")

def volG(vol):
    global chromecast
    try:
        chromecast.set_volume(float(vol))
    except Exception as e:
        print(f"Errore nel comando volG: {e}")

def getSimileCanz(data, songs_by_folder):
    print("Canzone richiesta:", data)
    canz = difflib.get_close_matches(data, songs_by_folder, n=1, cutoff=0)
    print("Canzone trovata:", canz[0])
    return canz[0].replace('[', '').replace(']', '')

def down(url, MUSIC_FOLDER):
    ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(MUSIC_FOLDER, '%(title)s.%(ext)s'),
            'writethumbnail': True,
            'postprocessors': [
                {  # Converti audio in mp3
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                },
                {  # Converte la thumbnail in jpg
                    'key': 'FFmpegThumbnailsConvertor',
                    'format': 'png',
                },
                {  # Inserisce la copertina nel file MP3
                    'key': 'EmbedThumbnail',
                }]}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return True
    except Exception as e:
        print("Errore durante il download:", e)
        return False

def search_videos(query, max_results=5):
    """
    Cerca video su YouTube e ritorna una lista con i risultati.
    
    Args:
        query: stringa di ricerca
        max_results: numero di risultati da ritornare (default 5)
    
    Returns:
        Lista di dizionari con info video (title, url, duration, channel)
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': 'in_playlist',
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            results = ydl.extract_info(f'ytsearch{max_results}:{query}', download=False)
        
        videos = []
        for entry in results['entries']:
            videos.append({
                'title': entry.get('title'),
                'url': f"https://www.youtube.com/watch?v={entry.get('id')}",
                'channel': entry.get('uploader'),
            })
        
        return videos
    except Exception as e:
        print(f"Errore durante la ricerca: {e}")
        return []

def get_cached_mp3(file_path, cache_dir="cache_mp3"):
    """
    Gestisce la conversione MP3 con un sistema di cache dedicata.
    """
    # 1. Se è già MP3, non serve cache
    if file_path.lower().endswith('.mp3'):
        return file_path

    # 2. Crea la cartella di cache se non esiste
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    # 3. Genera un ID univoco basato sul path assoluto del file
    # Usiamo l'hash per evitare problemi con caratteri speciali o path troppo lunghi
    file_id = hashlib.md5(os.path.abspath(file_path).encode()).hexdigest()
    cached_path = os.path.join(cache_dir, f"{file_id}.mp3")

    # 4. CONTROLLO: Se il file in cache esiste già, lo restituiamo subito
    if os.path.exists(cached_path):
        print(f"✅ Cache hit: Uso il file già convertito -> {cached_path}")
        return cached_path

    # 5. Se non esiste, convertiamo
    print(f"⚙️ Cache miss: Conversione in corso per {os.path.basename(file_path)}...")
    
    command = [
        'ffmpeg', '-i', file_path,
        '-vn', '-ar', '44100',
        '-ac', '2', '-b:a', '192k',
        cached_path, '-y'
    ]

    try:
        # Usiamo capture_output=True per non sporcare la console con i log di ffmpeg
        subprocess.run(command, check=True, capture_output=True)
        return cached_path
    except subprocess.CalledProcessError as e:
        print(f"❌ Errore conversione: {e}")
        if os.path.exists(cached_path):
            os.unlink(cached_path)
        return None

def get_testo(file_path, DOCKER=False):
    def pulisci_testo(testo_raw):
        # Rimuove solo metadati tipo [ti:...] [ar:...] ecc.
        testo = re.sub(r'\[[a-z]+:.*?\]', '', testo_raw, flags=re.IGNORECASE)
        
        # Mantiene i timestamp
        linee = [riga.strip() for riga in testo.splitlines() if riga.strip()]
        return "\n".join(linee)
    
    testo = ""

    if file_path.endswith('.flac'):
        audio = FLAC(file_path)
        if "LYRICS" in audio:
            testo = audio["LYRICS"][0]

    elif file_path.endswith('.mp3'):
        audio = MP3(file_path, ID3=ID3)
        for tag in audio.values():
            if isinstance(tag, USLT):
                testo = tag.text

    if not testo.strip():
        path = f'{file_path.split("\\")[-1].split(".")[0]}' if not DOCKER else f'{file_path.split("/")[-1].split(".")[0]}'
        print(f"Testo non trovato nei metadati, cerco online... '{path}'")
        response = get(f"https://lrclib.net/api/search?q={path}")
        if response.status_code == 200:
            dati = response.json()
            
            if dati:  # Controlliamo che la lista non sia vuota
                # Prendiamo syncedLyrics dal primo risultato
                testo = dati[0].get("syncedLyrics", "")

    return pulisci_testo(testo) if testo else None

def gen_config():
    config = {
        "Cartelle": {
            "YouTube": "YT_FOLDER"
        },
        "ALBUM_ORDER": [
            "23 6451",
            "c@ra++ere spec!@le",
            "sFaCioLaTe miXTaPe",
            "CASA GOSPEL"
        ],
        "ALBUM_FINTI": [
            "Beat",
            "Acustiche",
            "Sparse",
            "Freestyle"
        ],
        "IP_per_google_home": "192.168.1.8",
        "PORT": 80
    }

    with open("config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True)

def load_config(MUSIC_FOLDER, YT_FOLDER, DOCKER=False):
    config = {}
    if DOCKER:
        music_folders = {}
        for root, dirs, files in os.walk(MUSIC_FOLDER):
            for d in dirs:
                full_path = os.path.join(root, d)
                music_folders[d] = full_path
        music_folders["YouTube"] = YT_FOLDER
        config = {
            "Cartelle": {name: path if path != "YT_FOLDER" else YT_FOLDER for name, path in music_folders.items()},
            "ALBUM_ORDER": [a.strip() for a in os.getenv("ALBUM_ORDER", "").split(',')],
            "ALBUM_FINTI": [a.strip() for a in os.getenv("ALBUM_FINTI", "").split(',')],
            "IP_per_google_home": os.getenv("IP", ""),
            "PORT": int(os.getenv("PORT", 80))
        }
    else:
        if not os.path.exists('config.yaml'): gen_config()
        with open('config.yaml', 'r', encoding='utf-8') as config_file:
            config = yaml.safe_load(config_file)

    MUSIC_FOLDERS = {name: (path if path != "YT_FOLDER" else YT_FOLDER) for name, path in config.get("Cartelle", {}).items()}
    ALBUM_ORDER = config.get("ALBUM_ORDER", [])
    ALBUM_FINTI = config.get("ALBUM_FINTI", [])
    IP_per_google_home = config.get("IP_per_google_home", "")
    PORT = config.get("PORT", 80)
    return MUSIC_FOLDERS, ALBUM_ORDER, ALBUM_FINTI, IP_per_google_home, PORT

def get_accordi(file_path, DOCKER=False):
    def prendi_accordi(file_path):
        if not os.path.exists("chords.json"):
            with open("chords.json", "w", encoding="utf-8") as f:
                json.dump({}, f)
            return None

        with open("chords.json", "r") as f:
            chords = json.load(f)
        
        chords = chords.get(file_path)
        return chords if chords else None
    def process_chord(chord_key, suffix="major"):
        """
        Cerca l'accordo e lo converte nel tuo formato.
        chord_key: es. 'C', 'Bb', 'G#'
        suffix: es. 'major', 'minor', '7', 'm7'
        """
        def extract_barres(fingers_positions):
            """
            Analizza le posizioni delle dita per identificare un barrè.
            Se lo stesso dito (es. il '1') è usato su più corde allo stesso tasto,
            crea l'oggetto barre.
            """
            barres = []
            # Contiamo quante volte appare ogni dito (escludendo lo 0 o x)
            finger_counts = {}
            for pos in fingers_positions:
                fret, finger = pos[1], pos[2] # tasto, dito
                if finger != 0 and fret != "x":
                    if finger not in finger_counts:
                        finger_counts[finger] = []
                    finger_counts[finger].append(pos)

            for finger, positions in finger_counts.items():
                if len(positions) > 1:
                    # Se un dito preme più di una corda allo stesso tasto, è un barrè
                    frets = [p[1] for p in positions]
                    if len(set(frets)) == 1: # Tutte allo stesso tasto
                        strings = [p[0] for p in positions]
                        barres.append({
                            "fromString": max(strings),
                            "toString": min(strings),
                            "fret": frets[0]
                        })
            return barres
        def get_chord_database():
            if os.path.exists("chords_lib.json"):
                with open("chords_lib.json", "r") as f:
                    return json.load(f)
            else:
                response = requests.get(CHORD_DB_URL)
                if response.status_code == 200:
                    with open("chords_lib.json", "w") as f:
                        f.write(response.text)
                    return json.loads(response.text)
                else:
                    raise Exception(f"Failed to fetch chord database: {response.status_code}")

        CHORD_DB_URL = "https://raw.githubusercontent.com/tombatossals/chords-db/master/lib/guitar.json"
        db = get_chord_database()
        
        # Trova la nota base (C, C#, etc.)
        chords_for_note = db.get("chords").get(chord_key)
        if not chords_for_note:
            return f"Nota {chord_key} non trovata."

        # Trova la variante (major, minor, etc.)
        variant = next((item for item in chords_for_note if item["suffix"] == suffix), None)
        if not variant:
            return f"Sufisso {suffix} non trovato per {chord_key}."

        # Prendiamo la prima posizione suggerita (posizione 0)
        pos = variant["positions"][0]
        
        # ChordDB usa: frets (tasti), fingers (dita)
        # strings: 6 5 4 3 2 1
        raw_frets = pos["frets"]
        raw_fingers = pos["fingers"]
        
        fingers_output = []
        temp_positions = [] # Per calcolare i barrè

        for i in range(6):
            string_num = 6 - i
            fret = raw_frets[i] if raw_frets[i] != -1 else "x"
            finger = raw_fingers[i]
            
            fingers_output.append([string_num, fret])
            if finger != 0:
                temp_positions.append((string_num, fret, finger))

        # Generazione JSON finale
        result = {
            "fingers": fingers_output,
            "barres": extract_barres(temp_positions)
        }

        return result
    def generate_chord_svg(chord_data, chord_name="Accordo"):
        # Impostazioni dimensioni
        width = 180
        height = 200
        margin_top = 40
        margin_left = 30
        fret_spacing = 35
        string_spacing = 25
        
        # Colori e stili
        svg_header = f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
        styles = """
        <style>
            .grid { stroke: #bdbdbd; stroke-width: 2; }
            .finger { fill: #bdbdbd; }
            .barre { stroke: #bdbdbd; stroke-width: 8; stroke-linecap: round; }
            .text { font-family: Arial, sans-serif; font-size: 20px; text-anchor: middle; fill: #bdbdbd; }
            .fret-num { font-size: 10px; fill: #666; }
        </style>
        """
        
        content = [svg_header, styles]
        
        # Titolo accordo
        content.append(f'<text x="{width/2}" y="15" class="text" font-weight="bold">{chord_name}</text>')

        # Disegno Griglia (6 corde, 5 tasti)
        for i in range(6): # Corde
            x = margin_left + (i * string_spacing)
            content.append(f'<line x1="{x}" y1="{margin_top}" x2="{x}" y2="{margin_top + (4 * fret_spacing)}" class="grid" />')
        
        for i in range(5): # Tasti
            y = margin_top + (i * fret_spacing)
            content.append(f'<line x1="{margin_left}" y1="{y}" x2="{margin_left + (5 * string_spacing)}" y2="{y}" class="grid" />')

        # Disegno Barrè
        for barre in chord_data.get("barres", []):
            fret_y = margin_top + (barre['fret'] * fret_spacing) - (fret_spacing / 2)
            # Mappatura corde: 6 è a sinistra (margin_left), 1 è a destra
            x_start = margin_left + ((6 - barre['fromString']) * string_spacing)
            x_end = margin_left + ((6 - barre['toString']) * string_spacing)
            content.append(f'<line x1="{x_start}" y1="{fret_y}" x2="{x_end}" y2="{fret_y}" class="barre" />')

        # Disegno Dita
        for string, fret in chord_data.get("fingers", []):
            x = margin_left + ((6 - string) * string_spacing)
            
            if fret == "x":
                content.append(f'<text x="{x}" y="{margin_top - 10}" class="text">×</text>')
            elif fret == 0:
                content.append(f'<circle cx="{x}" cy="{margin_top - 12}" r="5" fill="none" stroke="#bdbdbd" stroke-width="2" />')
            else:
                # Calcolo posizione cerchio al centro del tasto
                y = margin_top + (fret * fret_spacing) - (fret_spacing / 2)
                # Evitiamo di disegnare il cerchio se è coperto da un barrè (opzionale)
                content.append(f'<circle cx="{x}" cy="{y}" r="8" class="finger" />')

        content.append('</svg>')

        return "\n".join(content)

    chords = prendi_accordi(file_path)
    if not chords: return None

    accordi = []
    for chord, suffix in chords.items():
        accordi.append(generate_chord_svg(process_chord(chord, suffix), chord_name=chord+" - "+suffix))
    
    return accordi
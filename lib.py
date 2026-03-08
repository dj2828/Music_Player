import pychromecast, os, yt_dlp, difflib, tempfile, subprocess, hashlib, re
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, USLT
from requests import get
import yaml

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
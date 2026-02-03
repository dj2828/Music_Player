import pychromecast, os, yt_dlp, difflib, tempfile, subprocess, hashlib

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
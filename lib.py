import pychromecast, os, yt_dlp, difflib, subprocess, hashlib, re
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, USLT
import yaml, json
import requests
from ytmusicapi import YTMusic
import syncedlyrics

# Inizializziamo la variabile globale per evitare errori di "NameError"
chromecast = None
IP_GOOGLE = "192.168.1.20"

def init_google_home():
    global chromecast
    try:
        print(f"Connessione a Google Home su {IP_GOOGLE}...")
        
        # ✅ Niente unpacking, restituisce direttamente il Chromecast
        chromecast = pychromecast.get_chromecast_from_host(
            (IP_GOOGLE, 8009, None, None, None)
        )
        
        chromecast.wait()
        print(f"✅ Connesso a: {chromecast.name}")
        return True

    except Exception as e:
        print(f"❌ Errore connessione: {e}")
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
    downloaded_file = {}

    def pp_hook(d):
        if d['status'] == 'finished':
            downloaded_file['path'] = d['info_dict'].get('filepath') or d.get('filename')

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(MUSIC_FOLDER, '%(title)s.%(ext)s'),
        'writethumbnail': True,
        'postprocessor_hooks': [pp_hook],
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            },
            {
                'key': 'FFmpegMetadata',   # <-- scrive artist, album, year, ecc.
                'add_metadata': True,
            },
            {
                'key': 'FFmpegThumbnailsConvertor',
                'format': 'png',
            },
            {
                'key': 'EmbedThumbnail',
            }
        ]
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return os.path.basename(downloaded_file.get('path')) # ritorna il nome del file
    except Exception as e:
        print("Errore durante il download:", e)
        return None

def search_videos(query, max_results=5):
    ytmusic = YTMusic()  # no auth necessaria per la ricerca

    try:
        results = ytmusic.search(query, filter='songs', limit=max_results)

        if not results: # fallback su youtube
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': 'in_playlist',
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                results = ydl.extract_info(f'ytsearch{max_results}:{query}', download=False)
            print(results)
            videos = []
            for entry in results['entries']:
                thumbnails = entry.get('thumbnails', [])
                best_thumb = thumbnails[-1]['url'] if thumbnails else None
                videos.append({
                    'title': entry.get('title'),
                    'url': f"https://youtube.com/watch?v={entry['id']}",
                    'channel': entry['artists'][0]['name'] if entry.get('artists') else None,
                    'duration': entry.get('duration'),
                    'thumbnail': best_thumb,
                })
            return videos
                
        videos = []
        for entry in results:
            thumbnails = entry.get('thumbnails', [])
            best_thumb = thumbnails[-1]['url'] if thumbnails else None

            videos.append({
                'title': entry.get('title'),
                'url': f"https://music.youtube.com/watch?v={entry['videoId']}",
                'channel': entry['artists'][0]['name'] if entry.get('artists') else None,
                'duration': entry.get('duration'),
                'thumbnail': best_thumb,
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
        if file_path.endswith('.flac'):
            audio = FLAC(file_path)
            artist = audio.get("ARTIST", [None])[0]
            title = audio.get("TITLE", [None])[0]

        elif file_path.endswith('.mp3'):
            audio = MP3(file_path, ID3=ID3)
            artist = str(audio.get("TPE1", "")) or None
            title = str(audio.get("TIT2", "")) or None
            
        print(f"Testo non trovato nei metadati, cerco online... '{artist} {title}'")
        testo = syncedlyrics.search(f"{artist} {title}") # prima fetchava solo da lrclib, ora da tipo tutto

    return pulisci_testo(testo) if testo else None

def gen_config():
    config = {
        "Cartelle": {
            "YouTube": "YT_FOLDER"
        },
        "ALBUM_ORDER": [
        ],
        "ALBUM_FINTI": [
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

def get_accordi(file_path):
    def prendi_accordi(file_path):
        if not os.path.exists("chords.json"):
            with open("chords.json", "w", encoding="utf-8") as f:
                json.dump({}, f)
            return None

        with open("chords.json", "r", encoding="utf-8") as f:
            chords = json.load(f)
        
        return chords.get(file_path)

    def process_chord(chord_key, variazzione=0):
        """
        Cerca l'accordo e lo converte nel tuo formato.
        chord_key: es. 'C', 'Bb', 'G#'
        suffix: es. 'major', 'minor', '7', 'm7'
        """
        enharmonic_map = {
            "Db": "C#",
            "D#": "Eb",
            "Gb": "F#",
            "G#": "Ab",
            "A#": "Bb"
        }
        print(f"Elaborazione accordo: {chord_key}")
        if chord_key.endswith("m"):
            chord_key = chord_key[:-1]
            suffix = "minor"
        elif chord_key.endswith("7"):
            chord_key = chord_key[:-1]
            suffix = "7"
        elif chord_key.endswith("m7"):
            chord_key = chord_key[:-1]
            suffix = "m7"
        else:
            suffix = "major"

        # Se la nota è nel dizionario la traduce (es. G# -> Ab), altrimenti la lascia com'è
        chord_key = enharmonic_map.get(chord_key, chord_key)
        chord_key = chord_key.replace("#", "sharp")
        def extract_barres(fingers_positions):
            barres = []
            finger_counts = {}
            for pos in fingers_positions:
                string_num, fret, finger = pos
                if finger != 0 and fret != "x":
                    finger_counts.setdefault(finger, []).append(pos)

            for finger, positions in finger_counts.items():
                if len(positions) > 1:
                    frets = [p[1] for p in positions]
                    if len(set(frets)) == 1:
                        strings = [p[0] for p in positions]
                        barres.append({
                            "fromString": max(strings),
                            "toString": min(strings),
                            "fret": frets[0]
                        })
            return barres

        def get_chord_database():
            if os.path.exists("chords_lib.json"):
                with open("chords_lib.json", "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                CHORD_DB_URL = "https://raw.githubusercontent.com/tombatossals/chords-db/master/lib/guitar.json"
                response = requests.get(CHORD_DB_URL)
                if response.status_code == 200:
                    with open("chords_lib.json", "w", encoding="utf-8") as f:
                        f.write(response.text)
                    return json.loads(response.text)
                else:
                    raise Exception(f"Failed to fetch chord database: {response.status_code}")

        db = get_chord_database()
        
        chords_for_note = db.get("chords", {}).get(chord_key)
        if not chords_for_note:
            return {"error": f"Nota {chord_key} non trovata."}

        variant = next((item for item in chords_for_note if item["suffix"] == suffix), None)
        if not variant:
            return {"error": f"Suffisso {suffix} non trovato per {chord_key}."}

        pos = variant["positions"][variazzione]
        
        raw_frets = pos["frets"]
        raw_fingers = pos["fingers"]
        
        fingers_output = []
        temp_positions = []

        for i in range(6):
            string_num = 6 - i
            fret = raw_frets[i] if raw_frets[i] != -1 else "x"
            finger = raw_fingers[i]
            
            fingers_output.append([string_num, fret])
            # Modificato per non includere le corde non suonate (x) nel calcolo del barrè
            if finger != 0 and fret != "x":
                temp_positions.append((string_num, fret, finger))

        return {
            "fingers": fingers_output,
            "barres": extract_barres(temp_positions),
            "baseFret": pos["baseFret"]
        }

    def generate_chord_svg(chord_data, chord_name="Accordo"):
        width = 180
        height = 200
        margin_top = 40
        margin_left = 35 # Aumentato leggermente per far stare il testo "fr"
        fret_spacing = 35
        string_spacing = 25
        
        valid_frets = [fret for _, fret in chord_data.get("fingers", []) if isinstance(fret, int) and fret > 0]
        min_fret = min(valid_frets) if valid_frets else 1
        start_fret = min_fret if min_fret > 2 else 1
        baseFret = chord_data.get("baseFret", 1)
        if baseFret == 0: baseFret = 1

        
        svg_header = f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
        styles = """
        <style>
            .grid { stroke: #bdbdbd; stroke-width: 2; }
            .finger { fill: #bdbdbd; }
            .barre { stroke: #bdbdbd; stroke-width: 8; stroke-linecap: round; }
            .text { font-family: Arial, sans-serif; font-size: 20px; text-anchor: middle; fill: #bdbdbd; }
            .fret-num { font-size: 12px; fill: #bdbdbd; font-weight: bold; }
        </style>
        """
        
        content = [svg_header, styles]
        
        # 1. Titolo
        content.append(f'<text x="{width/2}" y="15" class="text" font-weight="bold">{chord_name}</text>')

        # 2. Numero del Fret se baseFret > 1
        if baseFret > 1:
            fret_label_y = margin_top + (fret_spacing / 2) + 5
            content.append(f'<text x="{margin_left - 30}" y="{fret_label_y}" class="fret-num">{baseFret}fr</text>')

        # 3. Disegno Corde (Verticali)
        for i in range(6): 
            x = margin_left + (i * string_spacing)
            content.append(f'<line x1="{x}" y1="{margin_top}" x2="{x}" y2="{margin_top + (4 * fret_spacing)}" class="grid" />')
        
        # 4. Disegno Tasti (Orizzontali)
        for i in range(5): 
            y = margin_top + (i * fret_spacing)
            stroke_style = 'style="stroke-width: 4;"' if i == 0 and start_fret == 1 else ''
            content.append(f'<line x1="{margin_left}" y1="{y}" x2="{margin_left + (5 * string_spacing)}" y2="{y}" class="grid" {stroke_style}/>')

        # 5. Disegno Barrè (Prima delle dita, così le dita restano sopra)
        for barre in chord_data.get("barres", []):
            relative_fret = barre['fret'] - start_fret + 1
            if 1 <= relative_fret <= 4:
                fret_y = margin_top + (relative_fret * fret_spacing) - (fret_spacing / 2)
                x_start = margin_left + ((6 - barre['fromString']) * string_spacing)
                x_end = margin_left + ((6 - barre['toString']) * string_spacing)
                content.append(f'<line x1="{x_start}" y1="{fret_y}" x2="{x_end}" y2="{fret_y}" class="barre" />')

        # 6. Disegno Dita
        for string, fret in chord_data.get("fingers", []):
            x = margin_left + ((6 - string) * string_spacing)
            if fret == "x":
                content.append(f'<text x="{x}" y="{margin_top - 10}" class="text">×</text>')
            elif fret == 0:
                content.append(f'<circle cx="{x}" cy="{margin_top - 12}" r="5" fill="none" stroke="#bdbdbd" stroke-width="2" />')
            else:
                relative_fret = fret - start_fret + 1
                if 1 <= relative_fret <= 4:
                    y = margin_top + (relative_fret * fret_spacing) - (fret_spacing / 2)
                    content.append(f'<circle cx="{x}" cy="{y}" r="8" class="finger" />')

        content.append('</svg>')
        return "\n".join(content)

    if file_path.startswith("singolo"):
        chord = file_path[len("singolo"):]
        variazzione = 0
        if not chord.startswith(('A', 'B', 'C', 'D', 'E', 'F', 'G')):
            variazzione = int(chord[:1])
            chord = chord[1:]
        return generate_chord_svg(process_chord(chord, variazzione), chord_name=chord)
    chords = prendi_accordi(file_path)
    if not chords: 
        return None

    accordi_svg = []
    for chord in chords:
        if "capo" in chord:
            accordi_svg.append(chord)
            continue
        variazzione = 0
        if not chord.startswith(('A', 'B', 'C', 'D', 'E', 'F', 'G')):
            variazzione = int(chord[:1])
            chord = chord[1:]
        accordi_svg.append(generate_chord_svg(process_chord(chord, variazzione), chord_name=chord+(f" ({variazzione})" if variazzione > 0 else "")))
    
    return accordi_svg

def get_info(song):
    print(f"Recupero info per: {song}")
    if song.endswith('.flac'):
        audio = FLAC(song)
        # FLAC restituisce sempre liste di stringhe
        title = audio.get('title', [song.split('/')[-1][:-5]])[0]
        artist = audio.get('artist', ['Unknown Artist'])[0]
        album = audio.get('album', ['Unknown Album'])[0]
    elif song.endswith('.mp3'):
        audio = MP3(song)
        # Gli MP3 usano i frame ID3. Usiamo .text[0] per prendere il contenuto pulito
        title = str(audio.get('TIT2', song.split('/')[-1][:-4]))
        artist = str(audio.get('TPE1', 'Unknown Artist'))
        album = str(audio.get('TALB', 'Unknown Album'))
    else:
        return {"error": "Formato non supportato"}

    return {
        "title": title, 
        "artist": artist, 
        "album": album
    }

def salva_accordi(song, chords_new):
    if not os.path.exists("chords.json"):
        with open("chords.json", "w", encoding="utf-8") as f:
            json.dump({}, f)

    with open("chords.json", "r", encoding="utf-8") as f:
        chords = json.load(f)

    print(f"Salvataggio accordi per '{song}': {chords_new}")
    chords[song] = chords_new

    with open("chords.json", "w", encoding="utf-8") as f:
        json.dump(chords, f, indent=4)

def imgBadQuality(folder, img, max_width=100, output_format="webp"):
    from PIL import Image

    name, ext = os.path.splitext(img)
    new_filename = f"{name}_bad.{output_format}"

    if not os.path.exists(os.path.join(folder, new_filename)):

        path = os.path.join(folder, img)
        try:
            image = Image.open(path)
        except:
            return None

        # Converti in RGB se necessario (es. PNG con trasparenza)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        if image.width > max_width:
            ratio = max_width / image.width
            new_size = (max_width, int(image.height * ratio))
            image = image.resize(new_size, Image.LANCZOS)

        image.save(os.path.join(folder, new_filename), quality=60, optimize=True)

    return folder, new_filename

def imgResized(path, max_width=640):
    from PIL import Image

    if os.path.exists(path):
        image = Image.open(path)

        if image.width > max_width:
            ratio = max_width / image.width
            new_size = (max_width, int(image.height * ratio))
            image = image.resize(new_size, Image.LANCZOS)
            image.save(path, optimize=True)
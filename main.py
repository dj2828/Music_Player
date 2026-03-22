from flask import Flask, render_template, send_from_directory, request, redirect, url_for, flash, jsonify
import os, json
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.id3 import ID3, APIC
import lib

app = Flask(__name__)
app.secret_key = "S4Ss0"

def get_music():
    def album(folder, filename):
        folder_path = MUSIC_FOLDERS.get(folder)
        mp3_path = os.path.join(folder_path, filename)
        if mp3_path.endswith('.flac'):
            audio = FLAC(mp3_path)
            album = audio.get("ALBUM")
            album_name = album[0] if album else None
        else:
            audio = MP3(mp3_path, ID3=ID3)
            album = audio.get("TALB")
            album_name = album.text[0] if album else None

        if album_name:
            album_name = album_name.strip().replace('/', '_').replace('\\', '_').replace('?', 'p')
            
        else:
            album_name = None

        return album_name
    songs_by_folder = {}
    for folder_name, folder_path in MUSIC_FOLDERS.items():
        if os.path.exists(folder_path):
            temp_albums = {}
            songs = [f for f in os.listdir(folder_path) if f.lower().endswith(('.mp3', '.flac'))]
            songs = sorted(songs, key=lambda x: x.lower())
            
            for filename in songs:
                nome_album = album(folder_name, filename) # Usa la tua funzione ID3
                if not nome_album:
                    nome_album = "_SCONOSCIUTO_"
                
                if nome_album not in temp_albums:
                    temp_albums[nome_album] = []
                temp_albums[nome_album].append(filename)

            # --- LOGICA DI ORDINAMENTO ---
            # Prendiamo tutti i nomi degli album trovati
            album_trovati = list(temp_albums.keys())
            
            # Funzione di ordinamento: 
            # 1. Se l'album è in ALBUM_ORDER, usa la sua posizione nella lista.
            # 2. Se non c'è, mettilo dopo (indice alto).
            # 3. "_SCONOSCIUTO_" va sempre per ultimo.
            def sort_logic(name):
                if name == "_SCONOSCIUTO_":
                    return 9999
                try:
                    return ALBUM_ORDER.index(name)
                except ValueError:
                    return 8888 + album_trovati.index(name)

            album_ordinati = sorted(album_trovati, key=sort_logic)

            final_structure = {}
            brani_singoli = []

            for nome_alb in album_ordinati:
                tracce = temp_albums[nome_alb]
                # Se è un album reale (>1 traccia) e non è lo sconosciuto
                if nome_alb != "_SCONOSCIUTO_" and len(tracce) > 1:
                    final_structure[nome_alb] = tracce
                else:
                    brani_singoli.extend(tracce)
                    if nome_alb != "_SCONOSCIUTO_":
                        tutti_album_singoli.append(nome_alb)

            if brani_singoli:
                final_structure["Brani Singoli"] = brani_singoli
            
            songs_by_folder[folder_name] = final_structure
        else:
            songs_by_folder[folder_name] = {}
            
    return songs_by_folder

# config
DOCKER = os.getenv("DOCKER")
YT_FOLDER = os.getenv("YT_FOLDER", os.path.join("music"))
MUSIC_FOLDER = os.getenv("MUSIC_FOLDER", '')
COVER_FOLDER = os.getenv("COVER_FOLDER", os.path.join("cover"))

MUSIC_FOLDERS, ALBUM_ORDER, ALBUM_FINTI, IP, PORT = lib.load_config(MUSIC_FOLDER, YT_FOLDER, DOCKER)

# variabili globali
googleHome = False
tutti_album_singoli = [] # per tenere traccia di tutti i brani singoli, così da escluderli dagli album in img album

# creazione cartelle se non esistono
os.makedirs(YT_FOLDER, exist_ok=True)
os.makedirs(os.path.join(COVER_FOLDER, "album"), exist_ok=True)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', songs_by_folder=get_music(), pref=load_pref())

@app.route('/errore', methods=['GET'])
def errore():
    return render_template('404.html', motivo=request.args.get("motivo", "Errore sconosciuto"))

@app.route('/down', methods=['POST'])
def download():
    if lib.down(request.form.get('yt_url'), YT_FOLDER):
        return redirect(url_for('index'))
    else:
        return jsonify({"status": "error"}), 500
    
@app.route('/<folder>/<filename>')
def music(folder, filename):
    if folder_path := MUSIC_FOLDERS.get(folder):
        mp3 = True if request.args.get('mp3') == '1' else False
        print("Richiesta file:", folder, filename,  "da", request.remote_addr)
        # chiedi a gpt pk non lo capisco neanche io cosa fa sto if
        if (not filename.endswith('.mp3') and not (request.remote_addr.startswith('192.168.') or request.remote_addr == '127.0.0.1') and not DOCKER) or mp3:
            filename = lib.get_cached_mp3(os.path.join(folder_path, filename))
            return send_from_directory(os.path.dirname(filename), os.path.basename(filename))
        return send_from_directory(folder_path, filename)
    else:
        return "Cartella non trovata", 404

@app.route('/img/<folder>/<filename>', methods=['GET'])
def img(folder, filename):
    folder_path = MUSIC_FOLDERS.get(folder)
    mp3_path = os.path.join(folder_path, filename)
    if mp3_path.endswith('.flac'):
        audio = FLAC(mp3_path)
        album = audio.get("ALBUM")
        album_name = album[0] if album else None
    else:
        audio = MP3(mp3_path, ID3=ID3)
        album = audio.get("TALB")
        album_name = album.text[0] if album else None

    if not tutti_album_singoli: get_music() # per popolare la lista se vuota di tutti gli album singoli, così da escluderli dagli album in img album
    if album_name and album_name not in ALBUM_FINTI and album_name not in tutti_album_singoli:
        album_name = album_name.strip().replace('/', '_').replace('\\', '_').replace('?', 'p')
        img_path = os.path.join(COVER_FOLDER, "album", f"{album_name}.png")
        nome_img = f'{album_name}.png'
        dir_img = os.path.join(COVER_FOLDER, "album")
    else:
        img_path = os.path.join(COVER_FOLDER, f"{filename}.png")
        nome_img = f'{filename}.png'
        dir_img = os.path.join(COVER_FOLDER)

    if not os.path.exists(img_path):
        if mp3_path.endswith('.flac'):
            if audio.pictures:
                for picture in audio.pictures:
                    # Type 3 is usually the Front Cover
                    if picture.type == 3: 
                        try:
                            with open(img_path, "wb") as out_img:
                                out_img.write(picture.data)
                            print(f"Immagine salvata come {img_path}")
                            break 
                        except IOError as e:
                            print(f"Errore: {e}")
        else:
            for tag in audio.tags.values():
                if isinstance(tag, APIC):
                    try:
                        with open(img_path, "wb") as out_img:
                            out_img.write(tag.data)
                            print(f"Immagine salvata come {img_path}")
                    except:
                        pass
                    break
    else:
        print("Immagine già presente")
    if album_name and album_name not in ALBUM_FINTI and album_name not in tutti_album_singoli:
        return redirect("/img/album/" + album_name)
    else:
        return send_from_directory(dir_img, nome_img)

@app.route('/img/album/<album_name>', methods=['GET'])
def img_album(album_name):
    img_path = os.path.join(COVER_FOLDER, "album", f"{album_name}.png")
    if os.path.exists(img_path):
        return send_from_directory(os.path.join(COVER_FOLDER, "album"), f"{album_name}.png")
    else:
        return "Immagine non trovata", 404

@app.route('/google', methods=['POST'])
def google_home_da_sito():
    url = request.form.get('url')
    print("Richiesta di riproduzione su Google Home ricevuta con url:", url)
    if url == 'play':
        lib.playG('play')
    elif url == 'pause':
        lib.playG('pause')
    elif url == 'init':
        global googleHome
        if not googleHome:
            print("Google Home non attivo, inizializzo...")
            if lib.init_google_home():
                googleHome = True
            else:
                return "Google Home non disponibile", 404
        return "Google Home attivo", 1
    elif url == 'stop':
        lib.playG('stop')
        googleHome = False
    elif url.startswith('vol'):
        lib.volG(url[3:])
    else:
        lib.playG('http://'+IP+url)
    return "OK"

# per il webhook di Dialogflow per Google Home actions (non va più, le hanno tolte)
# va con il bot di telegram (+/-)
# non puoi comandarlo dal sito perchè non ciho sbatta di farlo (basta coppiare google_home_da_sito())
@app.route('/google_home', methods=['POST'])
def google_home_da_google():
    data = request.get_json().get('queryResult').get('parameters').get('canz')
    print(data)
    print("Richiesta di riproduzione su Google Home ricevuta")
    global googleHome
    if not googleHome:
        print("Google Home non attivo, inizializzo...")
        if lib.init_google_home():
            googleHome = True
        else:
            return jsonify({"status": "error"}), 2

    solo_tha = get_music().get('Tha Supreme', [])
    canz = lib.getSimileCanz(data, solo_tha)
    url = f"http://{IP}/Tha Supreme/{canz}"
    print("URL da riprodurre:", url)
    lib.playG(url)
    return jsonify({"status": "success"}), 200

@app.route('/sw')
def sw():
    return send_from_directory('static', 'sw.js')

@app.route('/ping', methods=['GET'])
def ping():
    """Endpoint leggero per verificare se il server è raggiungibile dal client.
    Restituisce JSON semplice e può essere richiamato frequentemente dal client.
    """
    return jsonify({"status": "ok"}), 200

@app.route('/cerca', methods=['GET'])
def cerca():
    query = request.args.get('q', '')
    if not query:
        return jsonify({"error": "Query mancante"}), 400
    results = lib.search_videos(query, max_results=5)
    return jsonify(results), 200

@app.route('/delete/<folder>/<filename>')
def delete_song(folder, filename):
    folder_path = MUSIC_FOLDERS.get(folder)
    if folder_path:
        file_path = os.path.join(folder_path, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            pref = load_pref()
            plays = load_plays()
            if f"{folder}/{filename}" in pref:
                pref.remove(f"{folder}/{filename}")
                with open('pref.json', 'w') as f:
                    json.dump(pref, f, indent=2)
            if f"{folder}/{filename}" in plays:
                del plays[f"{folder}/{filename}"]
                with open('plays.json', 'w') as f:
                    json.dump(plays, f, indent=2)
            return "OK", 200
        else:
            return "ERROR", 500
    else:
        return "ERROR", 500
    return redirect(url_for('index'))

PLAYS_FILE = 'plays.json'
def load_plays():
    if os.path.exists(PLAYS_FILE):
        with open(PLAYS_FILE, 'r') as f:
            return json.load(f)
    else:
        with open("plays.json", "w", encoding="utf-8") as f:
            f.write("{}")
    return {}
@app.route('/increment_plays', methods=['POST'])
def increment_plays():
    song = request.form.get('song')
    plays = load_plays()
    plays[song] = plays.get(song, 0) + 1
    with open(PLAYS_FILE, 'w') as f:
        json.dump(plays, f, indent=2)
    print(f"Incrementato play count per {song}: {plays[song]} plays totali")
    return "OK", 200

@app.route('/info', methods=['GET'])
def get_info():
    song = request.args.get('song')
    plays = load_plays()
    play_count = plays.get(song, 0)
    return jsonify({'plays': play_count})

@app.route('/stats', methods=['GET'])
def get_stats():
    def hours_played(plays):
        remove_song = []
        total_seconds = 0.0

        for song, count in plays.items():
            try:
                folder, filename = song.split('/', 1)
                folder_path = MUSIC_FOLDERS.get(folder)
                mp3_path = os.path.join(folder_path, filename)

                if mp3_path.endswith('.flac'):
                    audio = FLAC(mp3_path)
                    duration = audio.info.length
                else:
                    audio = MP3(mp3_path, ID3=ID3)
                    duration = audio.info.length

                total_seconds += duration * count

            except Exception:
                remove_song.append(song)
                continue

        for song in set(remove_song):
            print("Rimuovo canzone non trovata dalle statistiche:", song)
            plays.pop(song, None)

        with open(PLAYS_FILE, 'w') as f:
            json.dump(plays, f, indent=2)

        # Conversione corretta
        total_seconds = int(total_seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        return f"{hours}h {minutes}m"
    plays = load_plays()
    total_songs = len(plays)
    total_plays = sum(plays.values())
    total_hours = hours_played(plays)
    classifica = sorted(plays.items(), key=lambda x: x[1], reverse=True)[:10]

    return render_template('stats.html', total_songs=total_songs, total_plays=total_plays, total_hours=total_hours, classifica=classifica)

@app.route('/get_lyrics/<folder>/<filename>')
def get_lyrics(folder, filename):
    if folder_path := MUSIC_FOLDERS.get(folder):
        testo = lib.get_testo(os.path.join(folder_path, filename), DOCKER=DOCKER)
        return (testo, 200) if testo else ("Testo non trovato", 404)
    else:
        return "Cartella non trovata", 404

@app.route('/lyrics')
def lyrics():
    return render_template("lyrics.html")

PREF_FILE = 'pref.json'
def load_pref():
    if os.path.exists(PREF_FILE):
        with open(PREF_FILE, 'r') as f:
            return json.load(f)
    else:
        with open("pref.json", "w", encoding="utf-8") as f:
            f.write("[]")
    return []
@app.route('/pref', methods=['GET', 'POST'])
def pref():
    if request.method == 'GET':
        if song := request.args.get('song'):
            pref = load_pref()
            is_pref = song in pref
            return jsonify({'is_pref': is_pref}), 200
        else:
            return "Skibidi", 400
    song = request.form.get('song')
    pref = load_pref()
    if song in pref:
        pref.remove(song)
        status = "removed"
    else:
        pref.append(song)
        status = "added"
    with open('pref.json', 'w') as f:
        json.dump(pref, f, indent=2)
    return jsonify({"status": status}), 200

@app.after_request
def add_header(response):
    if request.path.endswith(('.mp3', '.flac')):
        response.headers['Cache-Control'] = 'public, max-age=3600'
    if request.path.startswith('/img/album/'):
        response.headers['Cache-Control'] = 'public, max-age=86400'
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=PORT)

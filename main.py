from flask import Flask, render_template, send_from_directory, request, redirect, url_for, flash, jsonify
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
import lib


app = Flask(__name__)
app.secret_key = "S4Ss0"

def ip(path_txt):
    if DOCKER:
        return os.getenv("IP", "0.0.0.0")
    else:
        with open(path_txt, 'r', encoding='utf-8') as file:
            for line in file:
                if line.startswith('#'):
                    return line[1:]
def load_music_folders(path_txt):
    global ALBUM_ORDER
    music_folders = {}
    if not DOCKER:
        if os.path.exists(path_txt):
            with open(path_txt, 'r', encoding='utf-8') as file:
                for line in file:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Gestione specifica per l'ordine degli album
                        if key == 'ALBUM_ORDER':
                            ALBUM_ORDER = [a.strip() for a in value.split(',')]
                            continue
                            
                        if value == 'YT_FOLDER':
                            value = YT_FOLDER
                        music_folders[key] = value
    else:
        # Logica Docker esistente
        for root, dirs, files in os.walk(MUSIC_FOLDER):
            for d in dirs:
                full_path = os.path.join(root, d)
                music_folders[d] = full_path
        music_folders["YouTube"] = YT_FOLDER
        ALBUM_ORDER = [a.strip() for a in os.getenv("ALBUM_ORDER", "").split(',')]
    return music_folders
def get_music():
    songs_by_folder = {}
    for folder_name, folder_path in MUSIC_FOLDERS.items():
        if os.path.exists(folder_path):
            temp_albums = {}
            songs = [f for f in os.listdir(folder_path) if f.lower().endswith('.mp3')]
            
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

            if brani_singoli:
                final_structure["Brani Singoli"] = brani_singoli
            
            songs_by_folder[folder_name] = final_structure
        else:
            songs_by_folder[folder_name] = {}
            
    return songs_by_folder
def album(folder, filename):
    folder_path = MUSIC_FOLDERS.get(folder)
    mp3_path = os.path.join(folder_path, filename)
    audio = MP3(mp3_path, ID3=ID3)
    album = audio.get("TALB")

    if album:
        album_name = album.text[0].strip().replace('/', '_').replace('\\', '_').replace('?', 'p')
        
    else:
        album_name = None

    return album_name

DOCKER = os.getenv("DOCKER")
YT_FOLDER = os.getenv("YT_FOLDER", os.path.join("music"))
MUSIC_FOLDER = os.getenv("MUSIC_FOLDER", '')
COVER_FOLDER = os.getenv("COVER_FOLDER", os.path.join("cover"))

os.makedirs(YT_FOLDER, exist_ok=True)
os.makedirs(os.path.join(COVER_FOLDER, "album"), exist_ok=True)
if not os.path.exists('config.txt'): os.system('echo YouTube=YT_FOLDER > config.txt')

ALBUM_ORDER = []
MUSIC_FOLDERS = load_music_folders('config.txt')
IP = ip('config.txt')
googleHome = False


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', songs_by_folder=get_music())

@app.route('/errore', methods=['GET'])
def errore():
    return render_template('404.html', motivo=request.args.get("motivo", "Errore sconosciuto"))

@app.route('/down', methods=['POST'])
def download():
    if not (url := request.form.get('yt_url')):
        flash("Nessun link o titolo inserito.")
        return redirect(url_for('index'))

    # Se non è un link, cerca su YouTube
    if not (url.startswith("http://") or url.startswith("https://")):
        url = f"ytsearch1:{url}"

    if lib.down(url, YT_FOLDER):
        flash("Download completato!")
    else:
        flash(f"Errore")
    return redirect(url_for('index'))

@app.route('/<folder>/<filename>')
def music(folder, filename):
    if folder_path := MUSIC_FOLDERS.get(folder):
        return send_from_directory(folder_path, filename)
    else:
        return "Cartella non trovata", 404

@app.route('/img', methods=['GET'])
def img():
    folder = request.args.get('folder')
    filename = request.args.get('filename')
    folder_path = MUSIC_FOLDERS.get(folder)
    mp3_path = os.path.join(folder_path, filename)
    audio = MP3(mp3_path, ID3=ID3)
    album = audio.get("TALB")

    if album:
        album_name = album.text[0].strip().replace('/', '_').replace('\\', '_').replace('?', 'p')
        img_path = os.path.join(COVER_FOLDER, "album", f"{album_name}.png")
        nome_img = f'{album_name}.png'
        dir_img = os.path.join(COVER_FOLDER, "album")
    else:
        img_path = os.path.join(COVER_FOLDER, f"{filename}.png")
        nome_img = f'{filename}.png'
        dir_img = os.path.join(COVER_FOLDER)

    if not os.path.exists(img_path):
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

    return send_from_directory(dir_img, nome_img)

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

@app.after_request
def add_header(response):
    if request.path.endswith('.mp3'):
        response.headers['Cache-Control'] = 'public, max-age=86400'
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)

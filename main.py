from flask import Flask, render_template, send_from_directory, request, redirect, url_for, flash
import os
import yt_dlp
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC

app = Flask(__name__)
app.secret_key = "supersecret"  # Necessario per flash

MUSIC_FOLDER = os.path.join('music')

MUSIC_FOLDERS = {
    "Tha Supreme": r'X:\cartelllla\canz\fr\thasup',
    "Nintendo": r'X:\cartelllla\vidoooooooooooooooo\canzoni\bg SERIE\Nintendo',
    "YouTube": MUSIC_FOLDER,  # Nuova cartella per i download
}

@app.route('/', methods=['GET'])
def index():
    songs_by_folder = {}
    for folder_name, folder_path in MUSIC_FOLDERS.items():
        if os.path.exists(folder_path):
            songs = [f for f in os.listdir(folder_path) if f.lower().endswith('.mp3')]
            songs_by_folder[folder_name] = songs
        else:
            songs_by_folder[folder_name] = []
    return render_template('index.html', songs_by_folder=songs_by_folder)

@app.route('/', methods=['POST'])
def download():
    url = request.form.get('yt_url')
    if not url:
        flash("Nessun link o titolo inserito.")
        return redirect(url_for('index'))

    # Se non è un link, cerca su YouTube
    if not (url.startswith("http://") or url.startswith("https://")):
        url = f"ytsearch1:{url}"

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
            }
        ],
        'prefer_ffmpeg': True,
        'quiet': True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        flash("Download completato!")
        print(f"Immagine croppata salvata in: {output_path}")
    except Exception as e:
        flash(f"Errore: {e}")
    return redirect(url_for('index'))

@app.route('/<folder>/<filename>')
def music(folder, filename):
    folder_path = MUSIC_FOLDERS.get(folder)
    if folder_path:
        return send_from_directory(folder_path, filename)
    else:
        return "Cartella non trovata", 404

@app.route('/<folder>/<filename>.png')
def img(folder, filename):
    folder_path = MUSIC_FOLDERS.get(folder)
    mp3_path = os.path.join(folder_path, filename)
    audio = MP3(mp3_path, ID3=ID3)
    album = audio.get("TALB")

    if album:
        album_name = album.text[0].strip().replace('/', '_').replace('\\', '_').replace('?', 'p')
        img_path = os.path.join("cover", "album", f"{album_name}.png")
        nome_img = f'{album_name}.png'
        dir_img = os.path.join("cover", "album")
    else:
        img_path = os.path.join("cover", f"{filename}.png")
        nome_img = f'{filename}.png'
        dir_img = "cover"

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)
import pychromecast, os, yt_dlp

def playG(url):
    print("Riproduzione su Google Home:", url)
    mc = chromecast.media_controller
    mc.play_media(url, "audio/mp3")
    mc.block_until_active()
    mc.play()
    print('Ok')
    return

def init_google_home():
    try:
        # Cerca tutti i dispositivi Chromecast nella rete
        devices, browser = pychromecast.get_chromecasts()
        # Mostra tutti i nomi trovati per aiutarti a identificare il tuo Google Home
        for cc in devices:
            print(cc.name)
        # Scegli il dispositivo con nome esatto o parziale
        device_name = "Studio_mini"  # oppure il nome esatto che hai visto stampato sopra
        # Cerca il dispositivo corrispondente
        global chromecast
        chromecast = next(cc for cc in devices if device_name.lower() in cc.name.lower())
        # Connessione al dispositivo
        chromecast.wait()
        return True
    except:
        print("Nessun dispositivo Google Home trovato. Assicurati che sia acceso e connesso alla rete.")
        return False

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
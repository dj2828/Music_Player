import pychromecast

def play(url):
    print("Riproduzione su Google Home:", url)
    mc = chromecast.media_controller
    mc.play_media(url, "audio/mp3")
    mc.block_until_active()
    mc.play()
    return

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
except:
    print("Nessun dispositivo Google Home trovato. Assicurati che sia acceso e connesso alla rete.")
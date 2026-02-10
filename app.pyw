from main import app
import webview
import threading
import pystray
from PIL import Image
import os
from flask import render_template

@app.route('/mini')
def mini():
    return render_template('mini.html')

class ApiBridge:
    def __init__(self):
        self.data_storage = {}

    def prevSong(self):
        main_window.evaluate_js("prevSong()")
    def togglePlay(self):
        main_window.evaluate_js("togglePlay()")
    def nextSong(self):
        main_window.evaluate_js("nextSong()")
    
    def setPlay(self, value):
        mini_window.evaluate_js(f"play('{value}')")
    def setSong(self, url, titolo, cartella):
        self.data_storage["url"] = url
        self.data_storage["titolo"] = titolo
        self.data_storage["cartella"] = cartella
        mini_window.evaluate_js(f"carica('{api.data_storage.get("url")}', '{api.data_storage.get("titolo")}', '{api.data_storage.get("cartella")}')")

main_window = None
mini_window = None
api = ApiBridge()
def crea_window():
    global main_window, mini_window
    main_window = webview.create_window("Music_player", "http://127.0.0.1:5000", width=1100, height=700, js_api=api)
    main_window.events.minimized += on_window_minimized
    main_window.events.closing += on_window_closed

    screens = webview.screens
    x = screens[0].width - 365
    y = screens[0].height - 170
    mini_window = webview.create_window("Mini_player", "http://127.0.0.1:5000/mini", width=355, height=170, frameless=True, js_api=api, hidden=True, x=x, y=y)
    webview.start()

def run_flask():
    # Avvia Flask in modalità silenziosa (senza il debugger che creerebbe conflitti)
    app.run(host='127.0.0.1', port=5000, debug=False)

def on_window_minimized():
    # Invece di chiudere, nascondiamo la finestra
    main_window.hide()
    mini_window.evaluate_js(f"carica('{api.data_storage.get("url")}', '{api.data_storage.get("titolo")}', '{api.data_storage.get("cartella")}')")
    mini_window.show()
    # Ritorna False per impedire la distruzione effettiva della finestra
    return False

def on_window_closed():
    main_window.hide()
    return False

# --- GESTIONE SYSTEM TRAY (ICONA) ---
def on_quit(icon, item):
    icon.stop()
    # Usiamo os._exit per chiudere istantaneamente tutti i thread (incluso il bot)
    os._exit(0)
def open(icon, item):
    if main_window:
        mini_window.hide()
        main_window.show()
        main_window.restore()

def setup_tray():
    image = Image.open("static/IO.png")
    menu = pystray.Menu(pystray.MenuItem('Apri', open, default=True),
                        pystray.MenuItem('Esci', on_quit))
    icon = pystray.Icon("Music_player", image, "Music_player", menu)
    icon.run()

flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()
tray_thread = threading.Thread(target=setup_tray, daemon=True)
tray_thread.start()
crea_window()
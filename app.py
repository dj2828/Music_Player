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



main_window = None
mini_window = None
def crea_window():
    global main_window, mini_window
    main_window = webview.create_window("Music_player", "http://127.0.0.1:5000", width=500, height=700)
    main_window.events.minimized += on_window_minimized

    mini_window = webview.create_window("Mini_player", "http://127.0.0.1:5000/mini", width=365, height=170, frameless=True)
    webview.start()

def run_flask():
    # Avvia Flask in modalità silenziosa (senza il debugger che creerebbe conflitti)
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

def on_window_minimized():
    # Invece di chiudere, nascondiamo la finestra
    main_window.hide()
    # Ritorna False per impedire la distruzione effettiva della finestra
    return False

# --- GESTIONE SYSTEM TRAY (ICONA) ---
def on_quit(icon, item):
    icon.stop()
    # Usiamo os._exit per chiudere istantaneamente tutti i thread (incluso il bot)
    os._exit(0)
def open(icon, item):
    if main_window:
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
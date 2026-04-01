from waitress import serve
from main import app

IP = os.getenv("IP", "0.0.0.0")
PORT = int(os.getenv("PORT", 80))

serve(app, host=IP, port=PORT)

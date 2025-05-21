from flask import Flask
import threading
import time
import requests

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def self_ping(url="https://your-railway-url.up.railway.app"):
    while True:
        try:
            requests.get(url)
        except:
            pass
        time.sleep(600)  # setiap 10 menit

def keep_alive():
    threading.Thread(target=run).start()
    threading.Thread(target=self_ping).start()

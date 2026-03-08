import os
from flask import Flask, Response
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder=".", static_url_path="")

@app.route("/config.js")
def config():
    token = os.getenv("JAWG_TOKEN", "")
    return Response(
        f'window.JAWG_TOKEN = "{token}";',
        mimetype="application/javascript"
    )

@app.route("/")
def index():
    return app.send_static_file("index.html")

if __name__ == "__main__":
    app.run(debug=True)
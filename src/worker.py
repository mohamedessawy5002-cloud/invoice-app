from flask import Flask
from workers import wsgi

app = Flask(__name__)

@app.get("/")
def index():
    return {"message": "Cloudflare test OK"}

Default = wsgi.entrypoint(app)

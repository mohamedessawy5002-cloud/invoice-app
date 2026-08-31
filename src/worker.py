from workers import wsgi
from main import app

Default = wsgi.entrypoint(app)

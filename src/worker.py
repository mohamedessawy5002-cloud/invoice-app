from workers import wsgi
import sys

sys.path.append(".")

from main import app

Default = wsgi.entrypoint(app)

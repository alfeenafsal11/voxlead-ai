import os
import sys

# Ensure backend package is in python search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.main import app

# Vercel Serverless Function entry point
# Exports 'app' for ASGI/WSGI invocation

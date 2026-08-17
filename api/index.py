import sys
import os

# Add server directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
server_dir = os.path.join(os.path.dirname(current_dir), "server")
if server_dir not in sys.path:
    sys.path.insert(0, server_dir)

from server import app

# Vercel ASGI entry point
# 'app' is the FastAPI instance

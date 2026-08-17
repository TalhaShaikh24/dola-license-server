import sys
import os
import uvicorn

# Ensure the server directory is in sys.path
server_dir = os.path.dirname(os.path.abspath(__file__))
if server_dir not in sys.path:
    sys.path.insert(0, server_dir)

def run():
    print("=" * 60)
    print("🚀 Starting Dola AI SaaS License Server & Admin Portal")
    print("📍 Super Admin Dashboard: http://localhost:8000/admin")
    print("🔑 Default Admin: username 'admin' | password 'admin123'")
    print("⚡ API Endpoint: http://localhost:8000/api")
    print("=" * 60)
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    run()

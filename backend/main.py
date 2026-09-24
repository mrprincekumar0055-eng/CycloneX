import sys
import os

# Ensure backend and project root are in sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_dir)

for _p in [_project_root, _current_dir]:
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from backend.app.main import app
except ImportError:
    from app.main import app

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)

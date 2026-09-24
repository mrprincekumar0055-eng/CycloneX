import sys
import os
import types
import traceback
import logging

logger = logging.getLogger("CycloneX.Entrypoint")

# Ensure backend and project root are in sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_dir)

for _p in [_current_dir, _project_root]:
    if _p and os.path.exists(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

# Ensure "backend" package is resolvable when backend is the service root
if "backend" not in sys.modules:
    backend_pkg = types.ModuleType("backend")
    backend_pkg.__path__ = [_current_dir]
    backend_pkg.__file__ = os.path.join(_current_dir, "__init__.py")
    sys.modules["backend"] = backend_pkg

# Load FastAPI application safely with transparent error reporting if import fails
try:
    from backend.app.main import app as _actual_app
    app = _actual_app
except Exception as _startup_exc:
    logger.exception("FATAL: Failed to import backend.app.main application")
    _startup_trace = traceback.format_exc()
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    app = FastAPI(title="CycloneX Startup Error Handler")

    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
    async def _catch_startup_error(full_path: str):
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": "STARTUP_IMPORT_FAILED",
                "message": str(_startup_exc),
                "traceback": _startup_trace
            }
        )

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)

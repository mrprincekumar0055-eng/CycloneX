import sys
import os
import traceback

_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_dir)
_backend_dir = os.path.join(_project_root, "backend")

for _p in [_project_root, _backend_dir]:
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from backend.app.main import app as _actual_app
    app = _actual_app
except Exception as _startup_exc:
    _startup_trace = traceback.format_exc()
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    app = FastAPI(title="CycloneX API Startup Error Handler")

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

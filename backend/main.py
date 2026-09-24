import sys
import os
import types
import traceback
import json
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Top-level handler definition guaranteed to satisfy Vercel AST builder
app = FastAPI(title="CycloneX Production API")

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

class SafeASGIWrapper:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        # Handle lifespan startup and shutdown cleanly if driven by ASGI adapter
        if scope.get("type") == "lifespan":
            while True:
                msg = await receive()
                if msg.get("type") == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif msg.get("type") == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    return
                else:
                    return

        try:
            await self.inner(scope, receive, send)
        except Exception as exc:
            tb = traceback.format_exc()
            body = json.dumps({
                "status": "error",
                "code": "ASGI_EXCEPTION",
                "message": str(exc),
                "traceback": tb.splitlines()
            }).encode("utf-8")
            headers = [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
            ]
            await send({"type": "http.response.start", "status": 500, "headers": headers})
            await send({"type": "http.response.body", "body": body, "more_body": False})

# Dynamically import real application and transparently report any cold-start exceptions
try:
    from backend.app.main import app as _real_app
    app = SafeASGIWrapper(_real_app)
except Exception as _startup_exc:
    _startup_trace = traceback.format_exc()
    import logging
    logging.exception(f"Startup import error: {_startup_exc}")

    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
    async def _catch_startup_error(full_path: str):
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": "STARTUP_IMPORT_FAILED",
                "message": str(_startup_exc),
                "traceback": _startup_trace.splitlines()
            }
        )

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)

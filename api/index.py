import os
import sys

# Add api/_lib so that 'backend' package inside _lib is resolved
api_dir = os.path.dirname(os.path.abspath(__file__))
lib_dir = os.path.join(api_dir, "_lib")
if lib_dir not in sys.path:
    sys.path.insert(0, lib_dir)

root_dir = os.path.abspath(os.path.join(api_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    from backend.app.main import app
except Exception as e:
    import traceback
    err_trace = traceback.format_exc()
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    app = FastAPI(title="VoxLead Diagnostic Fallback")

    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
    async def fallback_handler(full_path: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "traceback": err_trace,
                "sys_path": sys.path,
                "current_dir": os.getcwd()
            }
        )

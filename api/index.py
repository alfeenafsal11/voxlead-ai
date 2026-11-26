import os
import sys

# Ensure api directory and root are on sys.path
api_dir = os.path.dirname(os.path.abspath(__file__))
if api_dir not in sys.path:
    sys.path.insert(0, api_dir)

root_dir = os.path.abspath(os.path.join(api_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    from backend.app.main import app
except Exception as e:
    import traceback
    err_tb = traceback.format_exc()
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    app = FastAPI(title="VoxLead AI Fallback")

    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
    async def catch_all(full_path: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "traceback": err_tb,
                "sys_path": sys.path,
                "current_dir": os.getcwd(),
                "dir_contents": os.listdir(".") if os.path.exists(".") else [],
                "api_contents": os.listdir(api_dir) if os.path.exists(api_dir) else []
            }
        )

import os
import sys
import traceback

# Ensure root directory is in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    from backend.app.main import app
except Exception as e:
    err_tb = traceback.format_exc()
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    app = FastAPI(title="VoxLead AI Error Fallback")

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    async def fallback_handler(path: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "traceback": err_tb,
                "sys_path": sys.path,
                "current_dir": os.getcwd(),
                "dir_contents": os.listdir(".") if os.path.exists(".") else []
            }
        )

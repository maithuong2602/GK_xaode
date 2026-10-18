"""
Main FastAPI server application.
Serves both the REST API and the frontend Single Page Application.
"""
import os
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.api import router as api_router

app = FastAPI(
    title="Phần Mềm Xáo Đề Thi Bảo Toàn Định Dạng Gốc",
    description="Ứng dụng chuyên nghiệp dành cho giáo viên: Xáo đề Word/PDF bảo toàn 100% định dạng OOXML",
    version="1.0.0",
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API router
app.include_router(api_router)

# Ensure directories exist
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Mount static folder
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serves the main application SPA HTML."""
    index_path = os.path.join("templates", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>Đang khởi tạo ứng dụng...</h1>")


if __name__ == "__main__":
    print("[SERVER] Dang khoi dong may chu Xao De Thi tai http://localhost:8000 ...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import yt_dlp
import uuid
import os

app = FastAPI(title="Viral Audio Downloader API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TMP_DIR = "/tmp/audiodrop"
os.makedirs(TMP_DIR, exist_ok=True)

@app.get("/")
def home():
    return {"status":"AudioDrop Backend Live", "endpoints":["/api/extract?url=", "/api/download?url=", "/api/search?q="]}

@app.get("/api/extract")
def extract(url: str = Query(..., description="YouTube Shorts / Reels / YouTube URL")):
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get('title'),
                "thumbnail": info.get('thumbnail'),
                "duration": info.get('duration'),
                "uploader": info.get('uploader'),
                "view_count": info.get('view_count'),
                "audio_url": info.get('url') if 'url' in info else None,
                "id": info.get('id')
            }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/download")
def download(url: str = Query(..., description="YouTube Shorts URL")):
    try:
        uid = str(uuid.uuid4())[:8]
        out_template = os.path.join(TMP_DIR, f"{uid}.%(ext)s")
        final_mp3 = os.path.join(TMP_DIR, f"{uid}.mp3")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': out_template,
            'noplaylist': True,
            'quiet': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title','viral-audio').replace('/','-')[:50]
        
        # Find the mp3
        if os.path.exists(final_mp3):
            return FileResponse(
                final_mp3, 
                media_type="audio/mpeg",
                filename=f"{title}.mp3",
                headers={"Content-Disposition": f"attachment; filename={title}.mp3"}
            )
        else:
            # fallback try m4a
            for f in os.listdir(TMP_DIR):
                if uid in f:
                    return FileResponse(os.path.join(TMP_DIR,f), filename=f"{title}.mp3")
            return JSONResponse(status_code=500, content={"error":"File not found after conversion, install ffmpeg"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/search")
def search(q: str = Query(..., description="Search term like 'Aravindh trending'")):
    # Search YouTube for shorts
    try:
        ydl_opts = {'quiet':True, 'extract_flat':True, 'default_search':'ytsearch5'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(f"ytsearch5:{q} shorts", download=False)
            entries = result.get('entries',[])
            return [{"title": e.get('title'), "url": f"https://www.youtube.com/watch?v={e.get('id')}", "thumbnail": f"https://img.youtube.com/vi/{e.get('id')}/mqdefault.jpg", "id": e.get('id')} for e in entries]
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

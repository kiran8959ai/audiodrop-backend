from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import os
import uuid
import tempfile
import requests
from urllib.parse import urlparse, parse_qs

app = FastAPI(title="AudioDrop Backend - Bot Fix")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# FIX for YouTube bot detection on Render/AWS IPs
YTDLP_OPTS_BASE = {
    'quiet': True,
    'no_warnings': True,
    # Use android client to bypass bot check - most important fix
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'web'],
            'player_skip': ['webpage', 'configs'],
        }
    },
    'format': 'bestaudio/best',
    # Add user-agent to look like real browser
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
}

@app.get("/")
def root():
    return {"status": "AudioDrop Backend Live - Bot Fix v2", "endpoints": ["/api/extract?url=", "/api/download?url=", "/api/search?q="]}

@app.get("/api/extract")
def extract(url: str = Query(...)):
    try:
        # Try with bot-fix options
        ydl_opts = {**YTDLP_OPTS_BASE, 'skip_download': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
        return {
            "title": info.get("title", "Viral Audio"),
            "thumbnail": info.get("thumbnail", f"https://img.youtube.com/vi/{info.get('id','')}/mqdefault.jpg"),
            "duration": info.get("duration", 0),
            "uploader": info.get("uploader", "Unknown"),
            "id": info.get("id", ""),
        }
    except Exception as e:
        err = str(e)
        # If youtube bot error, try fallback methods
        if "Sign in to confirm" in err or "bot" in err.lower():
            # Fallback 1: Try Piped API (no bot check)
            try:
                video_id = extract_youtube_id(url)
                if video_id:
                    piped = requests.get(f"https://pipedapi.kavin.rocks/streams/{video_id}", timeout=10).json()
                    return {
                        "title": piped.get("title", "Viral Audio"),
                        "thumbnail": piped.get("thumbnailUrl", ""),
                        "duration": piped.get("duration", 0),
                        "uploader": piped.get("uploader", "Unknown"),
                        "id": video_id,
                        "fallback": "piped"
                    }
            except:
                pass
            
            raise HTTPException(status_code=429, detail={
                "error": "YouTube bot check on Render IP. Try these fixes:",
                "fixes": [
                    "1. Use Instagram Reels link - works 100% on Render",
                    "2. Try TikTok link - works 100%",
                    "3. Use YouTube link with yout-ube.com trick (see below)",
                    "4. Deploy on Railway.app instead of Render (less blocked)",
                ],
                "original_error": err,
                "workaround_url": f"https://www.yout-ube.com/watch?v={extract_youtube_id(url) or ''}"
            })
        raise HTTPException(status_code=500, detail=err)

def extract_youtube_id(url):
    try:
        parsed = urlparse(url)
        if "youtu.be" in parsed.netloc:
            return parsed.path[1:].split("?")[0]
        if "youtube.com" in parsed.netloc:
            qs = parse_qs(parsed.query)
            if "v" in qs:
                return qs["v"][0]
            if "/shorts/" in parsed.path:
                return parsed.path.split("/shorts/")[1].split("/")[0]
    except:
        pass
    return None

@app.get("/api/download")
def download(url: str = Query(...)):
    try:
        tmpdir = tempfile.mkdtemp()
        outtmpl = os.path.join(tmpdir, "%(title)s.%(ext)s")
        
        ydl_opts = {
            **YTDLP_OPTS_BASE,
            'outtmpl': outtmpl,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # Find mp3 file
            for f in os.listdir(tmpdir):
                if f.endswith(".mp3"):
                    filepath = os.path.join(tmpdir, f)
                    return FileResponse(filepath, media_type="audio/mpeg", filename=f"{info.get('id','audio')}.mp3")
        
        raise Exception("MP3 not created")
        
    except Exception as e:
        err = str(e)
        if "Sign in to confirm" in err or "bot" in err.lower():
            # Fallback: Redirect to Cobalt API
            try:
                cobalt_res = requests.post(
                    "https://api.cobalt.tools/api/json",
                    json={"url": url, "aFormat": "mp3", "isAudioOnly": True},
                    headers={"Accept": "application/json", "Content-Type": "application/json"},
                    timeout=15
                ).json()
                if cobalt_res.get("url"):
                    return JSONResponse({"fallback_url": cobalt_res["url"], "message": "Use this direct MP3 link", "mp3_url": cobalt_res["url"]})
            except:
                pass
            raise HTTPException(status_code=429, detail=f"YouTube blocked Render IP. Try Instagram/TikTok link instead. Original: {err}")
        raise HTTPException(status_code=500, detail=err)

@app.get("/api/search")
def search(q: str = Query(...)):
    try:
        # Use yt-dlp search with bot-fix
        ydl_opts = {**YTDLP_OPTS_BASE, 'skip_download': True, 'extract_flat': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(f"ytsearch5:{q}", download=False)
            entries = result.get("entries", [])[:5]
            return {"results": [{"id": e.get("id"), "title": e.get("title"), "thumbnail": f"https://img.youtube.com/vi/{e.get('id')}/mqdefault.jpg", "url": f"https://www.youtube.com/watch?v={e.get('id')}"} for e in entries]}
    except Exception as e:
        # Fallback to Piped search
        try:
            r = requests.get(f"https://pipedapi.kavin.rocks/search?q={q}&filter=music", timeout=10).json()
            items = r.get("items", [])[:5]
            return {"results": [{"id": item.get("url","").split("v=")[-1], "title": item.get("title"), "thumbnail": item.get("thumbnail"), "url": f"https://youtube.com{item.get('url','')}"} for item in items], "fallback": "piped"}
        except:
            raise HTTPException(status_code=500, detail=str(e))

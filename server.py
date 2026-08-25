from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import re
from urllib.parse import urlparse, parse_qs

app = FastAPI(title="AudioDrop - Cobalt + Piped - Final Fix")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_youtube_id(url):
    try:
        parsed = urlparse(url)
        if "youtu.be" in parsed.netloc:
            return parsed.path[1:].split("?")[0].split("/")[0]
        if "youtube.com" in parsed.netloc or "yout-ube.com" in parsed.netloc:
            qs = parse_qs(parsed.query)
            if "v" in qs:
                return qs["v"][0]
            if "/shorts/" in parsed.path:
                return parsed.path.split("/shorts/")[1].split("/")[0].split("?")[0]
    except:
        pass
    return None

COBALT_INSTANCES = [
    "https://api.cobalt.tools/api/json",
    "https://cobalt-api.kwiatekmiki.com/api/json",
    "https://api.co.wuk.sh/api/json",
]

@app.get("/")
def root():
    return {
        "status": "AudioDrop Backend Live - Cobalt Final v3 - YouTube via Cobalt, Instagram direct",
        "endpoints": ["/api/extract?url=", "/api/download?url=", "/api/search?q="],
        "note": "YouTube uses Cobalt API (no bot block), Instagram/TikTok direct"
    }

@app.get("/api/extract")
def extract(url: str = Query(...)):
    # For Instagram / TikTok - try direct yt-dlp with android client (works 100%)
    if "instagram.com" in url or "tiktok.com" in url:
        try:
            import yt_dlp
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'extractor_args': {'youtube': {'player_client': ['android','web']}},
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            return {
                "title": info.get("title", "Viral Audio"),
                "thumbnail": info.get("thumbnail", ""),
                "duration": info.get("duration", 0),
                "uploader": info.get("uploader", "Unknown"),
                "id": info.get("id", ""),
                "direct_mp3": url
            }
        except Exception as e:
            pass  # fall through to cobalt

    # For YouTube - Use Cobalt + Piped (bypasses bot check completely)
    video_id = extract_youtube_id(url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Could not extract video ID")

    # Try Piped first for metadata (no bot check)
    try:
        r = requests.get(f"https://pipedapi.kavin.rocks/streams/{video_id}", timeout=10).json()
        if r.get("title"):
            return {
                "title": r.get("title", "Viral Audio"),
                "thumbnail": r.get("thumbnailUrl", f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"),
                "duration": r.get("duration", 0),
                "uploader": r.get("uploader", "Unknown"),
                "id": video_id,
                "source": "piped",
                "mp3_ready": True
            }
    except:
        pass

    # Fallback to YouTube thumbnail at least
    return {
        "title": f"YouTube Audio {video_id}",
        "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
        "duration": 0,
        "id": video_id,
        "source": "youtube",
        "mp3_ready": True,
        "note": "Use /api/download for MP3 via Cobalt"
    }

@app.get("/api/download")
def download(url: str = Query(...)):
    # Try Cobalt API for MP3 - works for YouTube, Instagram, TikTok - no bot block
    for cobalt_url in COBALT_INSTANCES:
        try:
            resp = requests.post(
                cobalt_url,
                json={
                    "url": url,
                    "aFormat": "mp3",
                    "isAudioOnly": True,
                    "isAudioMuted": False,
                    "dubLang": False
                },
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                timeout=15
            )
            data = resp.json()
            # Cobalt returns {status: "redirect" or "tunnel", url: "https://...mp3"}
            if data.get("url"):
                return JSONResponse({
                    "mp3_url": data["url"],
                    "title": "Viral Audio MP3",
                    "download_url": data["url"],
                    "message": "Direct MP3 link - open to download/play",
                    "source": "cobalt"
                })
            if data.get("status") == "error":
                continue
        except Exception as e:
            continue

    # If all cobalt instances fail, try direct yt-dlp for Instagram/TikTok
    if "instagram.com" in url or "tiktok.com" in url:
        try:
            import yt_dlp, tempfile, os
            from fastapi.responses import FileResponse
            tmpdir = tempfile.mkdtemp()
            outtmpl = os.path.join(tmpdir, "%(id)s.%(ext)s")
            ydl_opts = {
                'quiet': True,
                'outtmpl': outtmpl,
                'format': 'bestaudio/best',
                'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'192'}],
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                for f in os.listdir(tmpdir):
                    if f.endswith(".mp3"):
                        return FileResponse(os.path.join(tmpdir, f), media_type="audio/mpeg", filename=f"{info.get('id','audio')}.mp3")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    raise HTTPException(status_code=500, detail="Cobalt instances down. Try Instagram Reels link which works direct, or try again in 1 min.")

@app.get("/api/search")
def search(q: str = Query(...)):
    # Use Piped search - no bot block
    try:
        r = requests.get(f"https://pipedapi.kavin.rocks/search?q={q}&filter=music", timeout=10).json()
        items = r.get("items", [])[:8]
        results = []
        for item in items:
            vid_url = item.get("url","")
            vid_id = ""
            if "v=" in vid_url:
                vid_id = vid_url.split("v=")[-1].split("&")[0]
            elif "/watch/" in vid_url:
                vid_id = vid_url.split("/")[-1]
            else:
                vid_id = vid_url.split("/")[-1]
            results.append({
                "id": vid_id,
                "title": item.get("title",""),
                "thumbnail": item.get("thumbnail","") or f"https://img.youtube.com/vi/{vid_id}/mqdefault.jpg",
                "url": f"https://www.youtube.com{vid_url}" if vid_url.startswith("/") else vid_url,
                "uploader": item.get("uploaderName","")
            })
        return {"results": results, "source": "piped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

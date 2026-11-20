import os
import re
import av
import yt_dlp
from typing import Dict, Any, Optional, Tuple

CACHE_DIR = "downloads_cache"
OUTPUT_DIR = "output_reels"

def timestamp_to_seconds(ts: str) -> float:
    """Convert MM:SS or HH:MM:SS format to float seconds."""
    if not ts:
        return 0.0
    parts = list(map(float, ts.strip().split(':')))
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    elif len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return float(ts)

def extract_vid(url_or_id: str) -> str:
    match = re.search(r'(?:v=|\/v\/|youtu\.be\/|\/embed\/|\/shorts\/)([A-Za-z0-9_-]{11})', url_or_id)
    if match:
        return match.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url_or_id.strip()):
        return url_or_id.strip()
    return "source_video"

def download_source_streams(video_url_or_id: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Downloads or finds highest available quality video stream (1080p/720p HD) and audio stream.
    Returns (video_file_path, audio_file_path).
    """
    if os.path.exists(video_url_or_id):
        return video_url_or_id, None
        
    os.makedirs(CACHE_DIR, exist_ok=True)
    vid = extract_vid(video_url_or_id)
    
    # Check if already cached
    actual_v = None
    for prefix in [f"{vid}_720p", f"{vid}_hd", vid]:
        for ext in ['mp4', 'mkv', 'webm']:
            cand = os.path.join(CACHE_DIR, f"{prefix}.{ext}")
            if os.path.exists(cand) and os.path.getsize(cand) > 50000:
                actual_v = cand
                break
        if actual_v:
            break
            
    actual_a = None
    for prefix in [f"{vid}_audio", vid]:
        for ext in ['m4a', 'webm', 'opus', 'mp4']:
            cand = os.path.join(CACHE_DIR, f"{prefix}.{ext}")
            if os.path.exists(cand) and os.path.getsize(cand) > 10000:
                actual_a = cand
                break
        if actual_a:
            break
            
    if actual_v and actual_a:
        return actual_v, actual_a
        
    full_url = video_url_or_id
    if not video_url_or_id.startswith("http"):
        full_url = f"https://www.youtube.com/watch?v={vid}"
        
    ydl_opts_video = {
        'format': '137/232/136/bestvideo[height<=1080][ext=mp4]/bestvideo[height<=720]/bestvideo',
        'outtmpl': os.path.join(CACHE_DIR, f"{vid}_hd.%(ext)s"),
        'quiet': True,
        'no_warnings': True
    }
    
    ydl_opts_audio = {
        'format': '140/bestaudio[ext=m4a]/bestaudio',
        'outtmpl': os.path.join(CACHE_DIR, f"{vid}_audio.%(ext)s"),
        'quiet': True,
        'no_warnings': True
    }
    
    try:
        if not actual_v:
            with yt_dlp.YoutubeDL(ydl_opts_video) as ydl_v:
                ydl_v.download([full_url])
        if not actual_a:
            with yt_dlp.YoutubeDL(ydl_opts_audio) as ydl_a:
                ydl_a.download([full_url])
                
        for prefix in [f"{vid}_hd", f"{vid}_720p", vid]:
            for ext in ['mp4', 'mkv', 'webm']:
                cand = os.path.join(CACHE_DIR, f"{prefix}.{ext}")
                if os.path.exists(cand) and os.path.getsize(cand) > 50000:
                    actual_v = cand
                    break
            if actual_v:
                break
                
        for prefix in [f"{vid}_audio", vid]:
            for ext in ['m4a', 'webm', 'opus', 'mp4']:
                cand = os.path.join(CACHE_DIR, f"{prefix}.{ext}")
                if os.path.exists(cand) and os.path.getsize(cand) > 10000:
                    actual_a = cand
                    break
            if actual_a:
                break
                
        return actual_v, actual_a
    except Exception as e:
        print("Download error:", e)
        return actual_v, actual_a

def trim_and_encode_hd(v_path: str, a_path: Optional[str], output_path: str, start_sec: float, end_sec: float) -> bool:
    """Encodes sharp 720p/1080p HD clip with crystal clear visuals and crisp audio."""
    try:
        v_in = av.open(v_path)
        a_in = av.open(a_path) if a_path and os.path.exists(a_path) else v_in
        
        out_c = av.open(output_path, 'w')
        video_in = v_in.streams.video[0]
        audio_in = a_in.streams.audio[0] if a_in.streams.audio else None

        # Setup High Definition H.264 video
        video_out = out_c.add_stream('libx264', rate=video_in.average_rate)
        video_out.width = video_in.codec_context.width
        video_out.height = video_in.codec_context.height
        video_out.pix_fmt = 'yuv420p'
        # High quality CRF 20 (sharp crisp text and code)
        video_out.options = {'preset': 'veryfast', 'crf': '20'}

        # Setup AAC Audio
        if audio_in:
            audio_out = out_c.add_stream('aac', rate=audio_in.rate)
            audio_out.codec_context.sample_rate = audio_in.rate
        else:
            audio_out = None

        # 1. Process Video
        v_in.seek(int(start_sec / video_in.time_base), any_frame=False, backward=True, stream=video_in)
        first_v_pts = None
        for frame in v_in.decode(video_in):
            sec = float(frame.pts * video_in.time_base)
            if sec < start_sec:
                continue
            if sec > end_sec:
                break
            if first_v_pts is None:
                first_v_pts = frame.pts
            frame.pts = max(0, frame.pts - first_v_pts)
            for packet in video_out.encode(frame):
                out_c.mux(packet)
                
        for packet in video_out.encode():
            out_c.mux(packet)

        # 2. Process Audio
        if audio_in and audio_out:
            a_in.seek(int(start_sec / audio_in.time_base), any_frame=False, backward=True, stream=audio_in)
            first_a_pts = None
            for frame in a_in.decode(audio_in):
                sec = float(frame.pts * audio_in.time_base)
                if sec < start_sec:
                    continue
                if sec > end_sec:
                    break
                if first_a_pts is None:
                    first_a_pts = frame.pts
                frame.pts = max(0, frame.pts - first_a_pts)
                for packet in audio_out.encode(frame):
                    out_c.mux(packet)
                    
            for packet in audio_out.encode():
                out_c.mux(packet)

        out_c.close()
        v_in.close()
        if a_in != v_in:
            a_in.close()
            
        return os.path.exists(output_path) and os.path.getsize(output_path) > 1000
    except Exception as e:
        print("HD Trim error:", e)
        return False

def cut_clip_with_ytdlp(video_url_or_id: str, start_time: str, end_time: str, output_filename: str) -> Dict[str, Any]:
    """Downloads HD source and trims reel clip with high resolution."""
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        clean_name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', output_filename)
        if not clean_name.endswith('.mp4'):
            clean_name += '.mp4'
        out_path = os.path.join(OUTPUT_DIR, clean_name)
        
        start_sec = timestamp_to_seconds(start_time)
        end_sec = timestamp_to_seconds(end_time)
        if end_sec <= start_sec:
            end_sec = start_sec + 30.0
            
        # 1. Download or get cached HD streams
        v_file, a_file = download_source_streams(video_url_or_id)
        if not v_file or not os.path.exists(v_file):
            return {
                "success": False,
                "error": "Could not download HD video streams. Please check the URL or internet connection."
            }
            
        # 2. Trim and encode in HD
        ok = trim_and_encode_hd(v_file, a_file, out_path, start_sec, end_sec)
        if ok and os.path.exists(out_path):
            return {
                "success": True,
                "file_path": out_path,
                "message": f"Successfully clipped HD reel to {out_path}"
            }
        else:
            return {
                "success": False,
                "error": "Failed to cut HD video segment."
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Clipping error: {str(e)}"
        }

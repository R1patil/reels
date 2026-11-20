import re
from typing import Dict, List, Any, Optional
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable

def extract_video_id(url_or_id: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats or raw ID."""
    if not url_or_id:
        return None
    url_or_id = url_or_id.strip()
    
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url_or_id):
        return url_or_id
        
    patterns = [
        r'(?:v=|\/v\/|youtu\.be\/|\/embed\/|\/shorts\/|\/live\/)([A-Za-z0-9_-]{11})',
        r'(?:watch\?.*v=)([A-Za-z0-9_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    return None

def format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS or HH:MM:SS format."""
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

def timestamp_to_seconds(ts: str) -> int:
    """Convert MM:SS or HH:MM:SS format to seconds."""
    parts = list(map(int, ts.strip().split(':')))
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    elif len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return int(float(ts))

def get_youtube_transcript(video_id: str) -> Dict[str, Any]:
    """
    Fetches transcript for a YouTube video using YouTubeTranscriptApi 1.2.5+.
    Returns a dict with 'success', 'data', 'formatted_text', and 'error' if any.
    """
    try:
        api = YouTubeTranscriptApi()
        try:
            transcript_list = api.list(video_id)
        except AttributeError:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
        # Priority: Manual English -> Generated English -> Any Manual -> Any Generated
        transcript_obj = None
        try:
            transcript_obj = transcript_list.find_manually_created_transcript(['en', 'en-US', 'en-GB'])
        except Exception:
            try:
                transcript_obj = transcript_list.find_generated_transcript(['en', 'en-US', 'en-GB'])
            except Exception:
                try:
                    transcript_obj = transcript_list.find_transcript(['en'])
                except Exception:
                    for t in transcript_list:
                        transcript_obj = t
                        break
        
        if not transcript_obj:
            return {
                "success": False,
                "error": "No English or matching transcript was found for this video."
            }
            
        raw_items = transcript_obj.fetch()
        
        formatted_lines = []
        parsed_entries = []
        for item in raw_items:
            # Supports both dictionary and object formats
            start_sec = getattr(item, 'start', None) if not isinstance(item, dict) else item.get('start')
            duration = getattr(item, 'duration', 0) if not isinstance(item, dict) else item.get('duration', 0)
            text = getattr(item, 'text', '') if not isinstance(item, dict) else item.get('text', '')
            
            text = str(text).replace('\n', ' ').strip()
            ts_str = format_timestamp(float(start_sec or 0))
            formatted_lines.append(f"[{ts_str}] {text}")
            parsed_entries.append({
                "start": start_sec,
                "duration": duration,
                "end": (start_sec or 0) + (duration or 0),
                "timestamp": ts_str,
                "text": text
            })
            
        full_formatted_text = "\n".join(formatted_lines)
        total_sec = parsed_entries[-1]["end"] if parsed_entries else 0
        return {
            "success": True,
            "video_id": video_id,
            "language": getattr(transcript_obj, 'language', 'English'),
            "is_generated": getattr(transcript_obj, 'is_generated', True),
            "raw_entries": parsed_entries,
            "formatted_text": full_formatted_text,
            "total_duration_sec": total_sec,
            "total_duration_str": format_timestamp(total_sec)
        }
        
    except TranscriptsDisabled:
        return {
            "success": False,
            "error": "Subtitles/transcripts are disabled for this video by the creator."
        }
    except NoTranscriptFound:
        return {
            "success": False,
            "error": "No subtitles or transcripts could be found for this video."
        }
    except VideoUnavailable:
        return {
            "success": False,
            "error": "This video is unavailable (it may be private or removed)."
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to retrieve transcript: {str(e)}"
        }

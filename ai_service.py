import json
import re
import requests
from typing import Dict, Any, List, Optional

SYSTEM_PROMPT = """You are an elite short-form video strategist, viral content director, and audience growth consultant (specializing in YouTube Shorts, Instagram Reels, and TikTok).

Your task is to analyze the provided YouTube video transcript (which includes timestamps) and extract high-performing, high-virality Reel / Short segments.

Channel Goal / Niche:
{channel_goal}

Target Clip Duration:
{duration_pref}

CRITICAL RULES FOR EXTRACTION:
1. SCAN THE ENTIRE VIDEO TIMELINE: Do NOT only look at the first 1-2 minutes! A video has valuable gems throughout. You MUST examine the beginning, the middle (key insights, problem solving, logic breakdown), and the end (takeaways, conclusions, time complexity, punchlines).
2. DISTRIBUTE YOUR CLIPS: Extract 4 to 8 reel candidates distributed across different parts of the video (e.g., Intro/Hook, Core Explanation, Practical Demonstration, and Final Summary).
3. Virality & Hook: The first 3 seconds of each clip must have a strong hook, pattern interrupt, or compelling statement.
4. Completeness: Each clip must form a coherent, standalone idea that a viewer can understand without watching the rest of the video.

You MUST return a VALID JSON array containing 4 to 8 top reel candidates, formatted strictly as follows:
[
  {
    "id": 1,
    "section": "Early Video / Intro" or "Mid Video / Core Logic" or "Late Video / Conclusion",
    "start_timestamp": "MM:SS",
    "end_timestamp": "MM:SS",
    "duration_sec": 45,
    "viral_hook": "The exact opening line that grabs attention in the first 3 seconds",
    "suggested_title": "Punchy on-screen caption title (under 8 words)",
    "virality_score": 94,
    "tam_score": 88,
    "target_audience_fit": "Why this specific reel aligns with the channel goal",
    "why_it_will_go_viral": "Analysis of the psychology, emotion, and retention hook",
    "key_takeaway": "The core lesson or punchline the viewer walks away with",
    "transcript_excerpt": "Key excerpt of the dialogue from start to end"
  }
]

Ensure:
- Timestamps must accurately match where the speaker begins and concludes the thought in the transcript.
- JSON must be completely valid with no commentary outside the JSON array.
"""

def get_system_prompt(channel_goal: str, duration_pref: str) -> str:
    return SYSTEM_PROMPT.replace("{channel_goal}", channel_goal).replace("{duration_pref}", duration_pref)

def generate_claude_prompt(formatted_transcript: str, channel_goal: str, duration_pref: str = "30-60 seconds") -> str:
    """Generates a prompt ready to be pasted into the free Claude web interface."""
    sys_p = get_system_prompt(channel_goal, duration_pref)
    prompt = f"""{sys_p}

Here is the YouTube video transcript with timestamps:
---
{formatted_transcript}
---

Please analyze the transcript across its entire timeline and return strictly the JSON array of viral reel candidates."""
    return prompt

def parse_ai_json_response(raw_text: str) -> List[Dict[str, Any]]:
    """Cleans and extracts JSON array from model response."""
    text = raw_text.strip()
    
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()
        
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        text = match.group(0)
        
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "reels" in data:
            return data["reels"]
        elif isinstance(data, dict):
            return [data]
        return []
    except json.JSONDecodeError:
        return []

def analyze_with_gemini(api_key: str, formatted_transcript: str, channel_goal: str, duration_pref: str = "30-60 seconds") -> Dict[str, Any]:
    """Analyzes transcript using Google Gemini REST API (100% Free tier)."""
    try:
        api_key = api_key.strip()
        system_instruction_text = get_system_prompt(channel_goal, duration_pref)
        user_prompt = f"""Here is the video transcript with timestamps across the entire video:
---
{formatted_transcript}
---

Scan the ENTIRE duration of this video (do not just stop at 1:30!). Extract 4 to 8 high-potential reels from throughout the whole timeline (early, mid, and late parts).
Channel goal: '{channel_goal}'.
Target clip duration: {duration_pref}.
Return strictly the JSON array."""

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}]
                }
            ],
            "systemInstruction": {
                "parts": [{"text": system_instruction_text}]
            },
            "generationConfig": {
                "temperature": 0.7,
                "responseMimeType": "application/json"
            }
        }
        
        headers = {"Content-Type": "application/json"}
        
        models_to_try = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-flash-latest"]
        last_error = ""
        
        for model_name in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=90)
                if resp.status_code == 200:
                    res_json = resp.json()
                    candidates = res_json.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        raw_text = parts[0].get("text", "") if parts else ""
                        reels = parse_ai_json_response(raw_text)
                        return {
                            "success": True,
                            "reels": reels,
                            "raw_response": raw_text
                        }
                else:
                    last_error = f"{model_name}: {resp.status_code} - {resp.text}"
            except Exception as e:
                last_error = f"{model_name}: {str(e)}"
                
        return {
            "success": False,
            "error": f"Gemini API Error: {last_error}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Gemini API Error: {str(e)}"
        }

def analyze_with_claude(api_key: str, formatted_transcript: str, channel_goal: str, duration_pref: str = "30-60 seconds") -> Dict[str, Any]:
    """Analyzes transcript using Anthropic Claude REST API."""
    try:
        api_key = api_key.strip()
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        prompt = generate_claude_prompt(formatted_transcript, channel_goal, duration_pref)
        payload = {
            "model": "claude-3-5-sonnet-latest",
            "max_tokens": 4000,
            "temperature": 0.7,
            "system": "You are an expert viral video strategist. You output only valid JSON.",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        resp = requests.post(url, json=payload, headers=headers, timeout=90)
        if resp.status_code != 200:
            return {
                "success": False,
                "error": f"Claude API error {resp.status_code}: {resp.text}"
            }
            
        data = resp.json()
        raw_text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                raw_text += block.get("text", "")
                
        reels = parse_ai_json_response(raw_text)
        return {
            "success": True,
            "reels": reels,
            "raw_response": raw_text
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Claude API Error: {str(e)}"
        }

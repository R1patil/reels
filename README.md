# 🎬 Viral Reel & Shorts Extractor (100% Free, Zero Infrastructure Cost)

This software runs entirely on your local computer. It costs **$0**, requires **no server subscriptions**, and is designed specifically for **non-coders**.

---

## ⚡ How to Use It (Non-Coder 2-Step Guide)

### Option 1: Modern Web Dashboard (Recommended)
1. In this folder (`d:\cilents_demo`), simply **double-click** the file:
   👉 **`Launch_App.bat`**
2. Your web browser will automatically open with the dashboard.
3. Either:
   - **Paste a YouTube video URL**, OR
   - **Select `transcript.txt`** from your folder.
4. Type your channel's goal / target audience (e.g., *"Productivity tips for founders"*).
5. Click **"🚀 Extract High-Virality Reels"**.

---

### Option 2: Quick Script Runner
1. Paste your transcript into **`transcript.txt`**.
2. **Double-click** the file:
   👉 **`Run_Local_Script.bat`**
3. It instantly creates **`claude_prompt_ready.txt`** (ready to paste into Claude.ai for free) and analyzes your viral clips!

---

## 💡 Benefits of Using This Python App vs. Using Claude Online Manually

| Feature | Using Claude Online Manually | Using This Python App |
| :--- | :--- | :--- |
| **Extracting YouTube Transcripts** | You have to manually search for transcript tools, copy timestamps, or pay for transcript sites. | **1-Click Free YouTube Extraction:** Just paste the YouTube URL and it pulls the full transcript with timestamps automatically. |
| **Transcript Size Limits** | Claude Web has message/context length limits for long 1-2 hour videos. | Handles long transcripts seamlessly. |
| **Video Cutting (MP4)** | You get text timestamps, but then have to manually open video editing software, scrub, cut, and export. | **Automated Video Clipper:** Click 1 button and it cuts the exact `.mp4` video clip directly onto your computer using yt-dlp. |
| **Privacy & Zero Cost** | Pasting everything onto cloud chats. | Everything runs on your machine. No server or recurring subscriptions. |
| **Consistency** | You have to remember and rewrite the complex prompting rules every time. | Pre-configured with viral retention criteria (3-second hook evaluation, TAM score, viral psychology breakdown). |

---

## 🤖 Choosing Your AI Model

1. **Google Gemini (100% Free API - Recommended):**
   - Free from Google AI Studio.
   - Takes 30 seconds to get a key at: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
   - Paste the key once in the app sidebar—it will remember it for future uses.
2. **Claude Web Mode ($0 Free):**
   - No API key needed! The app generates `claude_prompt_ready.txt`.
   - Copy and paste it directly into [Claude.ai](https://claude.ai) on your browser.
3. **Claude API Mode (Pay-as-you-go):**
   - If you have an Anthropic Claude API key, you can enter it in the sidebar for direct automated analysis.

---

## 📂 File Structure
- `Launch_App.bat`: Double-click launcher for the visual web interface.
- `Run_Local_Script.bat`: Double-click runner for processing `transcript.txt`.
- `transcript.txt`: Where you can paste any raw video transcript.
- `app.py`: The user interface code.
- `transcript_service.py`: Automated YouTube transcript extraction.
- `ai_service.py`: Viral analysis engine and prompt builder.
- `video_clipper.py`: Video segment cutter.

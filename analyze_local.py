import os
import sys
import json
from ai_service import SYSTEM_PROMPT, generate_claude_prompt, analyze_with_gemini, analyze_with_claude, parse_ai_json_response

DEFAULT_TRANSCRIPT_FILE = "transcript.txt"
CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "channel_goal": "Grow audience with actionable viral insights",
        "duration_pref": "30-60 seconds",
        "gemini_api_key": "",
        "claude_api_key": ""
    }

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def main():
    print("=" * 60)
    print("      VIRAL REEL EXTRACTOR - LOCAL FILE RUNNER")
    print("=" * 60)
    
    cfg = load_config()
    
    # Check for transcript.txt
    if not os.path.exists(DEFAULT_TRANSCRIPT_FILE):
        print(f"\n[!] Notice: '{DEFAULT_TRANSCRIPT_FILE}' was not found.")
        print(f"    Creating an example '{DEFAULT_TRANSCRIPT_FILE}' for you...")
        with open(DEFAULT_TRANSCRIPT_FILE, "w", encoding="utf-8") as f:
            f.write("""[00:00] Hey everyone, welcome back. Today I'm sharing the single biggest mistake people make with time management.
[00:15] Most people think they don't have enough time, but the truth is you don't have an energy problem or a time problem, you have a priority problem.
[00:32] Here is a simple 2-minute rule that changed my entire productivity. If something takes less than 2 minutes, do it immediately.
[00:48] When you do this, your brain clears open cognitive loops and your anxiety drops by half.
[01:05] Try it tomorrow morning and see how much lighter your workday feels.""")
        print(f"[✓] Created '{DEFAULT_TRANSCRIPT_FILE}'. Paste your real transcript inside it and run this again!\n")
    
    with open(DEFAULT_TRANSCRIPT_FILE, "r", encoding="utf-8") as f:
        transcript_content = f.read().strip()
        
    if not transcript_content:
        print("[X] 'transcript.txt' is empty. Please paste your transcript into it.")
        input("\nPress Enter to exit...")
        return
        
    print(f"\n[✓] Loaded '{DEFAULT_TRANSCRIPT_FILE}' ({len(transcript_content)} characters)")
    
    # Channel Goal
    current_goal = cfg.get("channel_goal", "Grow audience with high-value insights")
    print(f"\nCurrent Channel Goal: '{current_goal}'")
    user_goal = input("Enter new goal (or press Enter to keep current): ").strip()
    if user_goal:
        current_goal = user_goal
        cfg["channel_goal"] = current_goal
        save_config(cfg)
        
    # Generate the ready-to-use Claude web prompt
    claude_prompt_text = generate_claude_prompt(transcript_content, current_goal, cfg.get("duration_pref", "30-60 seconds"))
    with open("claude_prompt_ready.txt", "w", encoding="utf-8") as f:
        f.write(claude_prompt_text)
    print("\n[✓] Saved ready-to-copy prompt to: 'claude_prompt_ready.txt'")
    print("    (You can open that file and copy-paste it directly into Claude.ai for free!)")
    
    # Check if Gemini or Claude API key is available
    gemini_key = cfg.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY", "")
    claude_key = cfg.get("claude_api_key") or os.environ.get("ANTHROPIC_API_KEY", "")
    
    reels = []
    if gemini_key:
        print("\n[*] Analyzing automatically using Gemini Free API...")
        res = analyze_with_gemini(gemini_key, transcript_content, current_goal)
        if res.get("success"):
            reels = res.get("reels", [])
        else:
            print(f"[!] Gemini analysis note: {res.get('error')}")
    elif claude_key:
        print("\n[*] Analyzing automatically using Claude API...")
        res = analyze_with_claude(claude_key, transcript_content, current_goal)
        if res.get("success"):
            reels = res.get("reels", [])
        else:
            print(f"[!] Claude analysis note: {res.get('error')}")
    else:
        print("\n[i] No API key configured yet. (No worries!)")
        print("    You have 2 free options:")
        print("    1. Enter a free Gemini API key to get instant automatic extraction.")
        print("    2. Or open 'claude_prompt_ready.txt' and paste it into claude.ai.")
        
        opt = input("\nWould you like to enter a free Gemini API key now? (y/n): ").strip().lower()
        if opt == 'y':
            key_input = input("Paste your Gemini API key (from https://aistudio.google.com/): ").strip()
            if key_input:
                cfg["gemini_api_key"] = key_input
                save_config(cfg)
                print("[*] Running analysis with your key...")
                res = analyze_with_gemini(key_input, transcript_content, current_goal)
                if res.get("success"):
                    reels = res.get("reels", [])
                else:
                    print(f"[!] Error: {res.get('error')}")
                    
    if reels:
        print(f"\n{'='*20} FOUND {len(reels)} VIRAL REEL OPPORTUNITIES {'='*20}\n")
        summary_lines = []
        for i, r in enumerate(reels, 1):
            title = r.get("suggested_title", f"Reel #{i}")
            start = r.get("start_timestamp", "00:00")
            end = r.get("end_timestamp", "00:00")
            score = r.get("virality_score", "N/A")
            hook = r.get("viral_hook", "")
            why = r.get("why_it_will_go_viral", "")
            
            block = f"""--- REEL #{i}: {title} ---
Timestamps: {start} -> {end}
Virality Score: {score}/100
Hook Line: "{hook}"
Why it works: {why}
Key Takeaway: {r.get('key_takeaway', '')}
"""
            print(block)
            summary_lines.append(block)
            
        with open("viral_reels_summary.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(summary_lines))
        with open("viral_reels_output.json", "w", encoding="utf-8") as f:
            json.dump(reels, f, indent=2)
            
        print("[✓] Results saved to 'viral_reels_summary.txt' and 'viral_reels_output.json'")
    
    input("\nFinished! Press Enter to exit...")

if __name__ == "__main__":
    main()

import os
import json
import streamlit as st
from transcript_service import extract_video_id, get_youtube_transcript, timestamp_to_seconds
from ai_service import (
    generate_claude_prompt,
    analyze_with_gemini,
    analyze_with_claude,
    parse_ai_json_response
)
from video_clipper import cut_clip_with_ytdlp
import auth_service
import importlib
try:
    importlib.reload(auth_service)
except Exception:
    pass
from auth_service import (
    register_user,
    login_user,
    reset_user_password,
    get_user_by_email,
    record_extraction_usage,
    upgrade_user_to_pro,
    is_supabase_enabled
)
from billing_service import PLAN_DETAILS, get_checkout_url, verify_promo_code
from razorpay_service import create_order, verify_payment_signature, get_razorpay_credentials

CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "channel_goal": "Help students solve real-world problems and master technical interviews",
        "duration_pref": "30-60 seconds",
        "gemini_api_key": "",
        "claude_api_key": "",
        "supabase_url": "",
        "supabase_key": "",
        "checkout_url": ""
    }

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

st.set_page_config(
    page_title="ReelViral AI — Turn Long Videos into Viral Shorts",
    page_icon="🎬",
    layout="wide"
)

# Custom Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
        color: #FF4B4B;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #718096;
        margin-bottom: 1.5rem;
    }
    .user-badge {
        display: inline-block;
        background: #f1f5f9;
        border: 1px solid #cbd5e1;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 600;
        color: #334155;
    }
    .pro-badge {
        background: linear-gradient(135deg, #f59e0b, #ef4444);
        color: white;
        border: none;
    }
    .paywall-card {
        background: #fff1f2;
        border: 2px solid #f43f5e;
        border-radius: 12px;
        padding: 24px;
        text-align: center;
        margin: 20px 0;
    }
    .reel-card {
        background: rgba(255, 75, 75, 0.04);
        border: 1px solid rgba(255, 75, 75, 0.2);
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1.2rem;
    }
    .score-badge {
        display: inline-block;
        background-color: #28a745;
        color: white;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.9rem;
    }
    .section-badge {
        display: inline-block;
        background-color: #6c757d;
        color: white;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .hook-box {
        background-color: rgba(0, 0, 0, 0.05);
        border-left: 4px solid #FF4B4B;
        padding: 8px 12px;
        font-weight: 600;
        margin: 8px 0;
    }
</style>
""", unsafe_allow_html=True)

cfg = load_config()

# Initialize Session State (visitors start logged out so they can sign up or log in)
if "logged_in_user" not in st.session_state:
    st.session_state["logged_in_user"] = None

# Ensure founder account is pre-registered in DB for the owner
founder = get_user_by_email("founder@reelviral.com")
if not founder:
    register_user("founder@reelviral.com", "founder123")
    upgrade_user_to_pro("founder@reelviral.com")

current_user = st.session_state.get("logged_in_user")

# ==============================================================
# RAZORPAY STANDARD PAYMENT SIGNATURE VERIFICATION (BACKEND)
# ==============================================================
params = st.query_params
if "razorpay_signature" in params and "razorpay_order_id" in params and "razorpay_payment_id" in params:
    r_order_id = params.get("razorpay_order_id")
    r_payment_id = params.get("razorpay_payment_id")
    r_signature = params.get("razorpay_signature")
    r_email = params.get("email") or (current_user["email"] if current_user else None)
    
    # Verify HMAC-SHA256 signature
    is_valid = verify_payment_signature(r_order_id, r_payment_id, r_signature)
    st.query_params.clear()
    
    if is_valid:
        if r_email:
            upgrade_user_to_pro(r_email)
        st.balloons()
        st.success(f"🎉 Payment Verified (Payment ID: {r_payment_id})! Account '{r_email}' upgraded to Creator Pro!")
        if current_user:
            current_user["subscription_tier"] = "pro"
            current_user["extractions_limit"] = 999999
            st.session_state["logged_in_user"] = current_user
        st.rerun()
    else:
        st.error("❌ Payment Signature Verification Failed! Signature mismatch. Your account was not upgraded.")

# Generic payment success fallback
elif params.get("payment_success") == "true":
    target_email = params.get("email") or (current_user["email"] if current_user else None)
    if target_email:
        upgrade_user_to_pro(target_email)
        st.balloons()
        st.success(f"🎉 Upgraded to Creator Pro!")
        st.query_params.clear()
        if current_user:
            current_user["subscription_tier"] = "pro"
            st.session_state["logged_in_user"] = current_user
        st.rerun()

# Refresh current user data
if current_user:
    updated = get_user_by_email(current_user["email"])
    if updated:
        current_user = updated
        st.session_state["logged_in_user"] = updated

# Header / Navigation Bar
nav_col1, nav_col2 = st.columns([3, 2])
with nav_col1:
    st.markdown('<div class="main-title">🎬 ReelViral AI SaaS</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Extract high-retention, high-TAM clips from YouTube videos automatically.</div>', unsafe_allow_html=True)

with nav_col2:
    if current_user:
        is_pro = current_user.get("subscription_tier") == "pro"
        used = current_user.get("extractions_used", 0)
        limit = current_user.get("extractions_limit", 2)
        
        col_status, col_btn = st.columns([3, 2])
        with col_status:
            if is_pro:
                st.markdown('<div class="user-badge pro-badge">👑 CREATOR PRO (Unlimited)</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="user-badge">⚡ Free Plan: <b>{used}/{limit} videos used</b></div>', unsafe_allow_html=True)
        with col_btn:
            if st.button("🚪 Logout", key="logout_btn"):
                st.session_state["logged_in_user"] = None
                st.rerun()
    else:
        st.info("Log in or create an account to start.")

# Helper to render Razorpay Standard Checkout Modal
def render_razorpay_modal(amount_inr=999, user_email=""):
    amount_paise = int(amount_inr * 100)
    try:
        order_res = create_order(amount_paise, currency="INR")
        if not order_res.get("success"):
            st.error(f"Failed to create Razorpay Order: {order_res.get('error')}")
            return
            
        key_id = order_res["key_id"]
        order_id = order_res["order_id"]
        
        checkout_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
        </head>
        <body style="font-family: sans-serif; text-align: center; margin: 0; padding: 10px;">
            <button id="rzp-button" style="
                background: linear-gradient(135deg, #f59e0b, #ef4444);
                color: white;
                border: none;
                padding: 14px 28px;
                border-radius: 8px;
                font-size: 1.1rem;
                font-weight: bold;
                cursor: pointer;
                box-shadow: 0 4px 14px rgba(239,68,68,0.4);
                width: 100%;
            ">
                ⚡ Pay ₹{amount_inr} with Razorpay (UPI, GPay, Cards)
            </button>
            <div id="error-msg" style="color: red; margin-top: 10px; font-size: 0.9rem; display: none;"></div>

            <script>
            var options = {{
                "key": "{key_id}",
                "amount": {amount_paise},
                "currency": "INR",
                "name": "ReelViral AI",
                "description": "Creator Pro Monthly Subscription",
                "order_id": "{order_id}",
                "prefill": {{
                    "email": "{user_email}"
                }},
                "theme": {{
                    "color": "#FF4B4B"
                }},
                "handler": function (response){{
                    var redirectUrl = window.top.location.origin + window.top.location.pathname + 
                        '?razorpay_order_id=' + encodeURIComponent(response.razorpay_order_id) +
                        '&razorpay_payment_id=' + encodeURIComponent(response.razorpay_payment_id) +
                        '&razorpay_signature=' + encodeURIComponent(response.razorpay_signature) +
                        '&email=' + encodeURIComponent("{user_email}");
                    window.top.location.href = redirectUrl;
                }},
                "modal": {{
                    "ondismiss": function(){{
                        console.log("Razorpay checkout modal closed by user.");
                    }}
                }}
            }};

            var rzp = new Razorpay(options);
            rzp.on('payment.failed', function (response){{
                var errDiv = document.getElementById('error-msg');
                errDiv.innerText = "Payment Failed: " + response.error.description;
                errDiv.style.display = "block";
            }});

            document.getElementById('rzp-button').onclick = function(e){{
                rzp.open();
                e.preventDefault();
            }};
            </script>
        </body>
        </html>
        """
        st.components.v1.html(checkout_html, height=80)
    except Exception as e:
        st.error(f"Razorpay Checkout Error: {str(e)}")

# Sidebar: Authentication & Configuration
with st.sidebar:
    st.header("👤 Account & Billing")
    
    if not current_user:
        auth_tab1, auth_tab2, auth_tab3 = st.tabs(["🔑 Log In", "📝 Sign Up", "🔄 Forgot Password"])
        with auth_tab1:
            log_email = st.text_input("Email", key="login_email")
            log_pass = st.text_input("Password", type="password", key="login_pass")
            if st.button("Log In", type="primary", use_container_width=True):
                res = login_user(log_email, log_pass)
                if res["success"]:
                    st.session_state["logged_in_user"] = res["user"]
                    st.rerun()
                else:
                    st.error(res["error"])
                    
        with auth_tab2:
            reg_email = st.text_input("Email", key="reg_email")
            reg_pass = st.text_input("Password", type="password", key="reg_pass")
            if st.button("Create Account", type="primary", use_container_width=True):
                res = register_user(reg_email, reg_pass)
                if res["success"]:
                    st.session_state["logged_in_user"] = res["user"]
                    st.success("Account created!")
                    st.rerun()
                else:
                    st.error(res["error"])

        with auth_tab3:
            st.caption("Reset your password:")
            rst_email = st.text_input("Your Registered Email", key="rst_email")
            rst_new_pw = st.text_input("New Password (min 6 chars)", type="password", key="rst_new_pw")
            if st.button("Update Password", type="primary", use_container_width=True):
                res_rst = reset_user_password(rst_email, rst_new_pw)
                if res_rst["success"]:
                    st.success(res_rst["message"])
                else:
                    st.error(res_rst["error"])
    else:
        st.write(f"Logged in as: **{current_user['email']}**")
        is_pro = current_user.get("subscription_tier") == "pro"
        
        if not is_pro:
            st.warning("You are on the **Starter (Free)** plan.")
            st.markdown("### ⚡ Upgrade to Pro (₹999/mo)")
            render_razorpay_modal(amount_inr=999, user_email=current_user["email"])
            st.markdown("""
            <div style="text-align: center; margin-top: 6px; margin-bottom: 12px;">
                <a href="https://razorpay.me/@seventeense" target="_blank" style="display: block; background: #0c2340; color: #fff; padding: 8px 12px; border-radius: 6px; text-decoration: none; font-size: 0.9rem; font-weight: 600; border: 1px solid #2563eb;">
                    📱 Pay via UPI / Razorpay.me (@seventeense)
                </a>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("🎟 Have a Promo/Founder Code?"):
                p_code = st.text_input("Enter code:", key="promo_input")
                if st.button("Apply Code"):
                    if verify_promo_code(p_code):
                        upgrade_user_to_pro(current_user["email"])
                        st.success("🎉 Upgraded to Creator Pro!")
                        st.rerun()
                    else:
                        st.error("Invalid promo code.")
        else:
            st.success("✓ Creator Pro Active — Unlimited HD Extractions")

    st.markdown("---")
    st.subheader("💳 Razorpay Integration")
    with st.expander("View Razorpay Status"):
        r_id, r_sec = get_razorpay_credentials()
        if r_id:
            st.success(f"✓ Key ID: `{r_id[:12]}...`")
            st.caption("Standard Web Checkout modal active (HMAC-SHA256 signature verification enabled).")
        else:
            st.warning("Razorpay credentials missing from .env or Secrets.")

    st.markdown("---")
    st.subheader("⚙️ AI Model")
    ai_choice = st.radio(
        "AI Engine:",
        ["Google Gemini (Included / Free)", "Claude API (Custom Key)", "Claude Web (Copy-Paste)"],
        index=0
    )
    
    gemini_key = cfg.get("gemini_api_key", "")
    if ai_choice == "Google Gemini (Included / Free)":
        gem_input = st.text_input("Gemini API Key:", value=gemini_key, type="password")
        if gem_input != gemini_key:
            cfg["gemini_api_key"] = gem_input
            save_config(cfg)
            gemini_key = gem_input

    # Supabase Settings
    with st.expander("⚡ Cloud Database (Supabase)"):
        sb_url_in = st.text_input("Supabase Project URL:", value=cfg.get("supabase_url", ""), placeholder="https://xxx.supabase.co")
        sb_key_in = st.text_input("Supabase Anon Key:", value=cfg.get("supabase_key", ""), type="password", placeholder="eyJhbG...")
        if sb_url_in != cfg.get("supabase_url", "") or sb_key_in != cfg.get("supabase_key", ""):
            cfg["supabase_url"] = sb_url_in
            cfg["supabase_key"] = sb_key_in
            save_config(cfg)
            st.rerun()
        if is_supabase_enabled():
            st.success("✓ Connected to Supabase Cloud")
        else:
            st.info("Using local database (`saas_database.db`)")

# Main Screen Inputs
input_mode = st.radio(
    "Choose Input Source:",
    ["🔗 YouTube Video URL", "📄 Local transcript.txt / Custom File"],
    horizontal=True
)

formatted_transcript = ""
video_url_for_clipping = ""
video_id = None

if input_mode == "🔗 YouTube Video URL":
    yt_url = st.text_input(
        "Enter YouTube Video URL:",
        value="https://www.youtube.com/watch?v=Qe7qERb9z9I",
        placeholder="https://www.youtube.com/watch?v=..."
    )
    if yt_url:
        video_id = extract_video_id(yt_url)
        video_url_for_clipping = yt_url
        if video_id:
            st.video(f"https://www.youtube.com/watch?v={video_id}")
        else:
            st.warning("Please enter a valid YouTube video link.")
else:
    file_mode = st.radio("File source:", ["Use 'transcript.txt' in project folder", "Upload custom .txt file"], horizontal=True)
    if file_mode == "Use 'transcript.txt' in project folder":
        if os.path.exists("transcript.txt"):
            with open("transcript.txt", "r", encoding="utf-8") as f:
                formatted_transcript = f.read()
            st.text_area("Loaded transcript.txt content preview:", formatted_transcript[:500] + ("..." if len(formatted_transcript) > 500 else ""), height=120)
        else:
            st.info("Place your `transcript.txt` file inside this folder.")
    else:
        uploaded_file = st.file_uploader("Upload transcript text file", type=["txt"])
        if uploaded_file is not None:
            formatted_transcript = uploaded_file.read().decode("utf-8")
            st.success("File uploaded successfully!")

st.markdown("---")
st.subheader("🎯 Strategy & Channel Target")
col1, col2 = st.columns([3, 1])

with col1:
    channel_goal = st.text_area(
        "Channel Goal & Audience Profile:",
        value=cfg.get("channel_goal", "Help students solve real-world problems and master technical interviews"),
        help="Specify the topic, who the audience is, and what makes a clip valuable for them.",
        height=70
    )
    if channel_goal != cfg.get("channel_goal"):
        cfg["channel_goal"] = channel_goal
        save_config(cfg)

with col2:
    duration_pref = st.selectbox(
        "Target Reel Duration:",
        ["30-60 seconds (Standard)", "15-30 seconds (Punchy)", "60-90 seconds (In-depth)"],
        index=0
    )

# Paywall Gate Check
can_extract = True
if current_user:
    is_pro = current_user.get("subscription_tier") == "pro"
    used = current_user.get("extractions_used", 0)
    limit = current_user.get("extractions_limit", 2)
    if not is_pro and used >= limit:
        can_extract = False
        st.markdown(f"""
        <div class="paywall-card">
            <h2 style="color: #e11d48; margin-top: 0;">🛑 Free Plan Limit Reached ({used}/{limit} videos)</h2>
            <p style="font-size: 1.1rem; color: #4b5563;">
                You've used all 2 free extractions for this month.<br>
                Upgrade to <b>Creator Pro</b> for unlimited video extractions, 720p HD clip downloads, and priority processing.
            </p>
        </div>
        """, unsafe_allow_html=True)
        # Render the Standard Razorpay Checkout Button right inside the paywall
        render_razorpay_modal(amount_inr=999, user_email=current_user["email"])
        st.markdown("""
        <div style="text-align: center; margin-top: 8px; margin-bottom: 12px;">
            <a href="https://razorpay.me/@seventeense" target="_blank" style="display: inline-block; background: #0c2340; color: #fff; padding: 10px 24px; border-radius: 8px; text-decoration: none; font-size: 1rem; font-weight: 600; border: 1px solid #2563eb;">
                📱 Or Pay ₹999 directly via UPI / Card (razorpay.me/@seventeense)
            </a>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 0.85rem; color: #9ca3af;'>Powered by Razorpay. Instant activation.</p>", unsafe_allow_html=True)

# Execution Button
analyze_btn = st.button("🚀 Extract High-Virality Reels", type="primary", use_container_width=True, disabled=not can_extract)

if analyze_btn and can_extract:
    # 1. Require Login & Quota Check
    if not current_user:
        st.warning("👉 Please **Create an Account** or **Log In** in the left sidebar to start extracting reels! (2 Free Extractions included)")
        st.stop()
        
    usage = record_extraction_usage(current_user["email"])
    if not usage["allowed"]:
        st.error(usage["error"])
        st.stop()
            
    # 2. Extract Transcript
    if input_mode == "🔗 YouTube Video URL":
        if not video_id:
            st.error("Please enter a valid YouTube URL.")
            st.stop()
            
        with st.spinner("Extracting full transcript across entire video length from YouTube..."):
            res_transcript = get_youtube_transcript(video_id)
            if not res_transcript["success"]:
                st.error(f"❌ {res_transcript['error']}")
                st.stop()
            formatted_transcript = res_transcript["formatted_text"]
            dur_str = res_transcript.get("total_duration_str", "Full video")
            lines_cnt = len(formatted_transcript.splitlines())
            with open("transcript.txt", "w", encoding="utf-8") as f:
                f.write(formatted_transcript)
            st.toast(f"Extracted transcript: {dur_str} ({lines_cnt} timestamps)!", icon="🎬")

    if not formatted_transcript.strip():
        st.error("Please enter a YouTube URL or provide a transcript file.")
        st.stop()

    st.session_state["formatted_transcript"] = formatted_transcript
    st.session_state["video_url_for_clipping"] = video_url_for_clipping
    st.session_state["video_id"] = video_id

    # 3. AI Analysis
    with st.spinner("🤖 AI scanning full video timeline for high-retention viral hooks & TAM..."):
        res = analyze_with_gemini(gemini_key, formatted_transcript, channel_goal, duration_pref)
        if not res.get("success"):
            st.error(res.get("error"))
            st.stop()
        st.session_state["reels"] = res.get("reels", [])
        st.success(f"🎉 Found {len(st.session_state['reels'])} High-Virality Reel Candidates across the video!")
        st.rerun()

# Display Reels if available
if "reels" in st.session_state and st.session_state["reels"]:
    reels = st.session_state["reels"]
    st.markdown("## 📊 Recommended Viral Reels (Across Video Timeline)")
    
    current_url = st.session_state.get("video_url_for_clipping")
    active_vid = st.session_state.get("video_id")
    is_pro = current_user.get("subscription_tier") == "pro" if current_user else False
    
    for i, reel in enumerate(reels, 1):
        with st.container():
            section_tag = reel.get('section', 'Video Highlight')
            st.markdown(f"""
            <div class="reel-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span class="section-badge">{section_tag}</span>
                        <h3 style="margin: 4px 0 0 0;">#{i}: {reel.get('suggested_title', f'Reel {i}')}</h3>
                    </div>
                    <div>
                        <span class="score-badge">🔥 Virality: {reel.get('virality_score', 85)}/100</span>
                        <span class="score-badge" style="background-color: #3182ce; margin-left: 8px;">🌍 TAM: {reel.get('tam_score', 80)}/100</span>
                    </div>
                </div>
                <p style="margin-top: 8px; font-size: 0.95rem; color: #4a5568;">
                    ⏱ <b>Timestamps:</b> <code>{reel.get('start_timestamp', '00:00')}</code> ➔ <code>{reel.get('end_timestamp', '00:00')}</code> 
                    (Duration: ~{reel.get('duration_sec', '45')}s)
                </p>
                <div class="hook-box">
                    🪝 <b>Opening Hook (0-3s):</b> "{reel.get('viral_hook', '')}"
                </div>
                <p><b>🧠 Why It Will Go Viral:</b> {reel.get('why_it_will_go_viral', '')}</p>
                <p><b>🎯 Audience Alignment:</b> {reel.get('target_audience_fit', '')}</p>
                <p><b>💡 Core Takeaway:</b> {reel.get('key_takeaway', '')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Interactive Video Preview Segment if YouTube ID available
            start_str = reel.get('start_timestamp', '00:00')
            end_str = reel.get('end_timestamp', '00:30')
            start_s = int(timestamp_to_seconds(start_str))
            end_s = int(timestamp_to_seconds(end_str))
            
            if active_vid:
                with st.expander(f"▶️ Preview Reel #{i} Video ({start_str} - {end_str})"):
                    embed_url = f"https://www.youtube.com/embed/{active_vid}?start={start_s}&end={end_s}"
                    st.components.v1.iframe(embed_url, height=360)
            
            # Action buttons for this reel
            col_a, col_b = st.columns([1, 1])
            with col_a:
                copy_text = f"Title: {reel.get('suggested_title')}\nSection: {section_tag}\nTimestamps: {start_str} - {end_str}\nHook: {reel.get('viral_hook')}\nTakeaway: {reel.get('key_takeaway')}"
                st.download_button(
                    label=f"📋 Download Reel #{i} Summary (.txt)",
                    data=copy_text,
                    file_name=f"reel_{i}_info.txt",
                    key=f"dl_btn_{i}"
                )
            with col_b:
                if current_url:
                    if is_pro:
                        if st.button(f"✂️ Cut & Download HD Clip #{i} (.mp4)", key=f"clip_btn_{i}"):
                            with st.spinner(f"Cutting HD clip #{i} from {start_str} to {end_str}..."):
                                clip_res = cut_clip_with_ytdlp(
                                    current_url,
                                    start_str,
                                    end_str,
                                    f"reel_{i}_{reel.get('suggested_title', 'clip').replace(' ', '_')[:20]}.mp4"
                                )
                                if clip_res["success"]:
                                    st.success(f"✓ HD Clip created: {clip_res['file_path']}")
                                    if os.path.exists(clip_res["file_path"]):
                                        with open(clip_res["file_path"], "rb") as vf:
                                            st.download_button(
                                                "📥 Click here to save HD MP4 to your PC",
                                                data=vf.read(),
                                                file_name=os.path.basename(clip_res["file_path"]),
                                                mime="video/mp4",
                                                key=f"mp4_dl_{i}"
                                            )
                                else:
                                    st.error(clip_res.get("error"))
                    else:
                        st.button(f"🔒 Cut & Download HD Clip #{i} (Pro Feature)", key=f"locked_clip_{i}", disabled=True, help="Upgrade to Creator Pro to unlock HD clip downloads!")

    # Export all reels as JSON
    st.markdown("---")
    st.download_button(
        "💾 Export All Reels as JSON",
        data=json.dumps(reels, indent=2),
        file_name="viral_reels.json",
        mime="application/json"
    )

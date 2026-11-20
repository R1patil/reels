# 🚀 ReelViral AI — Micro-SaaS Deployment & Monetization Guide

Your application is now a complete **commercial Micro-SaaS** with user accounts, plan limits, and paywalls built-in!

---

## 💎 How Your Micro-SaaS Is Structured

| Feature | Starter (Free) Plan | Creator Pro ($19 / month) |
| :--- | :--- | :--- |
| **Monthly Quota** | **2 Videos / Month** | **Unlimited Extractions** |
| **Clips Per Video** | Up to 3 Viral Highlights | **6 to 8 Clips Across Entire Timeline** |
| **Timeline Coverage** | Intro only | **Full Scan (Beginning, Mid, End)** |
| **HD Video Cutting (.mp4)** | 🔒 Locked | **🔓 1-Click 720p HD Clipping & Download** |
| **Interactive Previews** | ✅ Yes | ✅ Yes |
| **Virality & TAM Scoring** | ✅ Yes | ✅ Yes |

---

## 🧪 Testing Your SaaS Features Locally

1. **Launch the App:**
   - Double-click `Launch_App.bat`.
2. **User Accounts & Quota:**
   - Look at the top right: It shows your plan badge: `⚡ Free Plan: 0/2 videos used`.
   - Run a video analysis: Notice the count increments to `1/2`, then `2/2`.
   - On the 3rd attempt, the app automatically triggers the **Paywall Card** preventing further extractions and prompting the user to upgrade for **$19/mo**.
3. **Founder / Owner Bypass Code:**
   - In the sidebar, expand **🎟 Have a Promo/Founder Code?**
   - Enter: **`FOUNDER100`**
   - Click **Apply Code** ➔ Your account is instantly upgraded to **👑 CREATOR PRO (Unlimited)**!
   - Now the HD Video Cutter is unlocked!

---

## 🌐 Deploying Live to the Web for Free (Streamlit Community Cloud)

You can launch your SaaS on the internet for **$0 server cost**:

### Step 1: Create a GitHub Repository
1. Go to [github.com](https://github.com) and sign in.
2. Click **New Repository**, name it `reelviral-saas`, and select **Public** or **Private**.
3. Upload all files from `d:\cilents_demo` into this repository.

### Step 2: Deploy on Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with your GitHub account.
2. Click **Create app**.
3. Select your repository: `reelviral-saas`.
4. Set main file path: `app.py`.
5. Under **Advanced Settings > Secrets**, paste your Gemini API key:
   ```toml
   GEMINI_API_KEY = "your-gemini-key-here"
   LEMONSQUEEZY_CHECKOUT_URL = "https://yourbrand.lemonsqueezy.com/buy/..."
   ```
6. Click **Deploy!**

Your SaaS will be live at `https://your-name-reelviral.streamlit.app` accessible from anywhere in the world!

---

## 💳 Connecting Real Payments (LemonSqueezy)
1. Sign up for free at [LemonSqueezy.com](https://lemonsqueezy.com).
2. Go to **Products > Add Product**:
   - Name: `ReelViral Creator Pro`
   - Price: `$19 / month (Subscription)`
3. Copy your product's **Checkout Share URL**.
4. In `billing_service.py`, set:
   ```python
   DEFAULT_CHECKOUT_URL = "https://yourbrand.lemonsqueezy.com/buy/YOUR-PRODUCT-ID"
   ```
Whenever a user clicks **Upgrade to Pro ($19/mo)**, they will be taken directly to your checkout page to enter their card!

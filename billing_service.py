import os
import json
from typing import Dict, Any

CONFIG_FILE = "config.json"

# Default payment link (supports Razorpay, Cosmofeed, Instamojo, Cashfree, or Stripe)
DEFAULT_CHECKOUT_URL = "https://razorpay.me/@seventeense"

PLAN_DETAILS = {
    "free": {
        "name": "Starter (Free)",
        "price": "₹0 / month",
        "monthly_limit": 2,
        "features": [
            "2 YouTube Video Extractions / month",
            "Up to 3 Viral Reel Candidates",
            "Viral Hook & TAM Analysis",
            "In-Browser Video Segment Preview",
            "Standard Export"
        ]
    },
    "pro": {
        "name": "Creator Pro",
        "price_inr": "₹999 / month",
        "price_usd": "$19 / month",
        "monthly_limit": "Unlimited",
        "features": [
            "Unlimited YouTube Video Extractions",
            "Full Timeline Deep Scan (Beginning, Mid, End)",
            "6 to 8 Viral Reel Candidates per video",
            "1-Click 720p HD MP4 Video Clipping & Download",
            "Auto Video & Audio Synchronization",
            "Zero Watermarks",
            "Priority Processing Speed"
        ]
    }
}

def get_checkout_url(user_email: str) -> str:
    """
    Generates checkout link supporting Indian gateways (Razorpay, Cosmofeed, Instamojo, Cashfree).
    """
    checkout_url = ""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                checkout_url = cfg.get("checkout_url", "")
        except Exception:
            pass
            
    if not checkout_url:
        checkout_url = os.environ.get("PAYMENT_CHECKOUT_URL", DEFAULT_CHECKOUT_URL)
        
    sep = "&" if "?" in checkout_url else "?"
    
    # Razorpay payment links support pre-filling:
    # https://rzp.io/l/yourlink?email=...
    if "rzp.io" in checkout_url or "razorpay.com" in checkout_url:
        return f"{checkout_url}{sep}email={user_email}"
    elif "stripe.com" in checkout_url:
        return f"{checkout_url}{sep}prefilled_email={user_email}"
    elif "lemonsqueezy.com" in checkout_url:
        return f"{checkout_url}{sep}checkout[email]={user_email}"
    else:
        # Standard generic parameter
        return f"{checkout_url}{sep}email={user_email}"

def verify_promo_code(code: str) -> bool:
    """Special promotional/testing codes or Razorpay Payment IDs."""
    c = code.strip()
    if c.startswith("pay_") and len(c) >= 12:
        return True
    valid_codes = ["FOUNDER100", "PROBETA", "VIRAL2026", "UPIPAY", "TESTPAY", "SEVENTEENSE"]
    return c.upper() in valid_codes

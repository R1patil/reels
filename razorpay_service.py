import os
import hmac
import hashlib
import razorpay
from dotenv import load_dotenv
from typing import Dict, Any, Optional

# Load environment variables
load_dotenv()

def get_razorpay_credentials():
    """Retrieves Razorpay credentials from env, st.secrets, or config."""
    key_id = os.environ.get("RAZORPAY_KEY_ID", "")
    key_secret = os.environ.get("RAZORPAY_KEY_SECRET", "")
    
    # Check Streamlit secrets if running in Streamlit
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            key_id = key_id or st.secrets.get("RAZORPAY_KEY_ID", "")
            key_secret = key_secret or st.secrets.get("RAZORPAY_KEY_SECRET", "")
    except Exception:
        pass
        
    return key_id.strip(), key_secret.strip()

def get_client() -> razorpay.Client:
    key_id, key_secret = get_razorpay_credentials()
    if not key_id or not key_secret:
        raise ValueError("Razorpay credentials missing. Please set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET.")
    return razorpay.Client(auth=(key_id, key_secret))

def create_order(amount_paise: int, currency: str = "INR", receipt: Optional[str] = None, notes: Optional[dict] = None) -> Dict[str, Any]:
    """
    Creates a Razorpay order.
    Minimum amount: 100 paise.
    """
    if amount_paise < 100:
        raise ValueError("Amount must be at least 100 paise (₹1.00).")
        
    key_id, key_secret = get_razorpay_credentials()
    client = get_client()
    
    order_data = {
        "amount": int(amount_paise),
        "currency": currency.upper(),
        "receipt": receipt or f"receipt_{int(hashlib.md5(str(amount_paise).encode()).hexdigest(), 16) % 1000000}",
        "notes": notes or {}
    }
    
    try:
        order = client.order.create(data=order_data)
        return {
            "success": True,
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "key_id": key_id
        }
    except razorpay.errors.BadRequestError as e:
        return {"success": False, "status_code": 400, "error": str(e)}
    except razorpay.errors.GatewayError as e:
        return {"success": False, "status_code": 504, "error": str(e)}
    except Exception as e:
        return {"success": False, "status_code": 500, "error": f"Failed to create Razorpay order: {str(e)}"}

def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """
    Verifies Razorpay payment signature using HMAC-SHA256(order_id + "|" + payment_id, KEY_SECRET).
    Returns True only if signatures match.
    """
    if not order_id or not payment_id or not signature:
        return False
        
    key_id, key_secret = get_razorpay_credentials()
    if not key_secret:
        return False
        
    try:
        # Standard HMAC-SHA256 signature verification
        msg = f"{order_id}|{payment_id}".encode('utf-8')
        generated_signature = hmac.new(
            key_secret.encode('utf-8'),
            msg,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(generated_signature, signature)
    except Exception:
        return False

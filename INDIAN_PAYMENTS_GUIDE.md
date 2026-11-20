# 🇮🇳 Indian Payment Gateway Guide (UPI, GPay, PhonePe, Cards)

For Indian founders, you don't need Stripe or LemonSqueezy! 
You can accept payments instantly via **UPI (Google Pay, PhonePe, Paytm, BHIM)** and **Indian Debit/Credit cards** using **Razorpay** or **Cosmofeed**.

---

### Option 1: Razorpay Payment Links (Most Popular in India)

1. **Sign Up:** Go to **[razorpay.com](https://razorpay.com)** and create a free account (Individual account with PAN & Bank Account).
2. **Create Payment Link:**
   - In the left menu, click **Payment Links > Create Payment Link**.
   - **Amount:** `₹999` (or whatever price you choose, e.g. `₹499`, `₹1499`).
   - **Description:** `ReelViral AI Creator Pro (Monthly Access)`.
   - **Redirect URL:** In the payment link settings, set redirect URL to:
     `https://your-app.streamlit.app/?payment_success=true`
3. Click **Create Link** and copy the link (looks like: `https://rzp.io/l/abcdef123`).

---

### Option 2: Cosmofeed (Easiest — Takes 60 Seconds)

1. Go to **[cosmofeed.com](https://cosmofeed.com)** (used by thousands of Indian creators and SaaS builders).
2. Sign up with mobile number & Google.
3. Click **Create Digital Product / Subscription**:
   - Set price: `₹999`
   - Set Redirect URL on success to: `https://your-app.streamlit.app/?payment_success=true`
4. Copy your Cosmofeed product link (looks like: `https://cosmofeed.com/vp/...`).

---

### How to Connect It to Your App:
1. Open your app dashboard (`localhost:8502`).
2. In the sidebar, expand **"🇮🇳 Payment Gateway (Razorpay / UPI / Cards)"**.
3. Paste your Razorpay or Cosmofeed link.
4. It saves automatically!

Now, when any customer clicks **"⚡ Upgrade to Pro — ₹999/mo"**, they can pay instantly via:
- **UPI (Google Pay, PhonePe, Paytm, QR Code)**
- **Debit / Credit Cards (RuPay, Visa, MasterCard)**
- **NetBanking**
- And upon payment, their account is automatically upgraded to **Creator Pro**!

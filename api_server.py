import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from razorpay_service import create_order, verify_payment_signature, get_razorpay_credentials
from auth_service import upgrade_user_to_pro

PORT = 5000

class RazorpayAPIHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_POST(self):
        parsed_path = urlparse(self.path).path
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b"{}"
        
        try:
            body = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            self._set_headers(400)
            self.wfile.write(json.dumps({"error": "Invalid JSON body"}).encode())
            return

        # ==========================================
        # 1. POST /api/create-order
        # ==========================================
        if parsed_path == "/api/create-order":
            amount = body.get("amount")
            currency = body.get("currency", "INR")
            receipt = body.get("receipt")
            
            if not amount or not isinstance(amount, (int, float)):
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": "Missing or invalid amount"}).encode())
                return
                
            amount_paise = int(amount)
            if amount_paise < 100:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": "Minimum amount is 100 paise (₹1.00)"}).encode())
                return
                
            try:
                res = create_order(amount_paise, currency=currency, receipt=receipt)
                if res.get("success"):
                    self._set_headers(200)
                    self.wfile.write(json.dumps({
                        "order_id": res["order_id"],
                        "amount": res["amount"],
                        "currency": res["currency"],
                        "key_id": res["key_id"]
                    }).encode())
                else:
                    status_code = res.get("status_code", 500)
                    self._set_headers(status_code)
                    self.wfile.write(json.dumps({"error": res.get("error")}).encode())
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode())
            return

        # ==========================================
        # 2. POST /api/verify-payment
        # ==========================================
        elif parsed_path == "/api/verify-payment":
            order_id = body.get("razorpay_order_id")
            payment_id = body.get("razorpay_payment_id")
            signature = body.get("razorpay_signature")
            email = body.get("email")
            
            # Missing fields validation
            if not order_id or not payment_id or not signature:
                self._set_headers(400)
                self.wfile.write(json.dumps({
                    "status": "error",
                    "message": "Missing required fields (razorpay_order_id, razorpay_payment_id, razorpay_signature)"
                }).encode())
                return
                
            # Signature Verification
            is_valid = verify_payment_signature(order_id, payment_id, signature)
            if is_valid:
                # Upgrade user account
                if email:
                    upgrade_user_to_pro(email)
                self._set_headers(200)
                self.wfile.write(json.dumps({
                    "status": "success",
                    "message": "Payment verified successfully",
                    "order_id": order_id,
                    "payment_id": payment_id
                }).encode())
            else:
                # Signature mismatch - return 400 and do NOT mark as paid
                self._set_headers(400)
                self.wfile.write(json.dumps({
                    "status": "error",
                    "message": "Invalid payment signature (Signature mismatch)"
                }).encode())
            return

        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode())

def run_server():
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, RazorpayAPIHandler)
    print(f"Razorpay Backend API running at http://localhost:{PORT}")
    print("Endpoints available:")
    print("  POST /api/create-order")
    print("  POST /api/verify-payment")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()

if __name__ == "__main__":
    run_server()

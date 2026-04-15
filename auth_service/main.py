"""
AUTH SERVICE – Port 8001
Endpoint: POST /login
"""
 
import uuid
from flask import Flask, request, jsonify
 
app = Flask(__name__)
 
 
@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    username = body.get("username", "").strip()
 
    if not username:
        return jsonify({"error": "username is required"}), 400
 
    fake_token = f"fake-jwt-{uuid.uuid4().hex[:16]}"
    return jsonify({
        "access_token": fake_token,
        "user": username
    }), 200
 
 
if __name__ == "__main__":
    print("🔐 Auth Service running on http://localhost:8001")
    app.run(port=8001, debug=False)
 
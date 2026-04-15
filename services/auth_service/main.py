from fastapi import FastAPI
import jwt
import datetime

app = FastAPI()
SECRET = "secret"

@app.post("/login")
def login(data: dict):
    payload = {
        "user": data.get("username", "guest"),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }

    token = jwt.encode(payload, SECRET, algorithm="HS256")

    return {
        "access_token": token
    }
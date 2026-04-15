from fastapi import FastAPI

app = FastAPI()

@app.post("/login")
def login(data: dict):
    return {
        "access_token": "fake-jwt-token",
        "user": data.get("username", "guest")
    }
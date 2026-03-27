import json
from fastapi.testclient import TestClient
from app.main import app

with TestClient(app) as client:
    response = client.get("/analytics/top-risk?ecosystem=npm&limit=5")
    print(response.status_code)
    print(response.json())

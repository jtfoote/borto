from fastapi import FastAPI
from sqlalchemy.orm import Session
from shared.models import engine, SystemMetric

app = FastAPI()

@app.get("/api/metrics/latest")
def get_latest_metric():
    with Session(engine) as db:
        # Fetch the most recent db entry and return
        latest = db.query(SystemMetric).order_by(SystemMetric.id.desc()).first()
        return latest
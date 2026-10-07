from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from shared.models import engine, SystemMetric

app = FastAPI()


@app.get("/api/metrics/latest")
def get_latest_metric():
    with Session(engine) as db:
        # Fetch the most recent db entry and return
        latest = db.query(SystemMetric).order_by(SystemMetric.id.desc()).first()
        return latest

@app.get("/api/metrics/dc1")
def get_dc1():
    # Grab all values with location 2, i.e., in the dc1 output
    with Session(engine) as db:
        statement = select(SystemMetric).where(SystemMetric.value_location == 2).order_by(desc(SystemMetric.id)).limit(50)
        values = db.execute(statement).scalars().all()[::-1]
        return values

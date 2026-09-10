from datetime import datetime, timedelta, timezone
from pathlib import Path
import pickle

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Indian Railways Real-Time ETA API")
MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "xgboost_eta_v1.pkl"


class ETARequest(BaseModel):
    train_id: str = Field(min_length=1)
    next_station_code: str = Field(min_length=1)
    scheduled_arrival: datetime
    current_speed: float = Field(default=0, ge=0)


def load_model() -> object | None:
    if not MODEL_PATH.exists():
        return None
    try:
        with MODEL_PATH.open("rb") as model_file:
            return pickle.load(model_file)
    except (OSError, pickle.PickleError, EOFError):
        return None


model = load_model()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": "loaded" if model is not None else "fallback"}


@app.post("/predict-eta")
def predict_eta(request: ETARequest) -> dict[str, object]:
    scheduled = request.scheduled_arrival
    if scheduled.tzinfo is None:
        scheduled = scheduled.replace(tzinfo=timezone.utc)

    predicted_delay = 0.0
    if model is not None and hasattr(model, "predict"):
        try:
            predicted_delay = max(0.0, float(model.predict([[0, request.current_speed]])[0]))
        except (TypeError, ValueError, IndexError):
            predicted_delay = 0.0

    predicted_eta = scheduled + timedelta(minutes=predicted_delay)
    return {
        "train_id": request.train_id,
        "next_station_code": request.next_station_code,
        "scheduled_arrival": scheduled.isoformat(),
        "predicted_eta": predicted_eta.isoformat(),
        "predicted_delay_minutes": round(predicted_delay, 1),
        "confidence_score": 0.75 if model is not None else 0.25,
        "delay_reasons": [] if predicted_delay == 0 else ["model_prediction"],
    }
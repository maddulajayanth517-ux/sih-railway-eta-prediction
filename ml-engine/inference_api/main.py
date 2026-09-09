from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pickle
import pandas as pd
from datetime import datetime, timedelta
import os

app = FastAPI(title="Indian Railways Real-Time ETA API")

# Setup model paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, '../models/xgb_real_world_eta.pkl')
ENCODER_PATH = os.path.join(BASE_DIR, '../models/station_encoder.pkl')

# Load trained models on startup
try:
    with open(MODEL_PATH, 'rb') as f:
        model = pickle.load(f)
    with open(ENCODER_PATH, 'rb') as f:
        station_encoder = pickle.load(f)
    print("Successfully loaded trained 38M-row model artifacts!")
except Exception as e:
    print(f"Error loading models: {e}")

class ETARequest(BaseModel):
    train_no: str
    station_name: str
    scheduled_arrival: str  # ISO format string (e.g. '2026-09-09T18:30:00Z')

@app.post("/predict-eta")
def predict_eta(req: ETARequest):
    # Safely handle station encoding
    try:
        if req.station_name in station_encoder.classes_:
            encoded_station = station_encoder.transform([req.station_name])[0]
        else:
            encoded_station = 0  # Fallback for unlisted stations
    except Exception:
        encoded_station = 0

    # Feature matrix matching the training step ['station_encoded', 'distance']
    # If distance was filled as 0 during Colab training, we maintain that schema
    input_df = pd.DataFrame([{
        'station_encoded': encoded_station,
        'distance': 0
    }])

    # Predict delay in minutes
    predicted_delay = float(model.predict(input_df)[0])

    # Calculate actual estimated arrival time
    try:
        scheduled_time = datetime.fromisoformat(req.scheduled_arrival.replace('Z', '+00:00')).replace(tzinfo=None)
        predicted_eta = scheduled_time + timedelta(minutes=predicted_delay)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format for scheduled_arrival")

    return {
        "train_no": req.train_no,
        "station_name": req.station_name,
        "scheduled_arrival": req.scheduled_arrival,
        "predicted_eta": predicted_eta.isoformat() + "Z",
        "predicted_delay_minutes": round(max(0, predicted_delay), 1)
    }
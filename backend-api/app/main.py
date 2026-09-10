from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.train_routes import router as train_router

app = FastAPI(title="Railway ETA Prediction API", version="1.0.0")
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=False,
	allow_methods=["*"],
	allow_headers=["*"],
)
app.include_router(train_router)


@app.get("/health")
async def health() -> dict[str, str]:
	return {"status": "ok"}


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.modules.utilisateurs.router import router as user_router
from app.modules.plans_wifi.router import router as wifi_router

app = FastAPI(
    title="SpeedConnect API",
    description="API backend du projet SpeedConnect",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router)
app.include_router(wifi_router)

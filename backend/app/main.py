from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routers import auth, plans, users

app = FastAPI(title="AI Study Planner", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(plans.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}

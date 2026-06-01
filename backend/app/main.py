from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routers import agent, auth, documents, plans, users

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
app.include_router(documents.router)
app.include_router(agent.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}

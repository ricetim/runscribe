from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import create_db_and_tables
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    from app.database import Session, engine
    from app.routers.sync import _sync_strava_photos, _sync_coros
    from app.config import STRAVA_REFRESH_TOKEN, COROS_EMAIL
    if STRAVA_REFRESH_TOKEN:
        scheduler.add_job(lambda: _sync_strava_photos(Session(engine)), "interval", hours=6)
    if COROS_EMAIL:
        scheduler.add_job(lambda: _sync_coros(Session(engine)), "interval", hours=6)
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="RunScribe", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


from app.routers import activities, stats, sync, shoes, goals, plans, profile
app.include_router(activities.router)
app.include_router(stats.router)
app.include_router(sync.router)
app.include_router(shoes.router)
app.include_router(goals.router)
app.include_router(plans.router)
app.include_router(profile.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}

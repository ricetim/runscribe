import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.database import create_db_and_tables
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()


def _warm_all_caches():
    """Run in a background thread at startup to pre-populate all TTL caches."""
    from app.database import Session, engine
    from app.routers.activities import warm_cache as warm_activities
    from app.routers.stats import warm_cache as warm_stats
    with Session(engine) as session:
        warm_activities(session)
        warm_stats(session)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    from app.routers.sync import _sync_strava_photos, _sync_coros
    from app.config import STRAVA_REFRESH_TOKEN, COROS_EMAIL
    if STRAVA_REFRESH_TOKEN:
        scheduler.add_job(_sync_strava_photos, "interval", hours=6)
    if COROS_EMAIL:
        scheduler.add_job(_sync_coros, "interval", minutes=30)
    scheduler.start()
    threading.Thread(target=_warm_all_caches, daemon=True).start()
    yield
    scheduler.shutdown()


app = FastAPI(title="RunScribe", lifespan=lifespan)

# GZip first (outermost) so all responses — including CORS preflight — are compressed
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


from app.routers import activities, stats, sync, shoes, goals, plans, profile, tiles
app.include_router(activities.router)
app.include_router(stats.router)
app.include_router(sync.router)
app.include_router(shoes.router)
app.include_router(goals.router)
app.include_router(plans.router)
app.include_router(profile.router)
app.include_router(tiles.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}

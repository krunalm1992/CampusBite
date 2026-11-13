import asyncio
import logging
import time
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import SessionLocal, engine
from app.deps import _user_from_token
from app.seed import seed_if_empty
from app.tasks import reminder_loop
from app.ws import manager

logger = logging.getLogger("campusbite")


def wait_for_database() -> None:
    """Docker starts Postgres and the API together. Retry until the port accepts connections."""
    last_error: Exception | None = None
    for attempt in range(15):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except Exception as exc:  # noqa: BLE001 - startup should report any driver error
            last_error = exc
            logger.warning("Database not ready (%s/15): %s", attempt + 1, exc)
            time.sleep(2)
    raise RuntimeError("Could not connect to the database") from last_error


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # Import models so create_all sees every table.
    import app.models  # noqa: F401
    from app.database import Base

    wait_for_database()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    task = asyncio.create_task(reminder_loop())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


app = FastAPI(title="CampusBite API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request, call_next):
    """Log the method, path, status, and how long the handler took."""
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.exception("%s %s failed after %.1fms", request.method, request.url.path, elapsed_ms)
        raise
    elapsed = time.perf_counter() - started
    logger.info(
        "%s %s -> %s %.1fms",
        request.method,
        request.url.path,
        response.status_code,
        elapsed * 1000,
    )
    response.headers["X-Process-Time"] = f"{elapsed:.4f}"
    return response


from app.routers import admin, ai, auth, menu, orders, owner, restaurants, returns  # noqa: E402

app.include_router(auth.router)
app.include_router(restaurants.router)
app.include_router(menu.router)
app.include_router(orders.router)
app.include_router(returns.router)
app.include_router(ai.router)
app.include_router(owner.router)
app.include_router(admin.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"name": "CampusBite API", "docs": "/docs", "health": "/api/health"}


@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(default="")):
    db = SessionLocal()
    try:
        user = _user_from_token(token, db) if token else None
        user_id = user.id if user else None
    finally:
        db.close()
    if user_id is None:
        await websocket.close(code=4401)
        return
    await manager.connect(user_id, websocket)
    try:
        await websocket.send_json({"type": "connected", "user_id": user_id})
        while True:
            incoming = await websocket.receive_text()
            if incoming == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(user_id, websocket)

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import FRONTEND_DIST_DIR
from .db import get_connection
from .deps import get_session_user, normalize_token, require_admin, require_player
from .schemas import ActUpdateRequest, ChatRequest, LoginRequest, WebSearchRequest
from .seed import init_db
from .services import (
    create_session,
    get_chat_reply,
    get_current_act,
    get_player_bootstrap,
    get_session_payload,
    search_twitter,
    search_web,
    update_current_act,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    connection = get_connection()
    init_db(connection)
    connection.close()
    yield


app = FastAPI(title="月光下的持刀者", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST_DIR / "assets"), name="assets")


@app.get("/api/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/login")
async def login(payload: LoginRequest) -> dict:
    connection = get_connection()
    try:
        return create_session(connection, payload.passkey)
    finally:
        connection.close()


@app.get("/api/session")
async def read_session(user: dict = Depends(get_session_user)) -> dict:
    connection = get_connection()
    try:
        return get_session_payload(connection, user)
    finally:
        connection.close()


@app.post("/api/logout")
async def logout(authorization: str | None = Header(default=None)) -> dict[str, str]:
    token = normalize_token(authorization)
    connection = get_connection()
    try:
        connection.execute("DELETE FROM sessions WHERE token = ?", (token,))
        connection.commit()
        return {"message": "已登出"}
    finally:
        connection.close()


@app.get("/api/player/bootstrap")
async def player_bootstrap(user: dict = Depends(require_player)) -> dict:
    connection = get_connection()
    try:
        return get_player_bootstrap(connection, user["id"])
    finally:
        connection.close()


@app.post("/api/player/search/web")
async def player_web_search(
    payload: WebSearchRequest,
    user: dict = Depends(require_player),
) -> dict:
    del user
    connection = get_connection()
    try:
        return search_web(connection, payload.query)
    finally:
        connection.close()


@app.get("/api/player/search/twitter")
async def player_twitter_search(
    username: str,
    user: dict = Depends(require_player),
) -> dict:
    del user
    connection = get_connection()
    try:
        return search_twitter(connection, username)
    finally:
        connection.close()


@app.post("/api/player/chat")
async def player_chat(payload: ChatRequest, user: dict = Depends(require_player)) -> dict:
    del user
    connection = get_connection()
    try:
        return get_chat_reply(connection, payload.phone, payload.message)
    finally:
        connection.close()


@app.get("/api/admin/status")
async def admin_status(user: dict = Depends(require_admin)) -> dict[str, int]:
    del user
    connection = get_connection()
    try:
        return {"currentAct": get_current_act(connection)}
    finally:
        connection.close()


@app.post("/api/admin/current-act")
async def admin_update_current_act(
    payload: ActUpdateRequest,
    user: dict = Depends(require_admin),
) -> dict:
    del user
    connection = get_connection()
    try:
        return update_current_act(connection, payload.current_act)
    finally:
        connection.close()


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    del full_path
    if not FRONTEND_DIST_DIR.exists():
        return JSONResponse(
            status_code=503,
            content={
                "message": "frontend 尚未 build，請先到 frontend/ 執行 npm install 及 npm run build，或用 npm run dev 啟動開發環境。"
            },
        )
    return FileResponse(FRONTEND_DIST_DIR / "index.html")

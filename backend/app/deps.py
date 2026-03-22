from __future__ import annotations

from typing import Any

from fastapi import Depends, Header, HTTPException

from .db import get_connection


def normalize_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="未登入")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return authorization.strip()


def get_session_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    token = normalize_token(authorization)
    connection = get_connection()
    row = connection.execute(
        """
        SELECT users.id, users.role_name, users.is_admin, users.passkey
        FROM sessions
        JOIN users ON users.id = sessions.user_id
        WHERE sessions.token = ?
        """,
        (token,),
    ).fetchone()
    connection.close()
    if row is None:
        raise HTTPException(status_code=401, detail="登入已失效，請重新登入")
    return dict(row)


def require_player(user: dict[str, Any] = Depends(get_session_user)) -> dict[str, Any]:
    if user["is_admin"]:
        raise HTTPException(status_code=403, detail="管理員不可使用玩家介面")
    return user


def require_admin(user: dict[str, Any] = Depends(get_session_user)) -> dict[str, Any]:
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail="你沒有管理員權限")
    return user

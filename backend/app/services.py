from __future__ import annotations

import secrets
import sqlite3
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from .security import hash_message


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_current_act(connection: sqlite3.Connection) -> int:
    row = connection.execute("SELECT current_act FROM game_state WHERE id = 1").fetchone()
    return int(row["current_act"])


def create_session(connection: sqlite3.Connection, passkey: str) -> dict[str, Any]:
    user = connection.execute(
        "SELECT id, role_name, is_admin FROM users WHERE passkey = ?",
        (passkey.strip(),),
    ).fetchone()
    if user is None:
        raise HTTPException(status_code=401, detail="Passkey 錯誤")

    token = secrets.token_urlsafe(24)
    connection.execute(
        "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
        (token, user["id"], utc_now()),
    )
    connection.commit()
    current_act = get_current_act(connection)

    return {
        "token": token,
        "user": {
            "roleName": user["role_name"],
            "isAdmin": bool(user["is_admin"]),
        },
        "currentAct": current_act,
    }


def get_session_payload(connection: sqlite3.Connection, user: dict[str, Any]) -> dict[str, Any]:
    return {
        "user": {
            "roleName": user["role_name"],
            "isAdmin": bool(user["is_admin"]),
        },
        "currentAct": get_current_act(connection),
    }


def get_player_bootstrap(connection: sqlite3.Connection, user_id: int) -> dict[str, Any]:
    current_act = get_current_act(connection)
    scripts = connection.execute(
        """
        SELECT act, title, content
        FROM scripts
        WHERE user_id = ? AND act <= ?
        ORDER BY act
        """,
        (user_id, current_act),
    ).fetchall()
    contacts = connection.execute(
        "SELECT phone, name, intro FROM chat_contacts ORDER BY phone"
    ).fetchall()
    return {
        "currentAct": current_act,
        "scripts": [dict(row) for row in scripts],
        "contacts": [dict(row) for row in contacts],
    }


def search_web(connection: sqlite3.Connection, query: str) -> dict[str, Any]:
    keywords = [part.strip().lower() for part in query.split() if part.strip()]
    if not keywords:
        raise HTTPException(status_code=400, detail="請輸入 1 至 3 個關鍵字")
    if len(keywords) > 3:
        raise HTTPException(status_code=400, detail="最多只可搜尋 3 個關鍵字")

    current_act = get_current_act(connection)
    clues = connection.execute(
        "SELECT title, url, snippet, keywords FROM web_clues WHERE act <= ? ORDER BY act, id",
        (current_act,),
    ).fetchall()
    results = []
    for clue in clues:
        source_keywords = clue["keywords"].lower().split()
        if any(keyword in source_keywords for keyword in keywords):
            results.append(
                {
                    "title": clue["title"],
                    "url": clue["url"],
                    "snippet": clue["snippet"],
                }
            )
    return {"results": results, "currentAct": current_act}


def search_twitter(connection: sqlite3.Connection, username: str) -> dict[str, Any]:
    normalized = username.strip().lower().removeprefix("@")
    if not normalized:
        raise HTTPException(status_code=400, detail="請輸入使用者名稱")

    current_act = get_current_act(connection)
    rows = connection.execute(
        """
        SELECT username, display_name, content, posted_at, reply_content
        FROM tweets
        WHERE act <= ?
          AND (
            LOWER(username) = ?
            OR LOWER(display_name) = ?
          )
        ORDER BY act, id
        """,
        (current_act, normalized, normalized),
    ).fetchall()
    return {"results": [dict(row) for row in rows], "currentAct": current_act}


def get_chat_reply(connection: sqlite3.Connection, phone: str, message: str) -> dict[str, Any]:
    current_act = get_current_act(connection)
    contact = connection.execute(
        "SELECT id, phone, name FROM chat_contacts WHERE phone = ?",
        (phone.strip(),),
    ).fetchone()
    if contact is None:
        raise HTTPException(status_code=404, detail="找不到這個號碼")

    responses = connection.execute(
        """
        SELECT trigger_keywords, response_text
        FROM chat_responses
        WHERE contact_id = ? AND act <= ?
        ORDER BY act DESC, id DESC
        """,
        (contact["id"], current_act),
    ).fetchall()
    reply = "我唔太清楚。"
    message_hash = hash_message(message)
    normalized_message = message.strip().lower()
    for response in responses:
        triggers = response["trigger_keywords"].split()
        trigger_match = any(trigger.lower() in normalized_message for trigger in triggers)
        if trigger_match or hash_message(" ".join(triggers)) == message_hash:
            reply = response["response_text"]
            break

    return {
        "contact": {"phone": contact["phone"], "name": contact["name"]},
        "reply": reply,
        "currentAct": current_act,
    }


def update_current_act(connection: sqlite3.Connection, current_act: int) -> dict[str, Any]:
    connection.execute(
        "UPDATE game_state SET current_act = ?, updated_at = ? WHERE id = 1",
        (current_act, utc_now()),
    )
    connection.commit()
    return {"message": "幕數更新成功", "currentAct": get_current_act(connection)}

from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.config import DB_PATH
from backend.app.main import app


def main() -> None:
    if Path(DB_PATH).exists():
        Path(DB_PATH).unlink()

    with TestClient(app) as client:
        player_login = client.post("/api/login", json={"passkey": "001"})
        assert player_login.status_code == 200, player_login.text
        player = player_login.json()
        player_headers = {"Authorization": f"Bearer {player['token']}"}

        bootstrap = client.get("/api/player/bootstrap", headers=player_headers)
        assert bootstrap.status_code == 200, bootstrap.text
        assert len(bootstrap.json()["scripts"]) == 1

        web_before = client.post(
            "/api/player/search/web",
            headers=player_headers,
            json={"query": "陳宏 互聯網公司"},
        )
        assert web_before.status_code == 200, web_before.text
        assert len(web_before.json()["results"]) >= 1

        chat = client.post(
            "/api/player/chat",
            headers=player_headers,
            json={"phone": "00169922", "message": "我是23號11點左右在你們店里消費的客人，我好像少付了錢／多付了錢，你能幫我查一下嗎？"},
        )
        assert chat.status_code == 200, chat.text
        assert "支付了200元" in chat.json()["reply"]

        admin_login = client.post("/api/login", json={"passkey": "8888"})
        assert admin_login.status_code == 200, admin_login.text
        admin = admin_login.json()
        admin_headers = {"Authorization": f"Bearer {admin['token']}"}

        status = client.get("/api/admin/status", headers=admin_headers)
        assert status.status_code == 200, status.text
        assert status.json()["currentAct"] == 1

        update = client.post(
            "/api/admin/current-act",
            headers=admin_headers,
            json={"current_act": 2},
        )
        assert update.status_code == 200, update.text
        assert update.json()["currentAct"] == 2

        web_after = client.post(
            "/api/player/search/web",
            headers=player_headers,
            json={"query": "何聽雨 心理醫生"},
        )
        assert web_after.status_code == 200, web_after.text
        assert len(web_after.json()["results"]) >= 1

        twitter = client.get(
            "/api/player/search/twitter",
            headers=player_headers,
            params={"username": "羅思Ross要堅強"},
        )
        assert twitter.status_code == 200, twitter.text
        assert len(twitter.json()["results"]) >= 1

        print("smoke test passed")


if __name__ == "__main__":
    main()

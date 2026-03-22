# 月光下的持刀者

完整前後端專案架構：

- `backend/`: FastAPI API、SQLite、遊戲初始化資料
- `frontend/`: Vue 3 + Vite 前端

正式資料庫只保留：

- `backend/data/moon.db`

此檔會保留你目前已修改的資料內容。

## Backend

```bash
cd backend
python3 -m pip install -r requirements.txt
python3 run.py
```

後端預設跑在 `http://127.0.0.1:8888`

## Frontend

```bash
cd frontend
npm install
npm run dev
```

前端開發站預設跑在 `http://127.0.0.1:5173`，並自動代理 `/api` 到後端。

## Production Build

```bash
cd frontend
npm install
npm run build
```

build 後會產生 `frontend/dist`，FastAPI 會自動把它當成靜態站提供。

## Docker

這個專案已可直接包成單一容器，並保留現有 `moon.db`。

```bash
cd /Users/antoniocham/Desktop/moon
docker compose up --build
```

啟動後站點會在：

- `http://127.0.0.1:8888`

`docker-compose.yml` 會把本機的：

- `backend/data`

掛載到容器內，所以你目前的 `backend/data/moon.db` 不會被 Docker image 覆蓋。

## GitHub

這個專案已整理成可直接初始化 Git repo 並推上 GitHub 的結構。

建議流程：

```bash
cd /Users/antoniocham/Desktop/moon
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```

目前 `.gitignore` 已排除：

- `frontend/node_modules/`
- `frontend/dist/`
- Python 快取檔

但會保留：

- `backend/data/moon.db`

方便你把現有正式資料庫一併保存到 repo。

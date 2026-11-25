# Asset Management System

以 FastAPI、SQLModel、PostgreSQL 和 Redis 建置的資產管理後端 API。系統支援員工資產查詢、資產管理主管資產維護，以及維修申請審核流程。

## 功能特色
 
- **資產管理**:新增、查詢、修改資產,記錄品牌、型號、採購資訊、保固期限、保管人與狀態
- **報修申請**:員工針對資產提出報修申請單
- **主管審核**:資產管理主管核准或拒絕申請單,核准後資產自動轉為「維修中」,並記錄審核人與審核時間
- **狀態流程控管**:工單與資產的狀態轉換有明確規則,不合法的操作會回傳 4xx 錯誤
- **快取**:- 使用 Redis 快取資產與維修申請資料，資料異動時自動清除相關快取
- **權限控管**:【JWT】登入驗證,區分一般員工與資產管理主管
- **自動化測試**:使用 pytest 與 FastAPI TestClient,搭配獨立測試資料庫

## 技術架構

- Python 3.14
- FastAPI / Uvicorn
- SQLModel / PostgreSQL
- Redis / fastapi-cache2
- JWT / pwdlib Argon2
- Docker Compose
- Pytest

## 專案結構

```text
src/
├── main.py              # FastAPI app 與 middleware
├── database.py          # SQLModel 資料庫連線
├── cache.py             # 使用者專屬 Redis Cache Key
├── config.py            # 專案設定
├── models/              # User、Asset、Repair 資料模型
├── routers/             # Auth、User、Asset、Repair 路由
└── test/                # Pytest 測試與測試 fixtures
```

## 環境變數

專案根目錄建立 `.env`：

```dotenv
POSTGRES_USER=myuser
POSTGRES_PASSWORD=mypassword
POSTGRES_DB=asset_management

SECRET_KEY=replace-with-a-long-random-secret
REDIS_URL=redis://redis:6379/0

# 直接在本機執行時可使用，例如：
# DATABASE_URL=postgresql+psycopg://myuser:mypassword@localhost:15432/asset_management
```

Docker Compose 啟動時會將 `DATABASE_URL` 自動設定為容器內部的 PostgreSQL 位址：

```text
postgresql://<POSTGRES_USER>:<POSTGRES_PASSWORD>@db:5432/<POSTGRES_DB>
```

## 使用 Docker Compose 啟動

確認已安裝 Docker Desktop，然後在專案根目錄執行：

```bash
docker compose up --build
```

啟動後可開啟：

- API 文件：http://localhost:8000/docs
- ReDoc：http://localhost:8000/redoc
- PostgreSQL：`localhost:15432`
- Redis：容器內透過 `redis:6379` 存取；Compose 未對主機公開 Redis 埠

停止並移除容器：

```bash
docker compose down
```

保留 PostgreSQL 資料並重新啟動：

```bash
docker compose up --build
```

若要連同資料庫資料一起移除：

```bash
docker compose down -v
```


## 本機啟動

需要 Python 3.14 以上及 PostgreSQL、Redis。

安裝 `uv` 後執行：

```bash
uv sync
uv run uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```

本機模式的 `.env` 應提供可連線的 `DATABASE_URL`、`REDIS_URL` 與 `SECRET_KEY`。

## 身分與驗證

使用者角色：

- `employee`：一般員工
- `asset_manager`：資產管理主管

取得 Token：

```bash
curl -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=123&password=password123"
```

後續請求需在 Header 加入：

```text
Authorization: Bearer <access_token>
```

登出：

```bash
curl -X POST "http://localhost:8000/auth/logout" \
  -H "Authorization: Bearer <access_token>"
```

## 主要 API

### Authentication

| 方法 | 路徑 | 說明 |
|---|---|---|
| POST | `/auth/token` | 使用員工編號與密碼取得 JWT |
| POST | `/auth/logout` | 將目前 JWT 加入 Redis 黑名單 |

### Users

| 方法 | 路徑 | 權限 | 說明 |
|---|---|---|---|
| POST | `/users/register` | Asset Manager | 建立一般員工測試帳號 |
| GET | `/users/me` | 已登入使用者 | 查看自己的帳號資訊 |
| GET | `/users/{user_id}` | 無角色限制 | 查詢指定帳號 |
| PATCH | `/users/{user_id}` | 無角色限制 | 修改指定帳號 |
| DELETE | `/users/{user_id}` | 無角色限制 | 刪除指定帳號 |

### Assets

| 方法 | 路徑 | 權限 | 說明 |
|---|---|---|---|
| GET | `/assets/my` | Employee | 查詢自己的資產 |
| GET | `/assets/my/{asset_id}` | Employee | 查詢自己的指定資產 |
| GET | `/assets/` | Asset Manager | 查詢全部資產 |
| GET | `/assets/by-custodian/{custodian_id}` | Asset Manager | 查詢指定保管人的資產 |
| GET | `/assets/{asset_id}` | Asset Manager | 查詢指定資產 |
| POST | `/assets/` | Asset Manager | 新增資產 |
| PATCH | `/assets/{asset_id}` | Asset Manager | 修改資產 |
| DELETE | `/assets/{asset_id}` | Asset Manager | 將資產設為退役 |

資產狀態：

- `available`
- `in_use`
- `under_maintenance`
- `retired`

### Repair Requests

| 方法 | 路徑 | 權限 | 說明 |
|---|---|---|---|
| POST | `/repair-requests/` | Employee | 建立維修申請 |
| GET | `/repair-requests/my` | Employee | 查詢自己的申請 |
| GET | `/repair-requests/{request_id}` | Employee | 查詢自己的指定申請 |
| PATCH | `/repair-requests/{request_id}` | Employee | 審核前取消申請或修改故障描述 |
| GET | `/repair-requests/` | Asset Manager | 查詢全部申請 |
| GET | `/repair-requests/by-employee/{requester_id}` | Asset Manager | 查詢指定員工申請 |
| GET | `/repair-requests/by-status/{request_status}` | Asset Manager |依狀態查詢申請 |
| PATCH | `/repair-requests/{request_id}/review` | Asset Manager |審核或處理申請 |

維修申請狀態：

- `under_review`
- `approve_and_under_maintenance`
- `rejected`
- `cancelled`
- `completed`

合法維修流程：

```text
under_review -> approve_and_under_maintenance -> completed
under_review -> rejected
under_review -> cancelled
```

核准維修時，資產會進入 `under_maintenance`；維修完成時，資產會恢復為 `in_use`。

## 執行測試

使用記憶體 SQLite 與記憶體快取執行測試：

```bash
uv run pytest
```

執行指定測試檔：

```bash
uv run pytest src/test/test_assets.py
uv run pytest src/test/test_repair.py
uv run pytest src/test/test_user.py
```
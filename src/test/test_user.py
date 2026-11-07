from fastapi.testclient import TestClient
from ..main import app
from ..models.user import UserDB,UserRole
from ..routers.auth import get_password_hash
client = TestClient(app) # 實例化後，就可以用它來發送模擬的 HTTP 請求

# ----------------- Auth 相關測試：正確帳密登入、錯誤密碼登入、無 Token 存取---------------


def test_login_success(client, session): #  Pytest 看到這兩個參數，就會自動去找 conftest.py 裡對應的 fixture

    # 1. 準備:建立測試資料(一張待審核工單)
    # 準備一個測試用員工帳號 (假設 employee_id=123)
    db_user = UserDB(employee_id=123,
        name="Test User",
        department="IT",
        role=UserRole.ASSET_MANAGER,
        hashed_password=get_password_hash("password123"))
    session.add(db_user)
    session.commit()

    # 2. 執行:呼叫 API 使用者登入 (注意 OAuth2 表單的 key 必須是 username)
    response = client.post("/auth/token",data={"username":"123","password":"password123"})
    # 3. 驗證:檢查結果
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password(client, session):
    db_user = UserDB(employee_id=123,
        name="Test User",
        department="IT",
        role=UserRole.ASSET_MANAGER,
        hashed_password=get_password_hash("password123"))
    session.add(db_user)
    session.commit()

    # 2. 執行:呼叫 API 使用者登入
    response = client.post("/auth/token",data={"username":"123","password":"wrong"})
    # 3. 驗證:檢查結果
    assert response.status_code == 401
    data = response.json()
    assert "access_token" not in data
    assert data["detail"] == "Incorrect username or password"

# 權限驗證 (headers)：無 Token 存取時，直接不帶 headers 即可
def test_access_protected_without_token(client):
    # 無 Token 存取需要保護的 API (以註冊/新增為例，沒帶 headers 驗證)
    response = client.post("/users/register",json={
        "name": "New Employee",
        "password": "somepassword"
    })
    assert response.status_code == 401  # 或 403，取決於你的 fastapi 安全性相依設定


# ------- User 相關測試：Employee 不能建立 Manager ----------------
def test_employee_cannot_create_user(client, session):
    db_user = UserDB(employee_id=123,
        name="Test User",
        department="IT",
        role=UserRole.EMPLOYEE,
        hashed_password=get_password_hash("password123"))
    session.add(db_user)
    session.commit()

    # 讓這位 Employee 登入拿到 Token
    login_res = client.post("/auth/token",data={"username":"123","password":"password123"})
    token = login_res.json()["access_token"]
    # token_type = login_res.json()["token_type"]

    # response = client.post("/users/register",headers={"access_token":token,})
    response = client.post("/users/register",json={"name":"ka","department":"IT","password":"123"},headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403






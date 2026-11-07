import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from datetime import date
from ..database import get_session  # 引入你的專案依賴
from ..main import app  # 引入你的 FastAPI app
from ..models.user import UserDB,UserRole
from ..routers.auth import get_password_hash


# 1. 建立一個專門給測試用的記憶體 SQLite 資料庫
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(name="session")
def session_fixture():
    # 每個測試開始前，建立全新資料表
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        yield session
    # 測試結束後，刪除資料表
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    # 覆寫 FastAPI 原本的 get_session，改用上面的測試資料庫 session
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

# --------------- 專門生 Token 的 Fixture ------------------
@pytest.fixture
def employee_token(session,client):
    user_db = UserDB(employee_id=123,
        name="Test User",
        department="IT",
        role=UserRole.EMPLOYEE,
        hashed_password=get_password_hash("password123"))
    session.add(user_db)
    session.commit()
    response = client.post("/auth/token",data={"username":"123","password":"password123"})
    return response.json()["access_token"]

@pytest.fixture
def manager_token(session,client):
    user_db = UserDB(employee_id=202,
        name="Test User",
        department="IT",
        role=UserRole.ASSET_MANAGER,
        hashed_password=get_password_hash("password202"))
    session.add(user_db)
    session.commit()
    response = client.post("/auth/token",data={"username":"202","password":"password202"})
    return response.json()["access_token"]


@pytest.fixture
def sample_asset_data():
    return {
    "name": "Test Laptop",
    "category": "IT",
    "brand": "Dell",
    "model": "Latitude",
    "specifications": "8G",
    "supplier": "Dell Inc",
    "purchase_date": "2026-01-01",
    "purchase_price": 30000.0,
    "warranty_expiry": "2028-01-01",
    "department": "IT",
    }
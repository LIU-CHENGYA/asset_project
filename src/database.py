### Redis → 需要建立與關閉連線，所以通常放在 lifespan
### PostgreSQL → 通常只建立 Engine，真正需要時才開 Session，所以不用放在 lifespan

import os
from dotenv import load_dotenv
from sqlmodel import SQLModel, Session, create_engine

# 載入 .env 檔案
load_dotenv()

engine = create_engine(os.getenv("DATABASE_URL","sqlite:///:memory:"), pool_pre_ping=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# 每個請求一個 session，結束後自動關閉
def get_session():
    with Session(engine) as session:
        yield session


import os
from dotenv import load_dotenv
from sqlmodel import SQLModel, Session, create_engine
from typing import Annotated
from fastapi import Depends

# 載入 .env 檔案
load_dotenv()

engine = create_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# 每個請求一個 session，結束後自動關閉
def get_session():
    with Session(engine) as session:
        yield session


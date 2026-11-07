from fastapi import FastAPI
from .routers import assets,auth,repairs,user
from contextlib import asynccontextmanager
from .database import create_db_and_tables

@asynccontextmanager
async def lifespan(app: FastAPI):
    # FastAPI 啟動時執行
    create_db_and_tables() # create_all() 只會建立不存在的資料表，不會自動幫你修改既有資料表結構
    yield
    # FastAPI 關閉時執行（目前不需要額外操作）

app = FastAPI(
    title="Asset Management System",
    version="1.0.0",
    lifespan=lifespan,
)


app.include_router(user.router)
app.include_router(auth.router)
app.include_router(assets.router)
app.include_router(repairs.router)


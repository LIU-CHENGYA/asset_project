from fastapi import FastAPI,Request
import os
import time
from .routers import assets,auth,repairs,user
from redis import asyncio as aioredis # 注意：快取套件需要使用非同步的 redis
from contextlib import asynccontextmanager
from fastapi_cache import FastAPICache # 類別/快遞總部大腦
from fastapi_cache.backends.redis import RedisBackend # RedisBackend 不是一個獨立的套件，它是 fastapi-cache 套件內部自帶的一個「類別（Class）」，需要把它實例化成為一個物件
from .database import create_db_and_tables

# lifespan（生命週期管理）和 @asynccontextmanager（非同步上下文管理器）
# 是用來管理「應用程式啟動（Startup）」與「應用程式關閉（Shutdown）」

@asynccontextmanager # 是一個 Python 內建的「函式/裝飾器（Decorator）」 ## 它會把函式轉換成所謂的「非同步內容管理器（async context manager）」
async def lifespan(app: FastAPI):
    # FastAPI 啟動時執行
    create_db_and_tables() # create_all() 只會建立不存在的資料表，不會自動幫你修改既有資料表結構
    
    # 1. 建立 Redis 連線
    redis_url = os.environ["REDIS_URL"]
    
    # 2. 建立非同步的 Redis 連線連線客戶端 是專門負責跟 Redis 伺服器打電話的「接線生（通訊窗口）」。
    # decode_responses=True: Redis 回傳的是生硬的二進位字元（Bytes，例如 b'hello'）。設定 True 後，接線生會自動幫你翻譯成一般人看得懂的 Python 字串（String，例如 'hello'），你就不用在程式裡一直寫 .decode() 了。
    redis_client = aioredis.from_url(redis_url, encoding="utf8")
    # 確認 Redis 可以正常連線
    await redis_client.ping()

    # [為了 jwt 黑名單]【新增這行】把 redis_client 存進 app.state，讓其他路由可以透過 Request 取得
    app.state.redis = redis_client

    # 3. 將連線客戶端注入到 fastapi-cache2 中
    # 初始化 FastAPI Cache
    FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache") # 物件/專用的送貨卡車
    print("Redis Cache 初始化成功！")

    # 讓 FastAPI App 開始保持運行，並把 redis_client 帶過去以便後續關閉
    yield
    
    # ================= FastAPI 關閉時執行 =================
    print("正在關閉 Redis 連線...")
    await redis_client.close()


app = FastAPI(
    title="Asset Management System",
    version="1.0.0",
    lifespan=lifespan,
)
# 加在 app = FastAPI() 之後
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = (time.perf_counter() - start_time) * 1000
    response.headers["X-Process-Time"] = f"{process_time:.2f} ms"
    return response

app.include_router(user.router)
app.include_router(auth.router)
app.include_router(assets.router)
app.include_router(repairs.router)


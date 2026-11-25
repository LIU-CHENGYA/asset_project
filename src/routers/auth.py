import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
import uuid
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, status ,Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Session

from ..models import user
from ..database import get_session

def get_redis(request: Request): # request: Request : 目前這次 HTTP 請求的物件
    return request.app.state.redis # 從 FastAPI 全域空間拿出先前存好的 Redis 連線
# -------------------- 基本設定 --------------------
# 載入 .env 檔案
load_dotenv()
# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

router = APIRouter(prefix="/auth", tags=["auth"])

SessionDep = Annotated[Session, Depends(get_session)]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# -------------------- Token Model --------------------
class Token(BaseModel):
    access_token: str # 就是JWT
    token_type: str


class TokenData(BaseModel): # 需要一個類別來接這些解碼後的資料
    employee_id: int # 使用 employee_id 登入


# -------------------- 密碼處理 --------------------

password_hash = PasswordHash.recommended()


DUMMY_HASH = password_hash.hash("dummypassword")

def verify_password(plain_password:str, hashed_password:str) ->bool:
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password:str) -> str:
    return password_hash.hash(password)

# -------------------- 查詢使用者 --------------------
def get_user(session: SessionDep, employee_id: int,):
    return session.get(user.UserDB,employee_id)

# -------------------- 驗證帳號密碼 --------------------
def authenticate_user(session: SessionDep, employee_id: int, password: str):
    db_user = get_user(session, employee_id)
    if not db_user:
        verify_password(password, DUMMY_HASH) # 找不到帳號時，故意做一次假的密碼驗證
        return False
    if not verify_password(password, db_user.hashed_password):
        return False
    return db_user

# -------------------- 建立 JWT --------------------
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()

    # 1. 計算過期時間 (exp)
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    # 2. 加入 exp 與 jti 到 Payload 中 [為了 jwt 黑名單]
    to_encode.update({
        "exp": expire,
        "jti": str(uuid.uuid4())  # 產生唯一的識別碼
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# -------------------- 取得目前登入者 --------------------
## 使用者已經登入，並且在 Request Header 裡帶著 JWT Token 過來時，後端驗證這個 Token，然後找出目前登入的是哪個使用者。
async def get_current_user(session: SessionDep,token: Annotated[str, Depends(oauth2_scheme)],redis = Depends(get_redis)): # 【新增】注入 Redis
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]) #decode是: 解碼 + 驗證
        # 1. 取出 sub (員工編號) 與 jti (Token 唯一 ID)
        sub: str | None = payload.get("sub")
        jti: str = payload.get("jti")

        if sub is None or jti is None:
            raise credentials_exception
        
        # 【新增】檢查 jti 是否在 Redis 黑名單中
        is_blacklisted = await redis.exists(f"blacklist:{jti}")
        if is_blacklisted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token_data = TokenData(employee_id=int(sub))
    except (InvalidTokenError, ValueError, TypeError):
        raise credentials_exception
    db_user = get_user(session, token_data.employee_id)
    if db_user is None:
        raise credentials_exception
    return db_user

# -------------------- 登入 API --------------------
@router.post("/token")
def login_for_access_token(session: SessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],) -> Token:
    # OAuth2 表單欄位名稱是 username，
    # 但這個專案把員工編號當成登入帳號。
    try:
        employee_id = int(form_data.username)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect employee ID or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    db_user = authenticate_user(session, employee_id, form_data.password)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(db_user.employee_id)}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")

# 新增 /logout 登出路由
# [為了 jwt 黑名單]
@router.post("/logout")
async def logout(
    token: Annotated[str, Depends(oauth2_scheme)],
    redis = Depends(get_redis)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        exp = payload.get("exp")
        
        if jti and exp:
            # 計算這張 Token 還剩幾秒過期
            now = datetime.now(timezone.utc).timestamp()
            ttl = int(exp - now)
            
            # 只有在還沒過期時才需要寫入黑名單
            if ttl > 0:
                await redis.set(f"blacklist:{jti}", "revoked", ex=ttl)
                
        return {"message": "Successfully logged out"}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

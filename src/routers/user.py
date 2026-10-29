from typing import Annotated
from fastapi import Depends, APIRouter, HTTPException
from sqlmodel import Session
from ..models import user
from ..database import get_session
# 先定義一組路由，之後再掛到主程式 App 上
router = APIRouter(tags=["user"],prefix="/users",)

# 執行這個 API 時，請先透過 get_session 取得資料庫 Session，再把它傳進函式
SessionDep = Annotated[Session, Depends(get_session)]


# 新增
@router.post("/",response_model=user.UserPublic)
async def create_user(user_in:user.UserCreate,session: SessionDep,):
    # 把 user_in 的資料驗證後，轉換成一個 UserDB 物件。
    user_db = user.UserDB(name = user_in.name,department = user_in.department,role = user.UserRole.EMPLOYEE,hashed_password=hash_password(user_in.password),)
    session.add(user_db)
    session.commit()
    session.refresh(user_db)
    return user_db


# 查詢
@router.get("/{user_id}",response_model=user.UserPublic)
async def get_user(user_id: int,session: SessionDep,):
    user_db = session.get(user.UserDB,user_id)
    if not user_db:
        raise HTTPException(status_code=404, detail="user not found")
    return user_db

# 改
@router.patch("/{user_id}",response_model=user.UserPublic)
async def update_user(user_id:int,user_in:user.UserUpdate,session: SessionDep,):
    user_db = session.get(user.UserDB,user_id)
    if not user_db:
        raise HTTPException(status_code=404, detail="user not found")
    user_data = user_in.model_dump(exclude_unset=True)
    user_db.sqlmodel_update(user_data)
    session.add(user_db)
    session.commit()
    session.refresh(user_db)

    return user_db


# 刪除
@router.delete("/{user_id}")
async def delete_user(user_id:int ,session: SessionDep,):
    user_db = session.get(user.UserDB,user_id)
    if not user_db:
        raise HTTPException(status_code=404, detail="user not found")
    session.delete(user_db)
    session.commit()
    return {"ok": True}

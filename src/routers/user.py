from typing import Annotated
from fastapi import Depends, APIRouter, HTTPException,status
from sqlmodel import Session
from ..models import user
from .auth import get_current_user,get_password_hash
from ..database import get_session
# 先定義一組路由，之後再掛到主程式 App 上
router = APIRouter(tags=["users"],prefix="/users",)

# 執行這個 API 時，請先透過 get_session 取得資料庫 Session，再把它傳進函式
SessionDep = Annotated[Session, Depends(get_session)]
CurrentUser = Annotated[user.UserDB,Depends(get_current_user)]
def get_current_manager(current_user:CurrentUser):
    if current_user.role != user.UserRole.ASSET_MANAGER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only manager can access this endpoint")
    return current_user
ManagerUser = Annotated[ user.UserDB,Depends(get_current_manager)]

## 專案中必要的:
### 新增員工(測試)、登入並取得 JWT(在auth.py檔案中)、查看自己的帳號資訊(已登入使用者)

# 新增 (僅供測試，由專案管理者建立)
@router.post("/register",response_model=user.UserPublic)
def create_user(user_in:user.UserCreate,session: SessionDep,manager_user:ManagerUser,):
    # 把 user_in 的資料驗證後，轉換成一個 UserDB 物件。
    user_db = user.UserDB(name = user_in.name,department = user_in.department,role = user.UserRole.EMPLOYEE,hashed_password=get_password_hash(user_in.password),)
    
    session.add(user_db)
    session.commit()
    session.refresh(user_db)
    return user_db

# 查看自己的帳號資訊[已登入使用者]
@router.get("/me",response_model=user.UserPublic)
def get_me(current_user:CurrentUser):
    return current_user



## ------------- 非必要 --------------- ## 
# 查詢所有員工  (僅供測試，由專案管理者查看)
@router.get("/{user_id}",response_model=user.UserPublic)
def get_user(user_id: int,session: SessionDep,):
    user_db = session.get(user.UserDB,user_id)
    if not user_db:
        raise HTTPException(status_code=404, detail="user not found")
    return user_db

# 改 (僅供測試，由專案管理者查看)
@router.patch("/{user_id}",response_model=user.UserPublic)
def update_user(user_id:int,user_in:user.UserUpdate,session: SessionDep,):
    user_db = session.get(user.UserDB,user_id)
    if not user_db:
        raise HTTPException(status_code=404, detail="user not found")
    user_data = user_in.model_dump(exclude_unset=True)
    user_db.sqlmodel_update(user_data)
    session.add(user_db)
    session.commit()
    session.refresh(user_db)

    return user_db


# 刪除 (僅供測試，由專案管理者查看)
@router.delete("/{user_id}")
def delete_user(user_id:int ,session: SessionDep,):
    user_db = session.get(user.UserDB,user_id)
    if not user_db:
        raise HTTPException(status_code=404, detail="user not found")
    session.delete(user_db)
    session.commit()
    return {"ok": True}

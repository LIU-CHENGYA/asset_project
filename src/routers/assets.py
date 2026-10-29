from typing import Annotated
from fastapi import Depends, APIRouter, HTTPException, status
from sqlmodel import Session,select
from ..models import asset,user
from ..database import get_session
from .auth import get_current_user
# 先定義一組路由，之後再掛到主程式 App 上
router = APIRouter(tags=["asset"],prefix="/assets",)

# 執行這個 API 時，請先透過 get_session 取得資料庫 Session，再把它傳進函式
SessionDep = Annotated[Session, Depends(get_session)]

CurrentUser = Annotated[user.UserDB,Depends(get_current_user)]


# ----------- 員工 --------------------#
## 檢查登入者是否為一般員工
def get_current_employee(current_user:CurrentUser):
    if current_user.role != user.UserRole.EMPLOYEE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only employees can access this endpoint")
    return current_user

EmployeeUser = Annotated[ user.UserDB,Depends(get_current_employee)]

## 員工可以查看自己的所有資產

@router.get("/my",response_model=list[asset.AssetPublic])
def get_my_assets(session: SessionDep,current_user :EmployeeUser ):
    statement = select(asset.AssetDB).where(asset.AssetDB.custodian_id == current_user.employee_id)
    asset_db = session.exec(statement).all()
    return asset_db

## 員工可以查看自己特定的資產
## 問題是 要如何確定這個asset_id 是這個員工的? => where條件?
@router.get("/my/{asset_id}",response_model=asset.AssetPublic)
def get_my_asset(asset_id: int,session: SessionDep,current_user :EmployeeUser ):
    statement = select(asset.AssetDB).where(asset.AssetDB.custodian_id == current_user.employee_id,asset.AssetDB.asset_id==asset_id)
    asset_db = session.exec(statement).first()
    if not asset_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="can't find this asset")
    return asset_db



# ----------- 資產管理者 --------------------#
def get_current_manager(current_user:CurrentUser):
    if current_user.role != user.UserRole.ASSET_MANAGER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only manager can access this endpoint")
    return current_user
ManagerUser = Annotated[ user.UserDB,Depends(get_current_manager)]

## 主管可以查看每一個員工的所有資產

@router.get("/",response_model=list[asset.AssetPublic])
def get_assets(session: SessionDep,current_user :ManagerUser ):
    statement = select(asset.AssetDB).order_by(asset.AssetDB.asset_id)
    asset_db = session.exec(statement).all()
    return asset_db

## 主管可以查看特定員工的所有資產
@router.get("/by-custodian/{custodian_id}",response_model=list[asset.AssetPublic])
def get_employee_asset(custodian_id:int,session: SessionDep,current_user :ManagerUser ):
    statement = select(asset.AssetDB).where(asset.AssetDB.custodian_id==custodian_id).order_by(asset.AssetDB.asset_id)
    asset_db = session.exec(statement).all()
    return asset_db

## 主管可以查看任一asset_id 資產
@router.get("/{asset_id}",response_model=asset.AssetPublic)
def get_by_asset_id(asset_id:int,session: SessionDep,current_user :ManagerUser ):
    statement = select(asset.AssetDB).where(asset.AssetDB.asset_id==asset_id)
    asset_db = session.exec(statement).first()

    if not asset_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="can't find this asset")
    return asset_db



## 主管可以新增資產 =>保管者(一般員工)可加可不加
@router.post("/",response_model=asset.AssetPublic)
def create_asset(asset_in:asset.AssetCreate,session: SessionDep,current_user :ManagerUser,):
    initial_status = asset.Status.AVAILABLE
    
    # 驗證custodian_id
    if asset_in.custodian_id is not None: #有傳入指定保管者
        custodian = session.get(user.UserDB,asset_in.custodian_id)
        if not custodian:
            raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custodian not found",
        )
        if custodian.role != user.UserRole.EMPLOYEE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Custodian must be an employee",
            )
        # 順便改資產的狀態 => 直接這樣指定正確嗎?
        initial_status = asset.Status.IN_USE

    asset_db = asset.AssetDB.model_validate(asset_in) #model_validate是把普通的字典（或資料）驗證並轉成 Pydantic 模型（驗證並吃進去）
    asset_db.status = initial_status

    session.add(asset_db)
    session.commit()
    session.refresh(asset_db) # refresh() 取得資料庫生成的 asset_id。
    return asset_db

## 主管修改資產內容
@router.patch("/{asset_id}",response_model=asset.AssetPublic)
def update_asset(asset_id:int,asset_in:asset.AssetUpdate,session: SessionDep,current_user :ManagerUser,):
    asset_db = session.get(asset.AssetDB,asset_id)
    if not asset_db:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # 取得更新內容
    asset_data = asset_in.model_dump(exclude_unset=True)
    if not asset_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )
    
    # 檢查是否有指定保管者 更換/從無到有 ; 如果原本的狀態是RETIRED,UNDER_MAINTENANCE 不允許變更保管人
    # 如果原本是in_use 解除保管人 -> AVAILABLE, 更換保管人-> IN_USE
    # 如果原本是AVAILABLE 指派保管人 -> IN_USE
    #   
    if "custodian_id" in asset_data:
        new_custodian_id = asset_data["custodian_id"]

        # 不允許退役或維修中的資產變更保管人
        if asset_db.status in {asset.Status.RETIRED,asset.Status.UNDER_MAINTENANCE,}:
            raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot change custodian in the current asset status",
        )
        if new_custodian_id is not None:
            custodian = session.get(
                user.UserDB,
                new_custodian_id,
            )

            if custodian is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Custodian not found",
                )

            if custodian.role != user.UserRole.EMPLOYEE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Custodian must be an employee",
                )

            asset_data["status"] = asset.Status.IN_USE

        else:
            # 解除保管人
            asset_data["status"] = asset.Status.AVAILABLE


    # 檢查: 不允許非custodian_id的欄位被清空，設成nell
    for key,value in asset_data.items():
        if value is None and key != "custodian_id":
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,detail=f"{key} cannot be null",) # 傳入內容違反了商業邏輯
    asset_db.sqlmodel_update(asset_data) # 要更新的欄位字典
    session.add(asset_db)
    session.commit()
    session.refresh(asset_db)

    return asset_db


# 主管刪除特定的資產
@router.delete("/{asset_id}")
def delete_asset(asset_id:int ,session: SessionDep,current_user :ManagerUser,):
    asset_db = session.get(asset.AssetDB,asset_id)
    if not asset_db:
        raise HTTPException(status_code=404, detail="Asset not found")
    asset_db.status = asset.Status.RETIRED

    session.add(asset_db)
    session.commit()
    session.refresh(asset_db)

    return asset_db

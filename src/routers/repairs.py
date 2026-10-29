"""
申請單相關的api
1. 一般員工
    提出申請單  POST   /repair-requests
    查看自己所有的工單 GET  /repair-requests/my
    查看自己特定的工單 GET  /repair-requests/{request_id}
    在尚未審核前可以修改申請單 包含取消申請  PATCH /repair-requests /{request_id} 並且由從登入資訊取得employee_id

2. 管理主管
    查看所有申請單 GET  /repair-requests
    查看特定申請單 GET  /repair-requests/{request_id}
    審核申請單 PATCH /repair-requests/{request_id} => 修改狀態 同意/不同意/維修中 => 紀錄修改資訊
""" 

from typing import Annotated
from fastapi import Depends, APIRouter, HTTPException ,status
from sqlmodel import Session,select

from ..models import repair,user,asset
from ..database import get_session
from .auth import get_current_user
from datetime import datetime ,timezone

router = APIRouter(tags=["repair-requests"],prefix="/repair-requests",)

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

## 員工提出申請單
@router.post("/",response_model=repair.RepairRequestPublic)
def create_repair_requests(request:repair.RepairRequestCreate,session:SessionDep, employee_user : EmployeeUser):
    repair_db = repair.RepairRequestDB(asset_id= request.asset_id,fault_description=request.fault_description,requester_id=employee_user.employee_id)
    session.add(repair_db)
    session.commit()
    session.refresh(repair_db)
    return repair_db

## 員工查看自己所有的工單
@router.get("/my",response_model=list[repair.RepairRequestPublic])
def get_repair_request(session:SessionDep,employee_user : EmployeeUser):
    statement = select(repair.RepairRequestDB).where(repair.RepairRequestDB.requester_id == employee_user.employee_id)
    requests  = session.exec(statement).all()
    # if not requests :
    #     raise HTTPException(status_code=404,detail="repair_request not found")
    #  可以讓她回傳 [ ] 空的list
    return requests 

## 員工查看自己特定的工單
@router.get("/{request_id}",response_model=repair.RepairRequestPublic)
def get_my_repair_request(request_id:int,session:SessionDep,employee_user : EmployeeUser):
    statement = select(repair.RepairRequestDB).where(repair.RepairRequestDB.requester_id == employee_user.employee_id , repair.RepairRequestDB.request_id == request_id)
    requests  = session.exec(statement).first()
    if not requests :
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="repair_request not found")
    return requests 

## 在尚未審核前員工可以修改申請單 包含取消申請 
@router.patch("/{request_id}",response_model=repair.RepairRequestPublic)
def updated_request(request_id:int,request_in:repair.RepairUpdated_Employ,session:SessionDep,employee_user : EmployeeUser):
    statement = select(repair.RepairRequestDB).where(repair.RepairRequestDB.requester_id == employee_user.employee_id ,
                                                repair.RepairRequestDB.request_id == request_id,
                                                repair.RepairRequestDB.status == repair.RepairRequestStatus.UNDER_REVIEW,)
    repair_db  = session.exec(statement).first()
    if repair_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="repair_request not found")
    repair_data = request_in.model_dump(exclude_unset=True)
    # 員工只能取消申請，不能自行核准或開始維修 (也就是只能修改為取消)
    if "status" in repair_data:
        if repair_data["status"] != repair.RepairRequestStatus.CANCELLED:
            raise HTTPException(status_code=status.HTTP_400_FORBIDDEN,detail="Employees can only cancel repair requests")
        
    # 不允許空的 PATCH
    if not repair_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )
    
    repair_db.sqlmodel_update(repair_data)

    session.add(repair_db)
    session.commit()
    session.refresh(repair_db)

    return repair_db


# ----------- 資產管理主管 --------------------#
## 檢查登入者是否為資產管理主管
def get_current_manager(current_user:CurrentUser):
    if current_user.role != user.UserRole.ASSET_MANAGER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only manager can access this endpoint")
    return current_user
ManagerUser = Annotated[ user.UserDB,Depends(get_current_manager)]

## 資產管理主管查看所有員工的申請單
@router.get("/",response_model=list[repair.RepairRequestPublic])
def get_employee_all_request(manager_user:ManagerUser,session: SessionDep):
    statement = select(repair.RepairRequestDB).order_by(repair.RepairRequestDB.request_id)
    requests_db = session.exec(statement).all()

    return requests_db


## 資產管理主管查看特定員工的所有申請單  
@router.get("/by-employee/{requester_id}",response_model=list[repair.RepairRequestPublic],)
def get_requests_by_employee(requester_id:int,manager_user:ManagerUser,session: SessionDep): # 有需要特別處理 manager_user 嗎? => 即使函式內沒有讀取 manager_user，FastAPI 仍會先執行 ManagerUser 的依賴，確認呼叫者的角色是主管。因此，這樣寫就已經有權限檢查。
    statement = select(repair.RepairRequestDB).where(repair.RepairRequestDB.requester_id == requester_id)
    requests_db = session.exec(statement).all()
    return requests_db


## 資產管理主管查看申請單 依工單狀態篩選
@router.get("/by-status/{request_status}",response_model=list[repair.RepairRequestPublic])
def get_requests_by_status(request_status:repair.RepairRequestStatus,manager_user:ManagerUser,session: SessionDep):
    statement = select(repair.RepairRequestDB).where(repair.RepairRequestDB.status == request_status)
    requests_db = session.exec(statement).all()
    return requests_db

## 其他的篩選條件下的 api 要寫嗎?


#  (資料庫允許更新，不代表這次更新在業務規則上合理)
"""
1. 工單必須存在。
2. request_in 不能修改 reviewer_id 或 reviewed_at，這兩個欄位應由後端維護
3. 第一次審核時，應記錄 reviewer_id 和 reviewed_at
4. 只能進行合理的狀態轉換，不能任意把工單改成任何狀態

"""
## 資產管理主管審核申請單
@router.patch("/{request_id}/review",response_model=repair.RepairRequestPublic)
def review_request(request_id:int,request_in: repair.RepairUpdated_Manager,manager_user:ManagerUser,session: SessionDep):

    
    # 1. 取得資料庫中原本的工單 request_db
    request_db = session.get(repair.RepairRequestDB,request_id) 
    if not request_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="request-repair not found")


    # 2. 取得本次要更新的欄位 repair_data
    repair_data = request_in.model_dump(exclude_unset=True) # 把 Pydantic 模型裡的資料轉成字典
    if not repair_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )

    
    # 目前工單狀態
    current_status = request_db.status

    try:    
        # 3.待審核的工單只可以被核准或拒絕 (所以一定要傳入status)
        if current_status ==  repair.RepairRequestStatus.UNDER_REVIEW: # 目前狀態為待審核
            allowed_statuses = {repair.RepairRequestStatus.APPROVED_AND_UNDER_MAINTENANCE,repair.RepairRequestStatus.REJECTED}

            if "status" not in repair_data:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Should include status change")
            if repair_data["status"] not in allowed_statuses:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="A pending request can only be approved or rejected")
            
            # 只有核准開始維修時，才更新資產狀態
            if repair_data["status"] == repair.RepairRequestStatus.APPROVED_AND_UNDER_MAINTENANCE: # 開始維修
                asset_db = session.get(asset.AssetDB,request_db.asset_id)
                if asset_db is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Asset not found",
                    )
                
                if asset_db.status not in {asset.Status.AVAILABLE,asset.Status.IN_USE,}:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Asset cannot enter maintenance in its current status",
                    )
                asset_db.status = asset.Status.UNDER_MAINTENANCE
                session.add(asset_db)

            # 紀錄登記主管與審查時間
            repair_data["reviewed_at"] = datetime.now(timezone.utc)
            repair_data["reviewer_id"] = manager_user.employee_id

        #  4. 維修中的工單只能轉為完成
        elif current_status == repair.RepairRequestStatus.APPROVED_AND_UNDER_MAINTENANCE: 
            if repair_data.get("status") != repair.RepairRequestStatus.COMPLETED:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="A maintenance request can only be completed")
            repair_data["completed_at"] = datetime.now(timezone.utc)

        # 5. 已拒絕的工單只能補充維修說明
        elif current_status == repair.RepairRequestStatus.REJECTED: #如果為拒絕可以填上 "repair_solution" : 直接檢查更新欄位
            allowed_fields = {"repair_solution"}
            if not set(repair_data.keys()).issubset(allowed_fields):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="A rejected request can only update repair_solution")
            
        else : #已取消或已完成的工單不能再修改
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="This request cannot be updated in its current status")

        # 6. 更新工單
        request_db.sqlmodel_update(repair_data)
        session.add(request_db)

        # 7. 工單與資產一起提交
        session.commit()
        session.refresh(request_db)
        return request_db
    
    except Exception:
        session.rollback()
        raise # 把剛才捕捉到的例外原封不動再丟出去



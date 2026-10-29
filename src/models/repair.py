import enum
import datetime
from sqlmodel import Field, SQLModel
"""
RepairRequest申請單
  request_id — PK 申請單編號
  asset_id — FK
  requester_id — FK 申請人編號
  reviewer_id — FK，允許為空 審查人編號
  status (等待審查中 / 同意 / 不同意 / 維修中/ 完成 )
  requested_at 申請日期
  reviewed_at 審查日期
  repair_solution：維修處理方式或結果。
  fault_description 故障描述 (申請者自己要填寫)
  repair_date
  repair_cost
  vendor_technician
"""
class RepairRequestStatus(str, enum.Enum):
    CANCELLED = "cancelled"
    UNDER_REVIEW = "under_review"
    APPROVED_AND_UNDER_MAINTENANCE = "approve_and_under_maintenance"
    REJECTED = "rejected"
    COMPLETED = "completed"
"""
可能的三條路徑:
    UNDER_REVIEW → APPROVED_and_UNDER_MAINTENANCE → COMPLETED     資產管理主管
    UNDER_REVIEW → REJECTED     資產管理主管
    UNDER_REVIEW → CANCELLED    一般員工

"""


class RepairRequestBase(SQLModel):
    requested_at :datetime.datetime  = Field( default_factory=datetime.datetime.now ) # 程式會在建立物件的那一瞬間去記錄當前時間。
    reviewed_at :datetime.datetime  | None = None
    completed_at: datetime.datetime  | None = None
    repair_solution:str | None = None # 主管審核填寫內容
    fault_description :str  # 故障描述是一般員工建立維修申請的必要資訊，因此設為必填
    repair_cost :float | None = None
    vendor_technician :str | None = None


class RepairRequestDB(RepairRequestBase,table = True):
    __tablename__ = "repair_request"

    request_id : int | None = Field(default=None, primary_key=True)

    asset_id :int = Field(foreign_key="assets.asset_id")
    requester_id:int = Field(foreign_key="employees.employee_id") # 申請人編號
    reviewer_id : int | None = Field(default=None,foreign_key="employees.employee_id")  # 審查人編號 可為空
    status: RepairRequestStatus = RepairRequestStatus.UNDER_REVIEW

class RepairRequestPublic(RepairRequestBase):
    request_id : int 
    status:RepairRequestStatus
    asset_id :int 
    requester_id:int # 申請人編號
    reviewer_id : int | None = None # 審查人編號 可為空


class RepairRequestCreate(SQLModel): # 前端建立申請單時提供的資料
    asset_id: int
    fault_description: str
    # 其餘欄位其實系統都能自己決定

class RepairUpdated_Employ(SQLModel): # 給一般員工修改申請單
    status: RepairRequestStatus  | None = None# 這邊是直接讓他便取消嗎? => Router 限制： status 如果有提供，就只能是 CANCELLED
    fault_description :str | None = None
    # asset_id 應該是不能換? 不能

class RepairUpdated_Manager(SQLModel): # 給維修審查人員／資產管理人員使用
    status: RepairRequestStatus | None =None
    repair_solution:str | None =None
    repair_cost :float | None =None 
    vendor_technician :str | None =None
    

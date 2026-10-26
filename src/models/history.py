import enum
import datetime
from sqlmodel import Field, SQLModel
"""
AssetHistory
 	history_id — PK
 	asset_id — FK
 	event_type
 	event_date
 	department
 	custodian_id — FK 
 	description
 	request_id — FK 可為null
"""


class AssetHistoryBase(SQLModel):
    event_type : str
    event_date :datetime.date = Field(default_factory=datetime.datetime.now)
    department : str
    description :str


class AssetHistoryDB(AssetHistoryBase,table=True):
    __tablename__ = "asset_history"
    history_id: int | None = Field(default=None,primary_key=True)

    asset_id: int = Field(foreign_key="assets.asset_id")
    custodian_id : int | None  = Field(default=None,foreign_key="employees.employee_id")  # 有些資產可能尚未分配保管人
    request_id  : int = Field(foreign_key="repair_request.request_id") # 為何這個可以為空值?


class AssetHistoryPublic(AssetHistoryBase):
    history_id :int
    asset_id :int
    custodian_id :int | None = None
    request_id : int| None = None

class AssetHistoryUpdate(SQLModel):
    event_type : str | None =None
    department : str | None =None
    custodian_id: int | None = None
    description :str | None =None

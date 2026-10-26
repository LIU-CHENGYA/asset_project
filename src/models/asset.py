import enum
import datetime
from sqlmodel import Field, SQLModel
"""
Asset
	asset_id — PK
	name
	category
	brand
	model
	specifications
	supplier
	purchase_date
	purchase_price
	warranty_expiry
	department (資產所屬部門)
	custodian_id — FK (資產的保管人編號)
	status
"""
class Status(str, enum.Enum):
    AVAILABLE = "available"
    IN_USE = "in_use"
    UNDER_MAINTENANCE = "under_maintenance"
    RETIRED = "retired"

class AssetBase(SQLModel):
    name :str
    category :str
    brand : str
    model :str
    specifications :str
    supplier :str
    purchase_date : datetime.date
    purchase_price : float
    warranty_expiry:datetime.date
    department : str
    status : Status

class AssetDb(AssetBase,table = True):
    __tablename__ = "assets"

    asset_id : int | None = Field(default=None, primary_key=True)
    custodian_id : int | None = Field(default=None, foreign_key="employees.employee_id")


class AssetPublic(AssetBase):
    asset_id : int  
    custodian_id : int | None = None

class AssetUpdate(SQLModel):
    name :str | None =None
    category :str | None =None
    brand : str | None =None
    model :str | None =None
    specifications :str | None =None
    supplier :str | None =None
    purchase_date : datetime.date | None =None
    purchase_price : float  | None =None
    warranty_expiry:datetime.date | None =None
    department : str | None =None
    status : Status | None =None
    custodian_id: int | None = None


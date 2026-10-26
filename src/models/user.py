import enum
from sqlmodel import Field, SQLModel
"""
Employee
employee_id — PK
name
department
role (employee / asset_manager)

"""
class UserRole(str, enum.Enum):
    EMPLOYEE = "employee"
    ASSET_MANAGER = "asset_manager"



class UserBase(SQLModel): #最基礎的
    name: str 
    department: str 
    role: UserRole 

class UserDB(UserBase,table=True): #資料庫版本
    __tablename__ = "employees"
    
    employee_id : int | None = Field(default=None, primary_key=True)
    hashed_password : str 


class UserCreate(SQLModel): 
    name: str 
    department: str 
    password: str


class UserPublic(UserBase): #返還給前端
    employee_id : int 

class UserUpdate(SQLModel): 
    name: str | None =None
    department: str | None  =None

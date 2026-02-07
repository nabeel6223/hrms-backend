from datetime import date
from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel, EmailStr
from pydantic.generics import GenericModel

T = TypeVar("T")
class AttendanceBase(BaseModel):
    date: date
    status: str  # present | absent


class AttendanceCreate(AttendanceBase):
    pass


class AttendanceResponse(AttendanceBase):
    class Config:
        from_attributes = True

class EmployeeResponse(BaseModel):
    id: int
    employee_code: str
    name: str
    email: str
    department: str | None
    position: str | None

    class Config:
        orm_mode = True

class ApiResponse(GenericModel, Generic[T]):
    error: bool = False
    data: T        

class EmployeeCreate(BaseModel):
    employee_code: str
    name: str
    email: EmailStr
    department: Optional[str] = None
    position: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    error: bool
    message: str
    token: str | None = None

from fastapi import FastAPI, Depends, HTTPException, status, Request, Query,Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc,func, case
from typing import List
from datetime import date, timedelta
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException as FastAPIHTTPException
# from jose import jwt

from src.utils.database import SessionLocal, engine
from src.models import Base,Employee, Attendance
import src.crud, src.schemas
from src.schemas import EmployeeResponse,ApiResponse,AttendanceResponse, EmployeeCreate, LoginResponse, LoginRequest
# from src.deps import get_db
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Attendance Management API",root_path="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://hrms-frontend1.netlify.app/",   # React (CRA)
        "http://localhost:5173",   # React (Vite)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    try:
        with engine.connect():
            print("✅ db connected")
    except Exception as e:
        print("❌ db connection failed:", e)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/employees", response_model=ApiResponse[List[EmployeeResponse]])
def get_employees(db: Session = Depends(get_db)):
    try:
        employees = db.query(Employee).filter(Employee.status == 1).order_by(desc(Employee.id)).all()
        print(employees)
        return {
            "error": False,
            "data": employees
        }
    except:
        return {
            "error": True,
            "message": "Failed to fetch employees"
        }


@app.get("/attendance/summary")
def attendance_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
):
    records = (
        db.query(
            Employee.id.label("id"),
            Employee.employee_code.label("employee_code"),
            Employee.name.label("name"),
            func.sum(
                case((Attendance.status == "present", 1), else_=0)
            ).label("present"),
            func.sum(
                case((Attendance.status == "absent", 1), else_=0)
            ).label("absent"),
        )
        .join(Attendance, Attendance.employee_id == Employee.id)
        .filter(
            Attendance.date.between(start_date, end_date),
            Employee.status == 1,
        )
        .group_by(Employee.id)
        .order_by(Employee.name.asc())
        .all()
    )

    data = [
        {
            "id": r.id,
            "employee_code": r.employee_code,
            "name": r.name,
            "present": int(r.present),
            "absent": int(r.absent),
        }
        for r in records
    ]

    return {
        "error": False,
        "data": data,
    }

# 🔹 Get employee monthly attendance
@app.get(
    "/attendance/{employee_id}",
    response_model=ApiResponse[List[AttendanceResponse]]
)
def get_attendance(
    employee_id: int,
    year: int,
    month: int,
    db: Session = Depends(get_db),
):
    return src.crud.get_monthly_attendance(db, employee_id, year, month)


# 🔹 Mark / Update attendance (used by Edit modal)
@app.post(
    "/attendance/{employee_id}",
    response_model=src.schemas.AttendanceResponse
)
def mark_attendance(
    employee_id: int,
    payload: src.schemas.AttendanceCreate,
    db: Session = Depends(get_db),
):
    if payload.status not in ["present", "absent"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    return src.crud.upsert_attendance(
        db,
        employee_id=employee_id,
        date_value=payload.date,
        status=payload.status,
    )


@app.post(
    "/employee",
    response_model=ApiResponse[EmployeeResponse],
    status_code=status.HTTP_201_CREATED,
)
def add_employee(payload: EmployeeCreate, db: Session = Depends(get_db)):
    # check duplicate email or code
    print(EmployeeCreate)
    exists = (
        db.query(Employee)
        .filter(
            (Employee.email == payload.email)
            | (Employee.employee_code == payload.employee_code)
        )
        .first()
    )

    if exists:
        raise HTTPException(
            status_code=400,
            detail="Employee with same email or code already exists",
        )

    employee = Employee(
        employee_code=payload.employee_code,
        name=payload.name,
        email=payload.email,
        department=payload.department,
        position=payload.position,
        # password=payload.password,  # hash later if needed
    )

    db.add(employee)
    db.commit()
    db.refresh(employee)

    return {
        "error": False,
        "data": employee,
    }

@app.exception_handler(FastAPIHTTPException)
async def custom_http_exception_handler(request: Request, exc: FastAPIHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail if isinstance(exc.detail, str) else exc.detail.get("message"),
            "data": None,
        },
    )

@app.delete(
    "/employee/{employee_id}",
    response_model=ApiResponse[None],
)
def delete_employee(employee_id: int, db: Session = Depends(get_db)):
    employee = (
        db.query(Employee)
        .filter(Employee.id == employee_id, Employee.status == 1)
        .first()
    )

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    employee.status = 0
    db.commit()

    return {
        "error": False,
        "data": None
    }


@app.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest = Body(...)):

    try:
        email = payload.email
        password = payload.password

        # simple hardcoded check
        print(password)
        if not (email == "admin@hrms.com" and password == "Admin@123"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email or Password is incorrect!"
            )

        # create token
        # token_data = {
        #     "id": 1,
        #     "email": email,
        #     "exp": date.utcnow() + timedelta(seconds=24*60*60*1000)
        # }

        # token = jwt.encode(token_data, 'SECRET_KEY', algorithm="HS256")

        return {
            "error": False,
            "message": "Logged in!",
            "token": 'token'
        }

    except HTTPException as e:
        print(e)
        # propagate HTTP errors
        raise e
    except Exception:
        return {
            "error": True,
            "message": "Failed to login. Please try again.",
            "token": None
        }


# Root endpoint
@app.get("/")
def root():
    return {"message": "HRMS API Running"}

# --------------------
# Run with uvicorn
if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.environ.get("PORT", 9090))  # Render sets this automatically
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
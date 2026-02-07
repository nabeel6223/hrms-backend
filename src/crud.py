from sqlalchemy.orm import Session
from src.models import Attendance
from datetime import date

def get_monthly_attendance(
    db: Session,
    employee_id: int,
    year: int,
    month: int,
):
    try:
        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1)
        else:
            end = date(year, month + 1, 1)
        attendance = db.query(Attendance).filter(
                Attendance.employee_id == employee_id,
                Attendance.date >= start,
                Attendance.date < end
            ).all()
        return {
            "error": False,
            "data": attendance
        }
    except:
        return {
            "error": True,
            "message": "Failed to fetch attendance"
        }



def upsert_attendance(
    db: Session,
    employee_id: int,
    date_value: date,
    status: str
):
    record = (
        db.query(Attendance)
        .filter(
            Attendance.employee_id == employee_id,
            Attendance.date == date_value
        )
        .first()
    )

    if record:
        record.status = status
    else:
        record = Attendance(
            employee_id=employee_id,
            date=date_value,
            status=status
        )
        db.add(record)

    db.commit()
    db.refresh(record)
    return record

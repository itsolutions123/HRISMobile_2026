from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from .database import engine, Base, SessionLocal
from .models import JobCategory, JobSubItem, Employee, PunchLog
from .routers import auth, punch, jobs

Base.metadata.create_all(bind=engine)

app = FastAPI(title="HRIS DTR Backend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(punch.router)
app.include_router(jobs.router)

@app.on_event("startup")
def seed_initial_data():
    db = SessionLocal()
    try:
        existing_user = db.query(Employee).filter(Employee.employee_id == "3286").first()
        if not existing_user:
            test_user = Employee(
                employee_id="3286",
                name="Jaypee Balonzo",
                first_name="Jaypee",
                last_name="Balonzo",
                position="IT System Administrator",
                department="Admin",
                password_hash="bigtime@123",
                mobile_phone="+63 998 940 0957",
                email="itsupport.associate@bigtimeempire.com",
                role="Admin"
            )
            db.add(test_user)
            db.commit()

        if db.query(JobCategory).count() == 0:
            default_cat = JobCategory(name="HO IT", code="HO-IT", description="Head Office IT Department")
            db.add(default_cat)
            db.commit()
            db.refresh(default_cat)

            roles = ['IT Assistant', 'System Administrator', 'IT Head', 'Technical Support Specialist']
            for role in roles:
                db.add(JobSubItem(category_id=default_cat.id, name=role))
            db.commit()
    except Exception as e:
        print(f"Startup Seeding Exception: {e}")
    finally:
        db.close()

@app.get("/")
def health_check():
    return {"status": "online", "service": "HRIS Backend", "admin_panel": "/admin"}

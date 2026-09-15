from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from ..database import get_db
from ..models import JobCategory, JobSubItem

router = APIRouter(prefix="/api/jobs", tags=["Jobs Management"])

# Schemas
class SubItemCreate(BaseModel):
    name: str
    code: Optional[str] = None

class JobCategoryCreate(BaseModel):
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    sub_items: Optional[List[SubItemCreate]] = []

@router.get("")
def get_all_jobs(db: Session = Depends(get_db)):
    categories = db.query(JobCategory).all()
    result = []
    for cat in categories:
        subs = db.query(JobSubItem).filter(JobSubItem.category_id == cat.id).all()
        result.append({
            "id": cat.id,
            "name": cat.name,
            "code": cat.code,
            "description": cat.description,
            "sub_items": [{"id": s.id, "name": s.name, "code": s.code} for s in subs]
        })
    return result

@router.post("")
def create_job_category(payload: JobCategoryCreate, db: Session = Depends(get_db)):
    cat = db.query(JobCategory).filter(JobCategory.name == payload.name).first()
    
    if not cat:
        cat = JobCategory(name=payload.name, code=payload.code, description=payload.description)
        db.add(cat)
        db.commit()
        db.refresh(cat)

    if payload.sub_items:
        for sub in payload.sub_items:
            existing_sub = db.query(JobSubItem).filter(
                JobSubItem.category_id == cat.id,
                JobSubItem.name == sub.name
            ).first()
            if not existing_sub:
                db_sub = JobSubItem(category_id=cat.id, name=sub.name, code=sub.code)
                db.add(db_sub)
        db.commit()

    return {"status": "success", "category_id": cat.id}

@router.delete("/{category_id}")
def delete_job_category(category_id: int, db: Session = Depends(get_db)):
    cat = db.query(JobCategory).filter(JobCategory.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Job category not found")
    db.delete(cat)
    db.commit()
    return {"status": "success", "message": "Category deleted"}

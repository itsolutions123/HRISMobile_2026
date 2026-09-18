from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from ..database import get_db
from ..models import JobCategory, JobSubItem, BrandLocation, SmartGroup, Employee
from .auth import get_current_user

router = APIRouter(prefix="/api/jobs", tags=["Jobs & Smart Groups Management"])

# Schemas
class SubItemCreate(BaseModel):
    name: str
    code: Optional[str] = None

class JobCategoryCreate(BaseModel):
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    sub_items: Optional[List[SubItemCreate]] = []

class BrandCreate(BaseModel):
    name: str

class GroupCreate(BaseModel):
    name: str
    brand_name: Optional[str] = "Head Office"
    creator: Optional[str] = "Super Admin"

class GroupRename(BaseModel):
    new_name: str

# 1. LEGACY JOB CATEGORIES & SUB-ITEMS
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

# 2. BRAND LOCATIONS
@router.get("/brands")
def get_brands(db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    brands = db.query(BrandLocation).all()
    if not brands:
        default_brands = ["Head Office", "Stores", "Commissary"]
        for b in default_brands:
            db.add(BrandLocation(name=b))
        db.commit()
        brands = db.query(BrandLocation).all()
    return [b.name for b in brands]

@router.post("/brands")
def create_brand(payload: BrandCreate, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    if current_user.role not in ["Admin", "Superadmin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    existing = db.query(BrandLocation).filter(BrandLocation.name == payload.name).first()
    if existing:
        return {"status": "exists", "name": existing.name}
    brand = BrandLocation(name=payload.name)
    db.add(brand)
    db.commit()
    return {"status": "success", "name": brand.name}

@router.put("/brands/{old_name}")
def rename_brand(old_name: str, payload: BrandCreate, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    if current_user.role not in ["Admin", "Superadmin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    brand = db.query(BrandLocation).filter(BrandLocation.name == old_name).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    brand.name = payload.name
    db.commit()
    return {"status": "success", "new_name": payload.name}

@router.delete("/brands/{brand_name}")
def delete_brand(brand_name: str, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    if current_user.role not in ["Admin", "Superadmin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    brand = db.query(BrandLocation).filter(BrandLocation.name == brand_name).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    # Delete associated groups
    db.query(SmartGroup).filter(SmartGroup.brand_id == brand.id).delete()
    db.delete(brand)
    db.commit()
    return {"status": "success", "message": f"Brand {brand_name} deleted"}

# 3. SMART GROUPS
@router.get("/groups")
def get_smart_groups(brand: Optional[str] = None, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    query = db.query(SmartGroup)
    if brand and brand != "ALL":
        brand_obj = db.query(BrandLocation).filter(BrandLocation.name == brand).first()
        if brand_obj:
            query = query.filter(SmartGroup.brand_id == brand_obj.id)
        else:
            return []

    groups = query.all()
    if not groups and (not brand or brand == "ALL"):
        # Default seeding if empty
        ho = db.query(BrandLocation).filter(BrandLocation.name == "Head Office").first()
        ho_id = ho.id if ho else None
        default_groups = [
            {"name": "HO - IT", "dept": "IT", "brand_id": ho_id},
            {"name": "HO - Marketing", "dept": "Marketing", "brand_id": ho_id},
            {"name": "HO - Admin", "dept": "Admin", "brand_id": ho_id},
            {"name": "HO - Human Resource", "dept": "HR", "brand_id": ho_id},
            {"name": "HO - Accounting", "dept": "Accounting", "brand_id": ho_id},
            {"name": "HO - Sales", "dept": "Sales", "brand_id": ho_id}
        ]
        for g in default_groups:
            db.add(SmartGroup(name=g["name"], dept=g["dept"], brand_id=g["brand_id"], creator="Super Admin"))
        db.commit()
        groups = db.query(SmartGroup).all()

    result = []
    for g in groups:
        b_name = "Head Office"
        if g.brand_id:
            b_obj = db.query(BrandLocation).filter(BrandLocation.id == g.brand_id).first()
            if b_obj:
                b_name = b_obj.name
        result.append({
            "id": g.id,
            "name": g.name,
            "dept": g.dept or g.name.replace("HO - ", ""),
            "brand": b_name,
            "creator": g.creator,
            "selected": g.selected
        })
    return result

@router.post("/groups")
def create_smart_group(payload: GroupCreate, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    if current_user.role not in ["Admin", "Superadmin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    brand_obj = db.query(BrandLocation).filter(BrandLocation.name == payload.brand_name).first()
    b_id = brand_obj.id if brand_obj else None

    existing = db.query(SmartGroup).filter(SmartGroup.name == payload.name).first()
    if existing:
        return {"status": "exists", "id": existing.id}

    group = SmartGroup(
        name=payload.name,
        dept=payload.name.replace("HO - ", ""),
        brand_id=b_id,
        creator=current_user.name or "Super Admin"
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return {"status": "success", "id": group.id, "name": group.name}

@router.put("/groups/{group_name}")
def rename_smart_group(group_name: str, payload: GroupRename, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    if current_user.role not in ["Admin", "Superadmin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    group = db.query(SmartGroup).filter(SmartGroup.name == group_name).first()
    if not group:
        raise HTTPException(status_code=404, detail="Smart group not found")
    
    group.name = payload.new_name
    group.dept = payload.new_name.replace("HO - ", "")
    db.commit()
    return {"status": "success", "new_name": payload.new_name}

@router.delete("/groups/{group_name}")
def delete_smart_group(group_name: str, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    if current_user.role not in ["Admin", "Superadmin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    group = db.query(SmartGroup).filter(SmartGroup.name == group_name).first()
    if not group:
        raise HTTPException(status_code=404, detail="Smart group not found")
    
    db.delete(group)
    db.commit()
    return {"status": "success", "message": f"Group '{group_name}' removed"}

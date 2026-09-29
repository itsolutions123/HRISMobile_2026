from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import json

from ..database import SessionLocal
from ..models import FormCategory, CustomForm, FormSubmission, Employee
from .auth import get_current_user

router = APIRouter(prefix="/api/forms", tags=["Forms"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic Schemas
class FormCategoryCreate(BaseModel):
    name: str

class CustomFormCreate(BaseModel):
    category: str
    name: str
    assigned_groups: Optional[List[str]] = []
    assignment_type: Optional[str] = "Dynamic"
    schema_fields: Optional[List[dict]] = None

class CustomFormUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    assigned_groups: Optional[List[str]] = None
    assignment_type: Optional[str] = None
    schema_fields: Optional[List[dict]] = None
    is_archived: Optional[bool] = None

class FormSubmissionCreate(BaseModel):
    smart_group: Optional[str] = None


# CATEGORY ENDPOINTS
@router.get("/categories")
def list_categories(is_archived: bool = False, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    categories = db.query(FormCategory).filter(FormCategory.is_archived == is_archived).all()
    return [{"id": c.id, "name": c.name, "isArchived": c.is_archived} for c in categories]

@router.post("/categories")
def create_category(cat: FormCategoryCreate, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    if current_user.role not in ["Admin", "Superadmin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    existing = db.query(FormCategory).filter(FormCategory.name == cat.name).first()
    if existing:
        if existing.is_archived:
            existing.is_archived = False
            db.commit()
            return {"id": existing.id, "name": existing.name, "isArchived": False}
        raise HTTPException(status_code=400, detail="Category already exists")
    new_cat = FormCategory(name=cat.name, is_archived=False)
    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)
    return {"id": new_cat.id, "name": new_cat.name, "isArchived": False}

@router.put("/categories/{cat_id}")
def update_category(cat_id: int, cat: FormCategoryCreate, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    if current_user.role not in ["Admin", "Superadmin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    category = db.query(FormCategory).filter(FormCategory.id == cat_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    category.name = cat.name
    db.commit()
    return {"status": "success", "id": category.id, "name": cat.name}

@router.patch("/categories/{cat_id}/archive")
def archive_category(cat_id: int, is_archived: bool = True, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    if current_user.role not in ["Admin", "Superadmin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    category = db.query(FormCategory).filter(FormCategory.id == cat_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    category.is_archived = is_archived
    db.commit()
    return {"status": "success", "id": category.id, "isArchived": is_archived}

@router.delete("/categories/{cat_id}")
def delete_category(cat_id: int, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    if current_user.role not in ["Admin", "Superadmin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    category = db.query(FormCategory).filter(FormCategory.id == cat_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    forms = db.query(CustomForm).filter(CustomForm.category_id == category.id).all()
    for f in forms:
        db.query(FormSubmission).filter(FormSubmission.form_id == f.id).delete()
    db.query(CustomForm).filter(CustomForm.category_id == category.id).delete()
    
    db.delete(category)
    db.commit()
    return {"status": "success", "message": f"Category deleted successfully"}


# CUSTOM FORM ENDPOINTS
@router.get("")
def list_forms(category: Optional[str] = None, is_archived: bool = False, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    query = db.query(CustomForm).filter(CustomForm.is_archived == is_archived)
    if category:
        cat_obj = db.query(FormCategory).filter(FormCategory.name == category).first()
        if cat_obj:
            query = query.filter(CustomForm.category_id == cat_obj.id)
        else:
            return []

    forms = query.all()
    results = []
    total_employees_count = db.query(Employee).count()

    for f in forms:
        submission_count = db.query(FormSubmission).filter(FormSubmission.form_id == f.id).count()
        cat_item = db.query(FormCategory).filter(FormCategory.id == f.category_id).first()
        results.append({
            "id": f.id,
            "category": cat_item.name if cat_item else "General",
            "name": f.name,
            "status": f.status,
            "entries": submission_count,
            "views": 1,
            "assignedGroups": f.assigned_groups.split(",") if f.assigned_groups else ["All users group"],
            "assignmentType": f.assignment_type or "Dynamic",
            "totalAssignees": total_employees_count,
            "createdBy": f.created_by,
            "createdAvatar": f.created_avatar,
            "administratedBy": f.administrated_by,
            "dateCreated": f.date_created,
            "isArchived": f.is_archived,
            "isNew": f.is_new,
            "schema_fields": f.schema_fields or "[]"
        })
    return results

@router.post("")
def create_form(form_in: CustomFormCreate, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    if current_user.role not in ["Admin", "Superadmin"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    cat_obj = db.query(FormCategory).filter(FormCategory.name == form_in.category).first()
    if not cat_obj:
        cat_obj = FormCategory(name=form_in.category, is_archived=False)
        db.add(cat_obj)
        db.commit()
        db.refresh(cat_obj)

    existing_form = db.query(CustomForm).filter(
        CustomForm.category_id == cat_obj.id,
        CustomForm.name.ilike(form_in.name.strip()),
        CustomForm.is_archived == False
    ).first()
    if existing_form:
        raise HTTPException(status_code=400, detail="form name already exist")

    user_name = current_user.name or f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or "Admin"
    user_initials = "".join([n[0] for n in user_name.split() if n]).upper()[:2] if user_name else "SA"

    new_form = CustomForm(
        category_id=cat_obj.id,
        name=form_in.name,
        status="Published",
        assigned_groups=",".join(form_in.assigned_groups) if form_in.assigned_groups else "All users group",
        assignment_type=form_in.assignment_type or "Dynamic",
        created_by=user_name,
        created_avatar=user_initials,
        administrated_by="+1",
        date_created=datetime.now().strftime("%m/%d/%Y"),
        is_archived=False,
        is_new=True,
        schema_fields=json.dumps(form_in.schema_fields) if form_in.schema_fields else "[]"
    )
    db.add(new_form)
    db.commit()
    db.refresh(new_form)
    return {"id": new_form.id, "name": new_form.name, "category": cat_obj.name, "assignmentType": new_form.assignment_type}

@router.get("/{form_id}")
def get_form_detail(form_id: int, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    form_obj = db.query(CustomForm).filter(CustomForm.id == form_id).first()
    if not form_obj:
        raise HTTPException(status_code=404, detail="Form not found")
    cat_item = db.query(FormCategory).filter(FormCategory.id == form_obj.category_id).first()
    total_employees_count = db.query(Employee).count()
    submission_count = db.query(FormSubmission).filter(FormSubmission.form_id == form_obj.id).count()
    
    return {
        "id": form_obj.id,
        "category": cat_item.name if cat_item else "General",
        "name": form_obj.name,
        "status": form_obj.status,
        "entries": submission_count,
        "assigned_groups": form_obj.assigned_groups.split(",") if form_obj.assigned_groups else [],
        "assignment_type": form_obj.assignment_type or "Dynamic",
        "totalAssignees": total_employees_count,
        "createdBy": form_obj.created_by,
        "dateCreated": form_obj.date_created,
        "isArchived": form_obj.is_archived,
        "schema_fields": json.loads(form_obj.schema_fields) if form_obj.schema_fields else []
    }

@router.put("/{form_id}")
def update_form(form_id: int, form_in: CustomFormUpdate, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    if current_user.role not in ["Admin", "Superadmin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    form_obj = db.query(CustomForm).filter(CustomForm.id == form_id).first()
    if not form_obj:
        raise HTTPException(status_code=404, detail="Form not found")

    if form_in.name is not None:
        form_obj.name = form_in.name
    if form_in.status is not None:
        form_obj.status = form_in.status
    if form_in.assigned_groups is not None:
        form_obj.assigned_groups = ",".join(form_in.assigned_groups)
    if form_in.assignment_type is not None:
        form_obj.assignment_type = form_in.assignment_type
    if form_in.schema_fields is not None:
        form_obj.schema_fields = json.dumps(form_in.schema_fields)
    if form_in.is_archived is not None:
        form_obj.is_archived = form_in.is_archived

    db.commit()
    return {"status": "success"}

@router.delete("/{form_id}")
def delete_form(form_id: int, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    if current_user.role not in ["Admin", "Superadmin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    form_obj = db.query(CustomForm).filter(CustomForm.id == form_id).first()
    if not form_obj:
        raise HTTPException(status_code=404, detail="Form not found")

    db.query(FormSubmission).filter(FormSubmission.form_id == form_id).delete()
    db.delete(form_obj)
    db.commit()
    return {"status": "success"}

@router.post("/{form_id}/duplicate")
def duplicate_form(form_id: int, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    if current_user.role not in ["Admin", "Superadmin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    form_obj = db.query(CustomForm).filter(CustomForm.id == form_id).first()
    if not form_obj:
        raise HTTPException(status_code=404, detail="Form not found")

    new_form = CustomForm(
        category_id=form_obj.category_id,
        name=f"{form_obj.name} (Copy)",
        status=form_obj.status,
        assigned_groups=form_obj.assigned_groups,
        assignment_type=form_obj.assignment_type,
        created_by=form_obj.created_by,
        created_avatar=form_obj.created_avatar,
        administrated_by=form_obj.administrated_by,
        date_created=datetime.now().strftime("%m/%d/%Y"),
        is_archived=False,
        is_new=True,
        schema_fields=form_obj.schema_fields
    )
    db.add(new_form)
    db.commit()
    db.refresh(new_form)
    return {"id": new_form.id, "name": new_form.name}


# FORM SUBMISSIONS
@router.get("/{form_id}/submissions")
def list_submissions(form_id: int, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    submissions = db.query(FormSubmission).filter(FormSubmission.form_id == form_id).all()
    return [
        {
            "id": s.id,
            "submittedBy": s.submitted_by,
            "dateTime": s.created_at.strftime("%m/%d/%Y, %I:%M %p") if s.created_at else "",
            "smartGroup": s.smart_group or "HO - I.T.",
            "status": s.status
        }
        for s in submissions
    ]

@router.post("/{form_id}/submissions")
def create_submission(form_id: int, sub_in: FormSubmissionCreate, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    user_name = current_user.name or f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or "Employee"
    submission = FormSubmission(
        form_id=form_id,
        submitted_by=user_name,
        smart_group=sub_in.smart_group or current_user.department or "HO - I.T.",
        status="Submitted"
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return {"status": "success", "id": submission.id}


# USER SIGNATURE ENDPOINTS
class SignaturePayload(BaseModel):
    signature: str

@router.get("/signatures/my-signature")
def get_my_signature(db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    return {"signature": current_user.saved_signature or ""}

@router.post("/signatures/my-signature")
def save_my_signature(payload: SignaturePayload, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    current_user.saved_signature = payload.signature
    db.commit()
    return {"status": "success", "message": "Signature saved to account"}

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.medical_information import MedicalInformation
from ..models.user import User
from ..models.user_profile import UserProfile
from ..schemas.safety import MedicalCreate, MedicalRead, ProfileCreate, ProfileRead
from ..utils.auth import get_current_user

router = APIRouter()


@router.get("/profile", response_model=ProfileRead)
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.post("/profile", response_model=ProfileRead, status_code=status.HTTP_201_CREATED)
def create_or_update_profile(
    payload: ProfileCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if profile is None:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
    profile.full_name = payload.full_name
    profile.date_of_birth = payload.date_of_birth
    profile.gender = payload.gender
    profile.address = payload.address
    profile.city = payload.city
    profile.state = payload.state
    profile.profile_image = payload.profile_image
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/profile/medical", response_model=MedicalRead)
def get_medical_information(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.query(MedicalInformation).filter(MedicalInformation.user_id == user.id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Medical information not found")
    return record


@router.post("/profile/medical", response_model=MedicalRead, status_code=status.HTTP_201_CREATED)
def create_or_update_medical_information(
    payload: MedicalCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.query(MedicalInformation).filter(MedicalInformation.user_id == user.id).first()
    if record is None:
        record = MedicalInformation(user_id=user.id)
        db.add(record)
    record.blood_group = payload.blood_group
    record.allergies = payload.allergies
    record.medical_conditions = payload.medical_conditions
    record.medications = payload.medications
    record.additional_information = payload.additional_information
    db.commit()
    db.refresh(record)
    return record

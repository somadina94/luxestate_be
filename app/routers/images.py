from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, Form
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import Annotated, List
from app.database import SessionLocal
from app.models.favorite import Favorite
from app.models.property import Property
from app.models.property_images import PropertyImage
from app.schemas.favorite import FavoriteCreate, FavoriteResponse
from app.schemas.image import ImageUpload
from app.services.image_service import ImageService
from app.dependencies import require_permission

router = APIRouter(prefix="/property_images", tags=["property_images"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(require_permission("update:properties"))]


@router.post("/{property_id}", status_code=status.HTTP_201_CREATED)
async def upload_property_image(
    db: db_dependency,
    current_user: user_dependency,
    property_id: int,
    alt_text: str = Form(None),
    is_primary: bool = Form(False),
    order_index: int = Form(0),
    file: UploadFile = File(...),
):
    # Validate file type and size
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Upload image to Cloudinary
    upload_result = await ImageService().upload_image(file, property_id)

    # Save to database
    image = PropertyImage(
        property_id=property_id,
        file_key=upload_result["public_id"],
        file_url=upload_result["secure_url"],
        alt_text=alt_text,
        is_primary=is_primary,
        order_index=order_index,
    )
    db.add(image)
    db.commit()

    return {
        "message": "Image uploaded successfully",
        "public_id": upload_result["public_id"],
        "url": upload_result["secure_url"],
    }


@router.get("/{property_id}", status_code=status.HTTP_200_OK)
async def get_property_Images(db: db_dependency, property_id: int):
    return (
        db.query(PropertyImage).filter(PropertyImage.property_id == property_id).all()
    )


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    db: db_dependency,
    current_user: user_dependency,
    image_id: str,
):
    image = db.query(PropertyImage).filter(PropertyImage.id == image_id).first()
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image with id {image_id} not found",
        )
    await ImageService().delete_image(image.file_key)
    db.delete(image)
    db.commit()

    return {"detail": "Image deleted successfully"}


@router.patch("/{image_id}", status_code=status.HTTP_200_OK)
async def update_order_index(
    db: db_dependency, user: user_dependency, image_id: int, order_index: int
):
    image = db.query(PropertyImage).filter(PropertyImage.id == image_id).first()
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image with id {image_id} not found",
        )

    image.order_index = order_index
    db.commit()
    db.refresh(image)

    return {
        "message": "Order index updated successfully",
        "image_id": image_id,
        "new_order_index": image.order_index,
    }

import cloudinary
import cloudinary.uploader
from fastapi import UploadFile
from app.config import settings


class ImageService:
    def __init__(self):
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
        )

    async def upload_image(self, file: UploadFile, property_id: int) -> dict:
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            file.file,
            folder=f"luxestate/properties/{property_id}",
            transformation=[
                {"width": 1200, "height": 800, "crop": "fill", "quality": "auto"},
                {"fetch_format": "auto"},
            ],
        )

        return {
            "public_id": result["public_id"],
            "secure_url": result["secure_url"],
            "format": result["format"],
            "width": result["width"],
            "height": result["height"],
        }

    async def delete_image(self, public_id: str):
        cloudinary.uploader.destroy(public_id)

    def get_image_url(self, public_id: str, transformations: dict = None):
        return cloudinary.CloudinaryImage(public_id).build_url(
            transformation=transformations
        )

from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorGridFSBucket, AsyncIOMotorDatabase
from bson import ObjectId, errors as bson_errors
import io

from app.database import get_db
from app.auth.deps import require_user

router = APIRouter(prefix="/api/storage", tags=["storage"])

MAX_FILE_SIZE = 50 * 1024 * 1024
ALLOWED_MIME_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml",
    "application/pdf",
    "text/plain", "text/csv", "text/markdown",
    "application/json", "application/xml",
    "application/zip", "application/gzip",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _get_fs(db: AsyncIOMotorDatabase) -> AsyncIOMotorGridFSBucket:
    return AsyncIOMotorGridFSBucket(db, bucket_name="komajdon_files")


@router.post("/upload/{collection}")
async def upload_file(
    collection: str,
    file: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
):
    fs = _get_fs(db)
    contents = await file.read()

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size is {MAX_FILE_SIZE // (1024*1024)}MB",
        )

    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_MIME_TYPES and not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{content_type}' is not allowed",
        )

    metadata = {
        "filename": file.filename,
        "content_type": content_type,
        "owner_id": str(user["_id"]),
        "collection": collection,
    }
    grid_id = await fs.upload_from_stream(
        file.filename or "untitled",
        io.BytesIO(contents),
        metadata=metadata,
    )
    return {
        "message": "File uploaded",
        "file_id": str(grid_id),
        "filename": file.filename,
        "size": len(contents),
        "content_type": content_type,
    }


@router.get("/download/{file_id}")
async def download_file(
    file_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
):
    fs = _get_fs(db)
    try:
        obj_id = ObjectId(file_id)
    except bson_errors.InvalidId:
        raise HTTPException(status_code=400, detail="Invalid file ID")

    try:
        grid_out = await fs.open_download_stream(obj_id)
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")

    if grid_out.metadata.get("owner_id") != str(user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")

    return StreamingResponse(
        grid_out,
        media_type=grid_out.metadata.get("content_type", "application/octet-stream"),
        headers={"Content-Disposition": f'attachment; filename="{grid_out.filename}"'},
    )


@router.get("/list/{collection}")
async def list_files(
    collection: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
):
    fs = _get_fs(db)
    cursor = fs.find({"metadata.collection": collection, "metadata.owner_id": str(user["_id"])})
    files = []
    async for grid_doc in cursor:
        files.append({
            "file_id": str(grid_doc._id),
            "filename": grid_doc.filename,
            "size": grid_doc.length,
            "content_type": grid_doc.metadata.get("content_type", ""),
            "upload_date": grid_doc.upload_date.isoformat() if hasattr(grid_doc.upload_date, "isoformat") else str(grid_doc.upload_date),
        })
    return {"files": files}


@router.delete("/delete/{file_id}")
async def delete_file(
    file_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
):
    fs = _get_fs(db)
    try:
        obj_id = ObjectId(file_id)
    except bson_errors.InvalidId:
        raise HTTPException(status_code=400, detail="Invalid file ID")

    try:
        grid_out = await fs.open_download_stream(obj_id)
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")

    if grid_out.metadata.get("owner_id") != str(user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")

    await fs.delete(obj_id)
    return {"message": "File deleted"}

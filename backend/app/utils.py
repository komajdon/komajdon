from __future__ import annotations

from bson import ObjectId
from fastapi import HTTPException


def parse_object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")

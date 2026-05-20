from __future__ import annotations
from typing import Literal, Any
from pydantic import BaseModel, Field

FieldType = Literal[
    "string", "number", "boolean", "date", "array", "object", "relation"
]

RelationType = Literal["has_one", "has_many", "belongs_to"]


class ValidationRule(BaseModel):
    required: bool = False
    unique: bool = False
    min_length: int | None = None
    max_length: int | None = None
    minimum: float | None = None
    maximum: float | None = None
    pattern: str | None = None
    enum: list[str] | None = None


class IndexSpec(BaseModel):
    field: str
    direction: Literal[1, -1] = 1
    unique: bool = False


class Relationship(BaseModel):
    type: RelationType = "belongs_to"
    target_model: str
    foreign_key: str = ""
    through: str | None = None


class FieldDefinition(BaseModel):
    name: str
    type: FieldType
    required: bool = False
    default: Any = None
    validation: ValidationRule = Field(default_factory=ValidationRule)
    relation: Relationship | None = None
    indexed: bool = False


class ModelSchema(BaseModel):
    name: str
    fields: list[FieldDefinition] = []
    indexes: list[IndexSpec] = []
    auth_protected: bool = False
    realtime_enabled: bool = False


class ModelSchemaOut(BaseModel):
    id: str = Field(alias="_id")
    name: str
    fields: list[FieldDefinition] = []
    indexes: list[IndexSpec] = []
    auth_protected: bool = False
    realtime_enabled: bool = False
    created_at: str = ""


class GenerateRequest(BaseModel):
    name: str
    fields: list[FieldDefinition] = []
    indexes: list[IndexSpec] = []
    auth_protected: bool = False
    realtime_enabled: bool = False


class AggregationStage(BaseModel):
    type: str
    params: dict[str, Any] = {}


class AggregationPipeline(BaseModel):
    name: str
    collection: str
    stages: list[AggregationStage] = []


class PipelineOut(BaseModel):
    id: str = Field(alias="_id")
    name: str
    collection: str
    stages: list[AggregationStage] = []
    created_at: str = ""

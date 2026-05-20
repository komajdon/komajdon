from __future__ import annotations
from typing import Literal, Any
from pydantic import BaseModel, Field


class TransformRule(BaseModel):
    op: Literal["pick", "omit", "rename", "compute", "filter", "sort"]
    params: dict[str, Any] = {}


class CompositionStep(BaseModel):
    id: str
    label: str = ""
    type: Literal["request", "transform", "merge"]

    method: str = "GET"
    path: str = ""
    headers: dict[str, str] = {}
    body: dict[str, Any] = {}

    source_steps: list[str] = []
    transform_rules: list[TransformRule] = []
    merge_mode: Literal["zip", "object", "concat"] = "concat"


class Composition(BaseModel):
    name: str
    description: str = ""
    method: str = "GET"
    steps: list[CompositionStep] = []
    output_step: str = ""


class CompositionOut(BaseModel):
    id: str = Field(alias="_id")
    name: str
    description: str = ""
    method: str = "GET"
    steps: list[CompositionStep] = []
    output_step: str = ""
    created_at: str = ""

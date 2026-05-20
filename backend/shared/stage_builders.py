from __future__ import annotations

STAGE_BUILDERS = {
    "match": lambda p: {"$match": p},
    "group": lambda p: {"$group": p},
    "sort": lambda p: {"$sort": p},
    "project": lambda p: {"$project": p},
    "limit": lambda p: {"$limit": int(p.get("limit", 10))},
    "skip": lambda p: {"$skip": int(p.get("skip", 0))},
    "lookup": lambda p: {
        "$lookup": {
            "from": p.get("from", ""),
            "localField": p.get("localField", ""),
            "foreignField": p.get("foreignField", "_id"),
            "as": p.get("as", "related"),
        }
    },
    "unwind": lambda p: {"$unwind": f"${p.get('field', '')}"},
    "count": lambda p: {"$count": p.get("as", "count")},
    "add_fields": lambda p: {"$addFields": p},
}


VALIDATION_RULES = {
    "limit": {"limit": {"type": "int", "min": 1, "max": 10000}},
    "skip": {"skip": {"type": "int", "min": 0}},
    "lookup": {"from": {"type": "str", "required": True}, "localField": {"type": "str", "required": True}, "foreignField": {"type": "str"}, "as": {"type": "str", "required": True}},
    "unwind": {"field": {"type": "str", "required": True}},
    "count": {"as": {"type": "str"}},
    "group": {"_id": {"type": "any", "required": True}},
    "sort": {},
    "project": {},
    "match": {},
    "add_fields": {},
}


def validate_stage(stage_type: str, params: dict) -> list[str]:
    errors = []
    rules = VALIDATION_RULES.get(stage_type, {})
    for field, rule in rules.items():
        if rule.get("required") and field not in params:
            errors.append(f"'{stage_type}' stage missing required field '{field}'")
        elif field in params:
            val = params[field]
            expected = rule.get("type", "any")
            if expected == "int":
                try:
                    v = int(val)
                    if "min" in rule and v < rule["min"]:
                        errors.append(f"'{field}' in '{stage_type}' must be >= {rule['min']}")
                    if "max" in rule and v > rule["max"]:
                        errors.append(f"'{field}' in '{stage_type}' must be <= {rule['max']}")
                except (TypeError, ValueError):
                    errors.append(f"'{field}' in '{stage_type}' must be an integer")
            elif expected == "str" and not isinstance(val, str):
                errors.append(f"'{field}' in '{stage_type}' must be a string")
    return errors


def _sanitize_params(stage_type: str, stage_params: dict, user_params: dict) -> dict:
    """Only allow user params that don't override security-relevant fields."""
    if stage_type == "match":
        return stage_params
    if stage_type == "lookup":
        safe = dict(stage_params)
        for k in ("from", "localField", "foreignField"):
            if k in user_params:
                safe.pop(k, None)
        return safe
    merged = {**stage_params, **user_params}
    return merged


def build_pipeline(stages: list, params: dict) -> list:
    pipeline = []
    for stage in stages:
        builder = STAGE_BUILDERS.get(stage["type"])
        if not builder:
            continue
        merged = _sanitize_params(stage["type"], stage.get("params", {}), params)
        stage_errors = validate_stage(stage["type"], merged)
        if stage_errors:
            logger = __import__("logging").getLogger("komajdon")
            logger.warning("Stage validation errors: %s", stage_errors)
        try:
            pipeline.append(builder(merged))
        except Exception:
            continue
    return pipeline


def serialize_id(item: dict) -> dict:
    if "_id" in item and hasattr(item["_id"], "__str__"):
        try:
            item["_id"] = str(item["_id"])
        except Exception:
            pass
    return item


def serialize_results(results: list) -> list:
    for item in results:
        serialize_id(item)
    return results

"""
Post-processing filter for LLM outputs to enforce strict schema compliance.
Removes extra keys, fills missing required fields with defaults, and ensures enum values are valid.
"""

from typing import Any, Dict, Type
from pydantic import BaseModel, ValidationError
from enum import Enum


def filter_llm_output(data: dict, schema: Type[BaseModel]) -> dict:
    """
    Remove extra keys from LLM output and fill missing required fields with defaults.
    Args:
        data: The LLM output as a dict.
        schema: The Pydantic model class to validate against.
    Returns:
        dict: Cleaned and validated output.
    Raises:
        ValidationError: If required fields are missing or invalid.
    """
    # Parse and validate using Pydantic (will remove extra fields if extra="forbid")
    try:
        obj = schema.parse_obj(data)
        return obj.dict()
    except ValidationError as e:
        # Try to auto-fix: remove extra fields, fill missing with defaults
        cleaned = {}
        for field in schema.__fields__:
            if field in data:
                value = data[field]
                # If field is enum, coerce to valid value
                field_type = schema.__fields__[field].type_  # type: ignore
                if isinstance(field_type, type) and issubclass(field_type, Enum):
                    try:
                        value = field_type(value)
                    except Exception:
                        value = list(field_type)[0]
                cleaned[field] = value
            else:
                # Use default if available
                default = schema.__fields__[field].default
                if default is not None:
                    cleaned[field] = default
        # Validate again
        obj = schema.parse_obj(cleaned)
        return obj.dict()

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
    # Common field aliases (map LLM output to schema fields)
    field_aliases = {
        'content': 'paragraph',  # Map content -> paragraph for ProjectionSchema
        'text': 'paragraph',
        'description': 'summary',
    }
    
    # Apply aliases
    normalized_data = {}
    for key, value in data.items():
        # Check if this key should be mapped to another field
        normalized_key = field_aliases.get(key, key)
        normalized_data[normalized_key] = value
    
    # Parse and validate using Pydantic v2 (will remove extra fields if extra="forbid")
    try:
        # Use model_validate instead of parse_obj (Pydantic v2)
        obj = schema.model_validate(normalized_data) if hasattr(schema, 'model_validate') else schema.parse_obj(normalized_data)
        return obj.model_dump() if hasattr(obj, 'model_dump') else obj.dict()
    except ValidationError as e:
        # Try to auto-fix: remove extra fields, fill missing with defaults
        cleaned = {}
        # Use model_fields (Pydantic v2) or __fields__ (Pydantic v1) for compatibility
        fields_dict = schema.model_fields if hasattr(schema, 'model_fields') else schema.__fields__
        
        for field_name, field_info in fields_dict.items():
            if field_name in normalized_data:
                value = normalized_data[field_name]
                # If field is enum, coerce to valid value
                # Get type from annotation (Pydantic v2) or type_ (Pydantic v1)
                field_type = field_info.annotation if hasattr(field_info, 'annotation') else getattr(field_info, 'type_', None)
                if field_type and isinstance(field_type, type) and issubclass(field_type, Enum):
                    try:
                        value = field_type(value)
                    except Exception:
                        value = list(field_type)[0]
                cleaned[field_name] = value
            else:
                # Use default if available
                default = field_info.default if hasattr(field_info, 'default') else None
                if default is not None and default != ...:  # ... is Pydantic's marker for required
                    cleaned[field_name] = default
        # Validate again
        obj = schema.model_validate(cleaned) if hasattr(schema, 'model_validate') else schema.parse_obj(cleaned)
        return obj.model_dump() if hasattr(obj, 'model_dump') else obj.dict()

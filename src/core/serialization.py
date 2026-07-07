"""Small compatibility helpers for Pydantic v1/v2."""

import json
from typing import Any

from pydantic import BaseModel


def to_message_dict(model: BaseModel) -> dict[str, Any]:
    """Return a JSON-ready dict for a Pydantic model."""
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return json.loads(model.json())

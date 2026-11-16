from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, Dict, Any

class PredictionRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"client_id": 100002},
                {"features": {"AMT_INCOME_TOTAL": 180000.0, "DAYS_BIRTH": -13000}}
            ]
        }
    )
    client_id: Optional[int] = Field(None, ge=1, description="Identifiant du client (SK_ID_CURR)")
    features: Optional[Dict[str, Any]] = Field(None, description="Features du client")

    @field_validator("features")
    @classmethod
    def validate_features(cls, v):
        if v is None:
            return v
        numeric_fields = {
            "AMT_INCOME_TOTAL": (0, None),
            "AMT_CREDIT": (0, None),
            "DAYS_BIRTH": (None, 0),
            "CNT_CHILDREN": (0, None),
            "EXT_SOURCE_1": (0, 1),
            "EXT_SOURCE_2": (0, 1),
            "EXT_SOURCE_3": (0, 1),
        }
        for field, (min_val, max_val) in numeric_fields.items():
            if field in v and v[field] is not None:
                value = v[field]
                if not isinstance(value, (int, float)):
                    raise ValueError(f"{field} doit être un nombre")
                if min_val is not None and value < min_val:
                    raise ValueError(f"{field} doit être >= {min_val}")
                if max_val is not None and value > max_val:
                    raise ValueError(f"{field} doit être <= {max_val}")
        return v

class PredictionResponse(BaseModel):
    client_id: Optional[int] = None
    probabilite_defaut: float
    risque: int

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)

class Token(BaseModel):
    access_token: str
    token_type: str
    is_admin: bool = False
    username: str = ""
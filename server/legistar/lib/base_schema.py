from pydantic import BaseModel as PydanticBase


class BaseSchema(PydanticBase):
    """Base schema type for all Legistar-returned data."""

    # def dict(self, *args, **kwargs):
    #     """Override dict() to ensure we remove None values from the output."""
    #     # Keep exclude_none=False if explicitly provided, though.
    #     final_kwargs = {"exclude_none": True, **kwargs}
    #     return super().dict(*args, **final_kwargs)

    # def json(self, *args, **kwargs):
    #     """Override json() to ensure we remove None values from the output."""
    #     # Keep exclude_none=False if explicitly provided, though.
    #     final_kwargs = {"exclude_none": True, **kwargs}
    #     return super().json(*args, **final_kwargs)

    class Config:
        allow_population_by_field_name = True

from pydantic import BaseModel, ConfigDict, Field


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    name: str
    color: str
    nav_group: str
    position: int
    is_active: bool
    article_count: int = 0


class CategoryCreate(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=60)
    name: str = Field(min_length=2, max_length=100)
    color: str = Field(default="#64748b", pattern=r"^#[0-9a-fA-F]{6}$")
    nav_group: str = Field(default="autres", max_length=30)
    position: int = 0
    is_active: bool = True


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    nav_group: str | None = Field(default=None, max_length=30)
    position: int | None = None
    is_active: bool | None = None

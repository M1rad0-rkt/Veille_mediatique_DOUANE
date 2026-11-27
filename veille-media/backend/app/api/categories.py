from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from app.core.deps import AdminUser, CurrentUser, DbSession
from app.models import Category, News, NewsCategory
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])


def _out(cat: Category, count: int = 0) -> CategoryOut:
    out = CategoryOut.model_validate(cat)
    out.article_count = count
    return out


@router.get("", response_model=list[CategoryOut])
def list_categories(db: DbSession, _user: CurrentUser, include_inactive: bool = False):
    counts = dict(db.execute(
        select(NewsCategory.category_id, func.count())
        .join(News, News.id == NewsCategory.news_id).where(News.duplicate_of_id.is_(None))
        .group_by(NewsCategory.category_id)).all())
    stmt = select(Category).order_by(Category.position, Category.id)
    if not include_inactive:
        stmt = stmt.where(Category.is_active)
    return [_out(c, counts.get(c.id, 0)) for c in db.scalars(stmt)]


@router.get("/nav")
def nav_groups(db: DbSession, _user: CurrentUser):
    """Navigation simplifiée (section 8.C) : un groupe = plusieurs catégories, articles comptés une seule fois."""
    rows = db.execute(
        select(Category.nav_group, func.count(func.distinct(News.id)))
        .join(NewsCategory, NewsCategory.category_id == Category.id)
        .join(News, (News.id == NewsCategory.news_id) & News.duplicate_of_id.is_(None))
        .where(Category.is_active).group_by(Category.nav_group)).all()
    counts = dict(rows)
    groups = db.execute(select(Category.nav_group, func.min(Category.position)).where(Category.is_active)
                        .group_by(Category.nav_group).order_by(func.min(Category.position))).all()
    return [{"nav_group": g, "count": counts.get(g, 0)} for g, _ in groups]


@router.post("", response_model=CategoryOut, status_code=201)
def create_category(body: CategoryCreate, db: DbSession, _admin: AdminUser):
    if db.scalar(select(Category.id).where(Category.slug == body.slug)):
        raise HTTPException(409, "Ce slug existe déjà")
    cat = Category(**body.model_dump())
    db.add(cat)
    db.commit()
    return _out(cat)


@router.put("/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, body: CategoryUpdate, db: DbSession, _admin: AdminUser):
    cat = db.get(Category, category_id)
    if not cat:
        raise HTTPException(404, "Catégorie introuvable")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(cat, k, v)
    db.commit()
    return _out(cat)


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int, db: DbSession, _admin: AdminUser):
    cat = db.get(Category, category_id)
    if not cat:
        raise HTTPException(404, "Catégorie introuvable")
    if cat.slug == "autres":
        raise HTTPException(409, "La catégorie « Autres » est la catégorie de repli et ne peut pas être supprimée")
    if db.scalar(select(func.count()).select_from(NewsCategory).where(NewsCategory.category_id == cat.id)):
        raise HTTPException(409, "Des articles utilisent cette catégorie : désactivez-la plutôt que de la supprimer")
    db.delete(cat)
    db.commit()

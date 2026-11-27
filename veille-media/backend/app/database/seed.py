"""Données initiales idempotentes : rôles, catégories, paramètres, premier admin."""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models import AppSetting, Category, Role, Source, User

log = logging.getLogger(__name__)

ROLES = {
    "admin": ["*"],
    "user": ["news:read", "favorites:write", "history:write"],
}

# (slug, nom, couleur, nav_group) — nav_group alimente la navigation simplifiée (section 8.C)
CATEGORIES = [
    ("economie-finances", "Économie et finances", "#0ea5e9", "economie"),
    ("politique-gouvernance", "Politique et gouvernance", "#6366f1", "politique"),
    ("societe", "Société", "#f59e0b", "societe"),
    ("sante", "Santé", "#ef4444", "sante"),
    ("education", "Éducation", "#8b5cf6", "education"),
    ("technologie-innovation", "Technologie et innovation", "#14b8a6", "technologie"),
    ("environnement-climat", "Environnement et climat", "#22c55e", "environnement"),
    ("agriculture-elevage", "Agriculture et élevage", "#84cc16", "autres"),
    ("infrastructures-transports", "Infrastructures et transports", "#64748b", "autres"),
    ("securite-justice", "Sécurité et justice", "#dc2626", "autres"),
    ("sport", "Sport", "#f97316", "sport"),
    ("culture-tourisme", "Culture et tourisme", "#ec4899", "culture"),
    ("international", "International", "#0891b2", "autres"),
    ("autres", "Autres", "#94a3b8", "autres"),
]

DEFAULT_SETTINGS = {"default_interval_minutes": 30, "theme": "light"}


def seed(db: Session) -> None:
    for name, perms in ROLES.items():
        if not db.scalar(select(Role).where(Role.name == name)):
            db.add(Role(name=name, permissions=perms))
    db.flush()

    existing = set(db.scalars(select(Category.slug)))
    for pos, (slug, name, color, nav) in enumerate(CATEGORIES, start=1):
        if slug not in existing:  # ne jamais écraser les modifications de l'admin
            db.add(Category(slug=slug, name=name, color=color, nav_group=nav, position=pos))

    for key, value in DEFAULT_SETTINGS.items():
        if not db.get(AppSetting, key):
            db.add(AppSetting(key=key, value=value))
    db.flush()

    admin_role = db.scalar(select(Role).where(Role.name == "admin"))
    has_admin = db.scalar(select(User.id).where(User.role_id == admin_role.id).limit(1))
    if not has_admin and settings.first_admin_email and settings.first_admin_password:
        db.add(User(
            email=settings.first_admin_email.lower(),
            full_name=settings.first_admin_name,
            password_hash=hash_password(settings.first_admin_password),
            role_id=admin_role.id,
        ))
        log.info("Premier administrateur créé : %s", settings.first_admin_email)
    db.commit()


# Médias du cahier des charges. Aucune URL de flux n'est supposée : le diagnostic réel
# (python -m app.tools.probe_sources --apply) détermine RSS/sitemap et active la source.
DEFAULT_SOURCES = [
    ("L'Express de Madagascar", "https://www.lexpress.mg/"),
    ("2424.mg", "https://2424.mg/"),
    ("Midi Madagasikara", "https://www.midi-madagasikara.mg/"),
    ("Newsmada", "https://www.newsmada.com/"),
    ("Madagascar Tribune", "https://www.madagascar-tribune.com/"),
]


def seed_sources(db: Session) -> None:
    """Appelé au démarrage de l'API seulement si aucune source n'existe encore."""
    if db.scalar(select(Source.id).limit(1)):
        return
    for name, url in DEFAULT_SOURCES:
        db.add(Source(name=name, base_url=url, type="rss", is_active=False))
    db.commit()
    log.info("Sources initiales créées (inactives) : lancer le diagnostic pour les activer")

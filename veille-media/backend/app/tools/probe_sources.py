"""Diagnostic réel des sources : robots.txt, flux RSS, sitemap. Met à jour la base si --apply.
Usage : docker compose exec api python -m app.tools.probe_sources [--apply]"""
import sys

from sqlalchemy import select

from app.database.session import SessionLocal
from app.models import Source
from app.scrapers.base import PoliteClient
from app.scrapers.discovery import probe_source


def main(apply: bool) -> None:
    with SessionLocal() as db, PoliteClient() as client:
        for src in db.scalars(select(Source).order_by(Source.name)):
            rep = probe_source(client, src.base_url)
            print(f"\n== {src.name} ({src.base_url})")
            print(f"   robots.txt autorise : {rep.robots_ok}")
            print(f"   flux RSS            : {rep.feed_url or '—'} ({rep.feed_items} articles)")
            print(f"   sitemap             : {rep.sitemap_url or '—'}")
            for n in rep.notes:
                print(f"   note : {n}")
            if apply:
                src.robots_ok = rep.robots_ok
                if rep.recommended_type and rep.robots_ok:
                    src.type, src.feed_url, src.is_active = rep.recommended_type, rep.feed_url or rep.sitemap_url, True
                    print(f"   => activée en mode {src.type}")
                else:
                    src.is_active = False
                    print("   => laissée INACTIVE (aucun moyen de collecte autorisé trouvé) : à configurer à la main")
                db.commit()


if __name__ == "__main__":
    main("--apply" in sys.argv)

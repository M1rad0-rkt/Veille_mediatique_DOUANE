# Plateforme de veille médiatique — Madagascar

Collecte automatique des actualités de médias malgaches, classement par catégorie et résumés par IA (Gemini),
consultables dans une interface web par les agents de communication.

État : **Phases 1 à 6 livrées** — API FastAPI + PostgreSQL, agent de collecte (worker), IA, interface React, tests.

## Démarrage local (Windows, Docker Desktop avec WSL 2)

```powershell
copy .env.example .env      # puis éditer .env (voir ci-dessous)
docker compose up --build
```

À renseigner dans `.env` : `POSTGRES_PASSWORD`, `SECRET_KEY`, `FIRST_ADMIN_*`, **`GEMINI_API_KEY`** (gratuite : https://aistudio.google.com/apikey)
et `USER_AGENT` (mettez un vrai contact : les sites voient qui les consulte).
Génération d'une clé : `docker run --rm python:3.12-slim python -c "import secrets; print(secrets.token_urlsafe(48))"`

| Service | Rôle | Adresse |
|---|---|---|
| `frontend` | Interface React (Vite) | http://localhost:5173 |
| `api` | API FastAPI + migrations | http://localhost:8000/api/docs |
| `worker` | Agent de collecte + traitement IA | (arrière-plan) |
| `db` | PostgreSQL 16 + pgvector | localhost:5432 |

### Première mise en route des sources (important)

Les 5 médias du cahier des charges sont créés **inactifs** : aucune adresse de flux n'est supposée, elle doit être constatée sur le vrai site.
1. Connectez-vous (http://localhost:5173) avec `FIRST_ADMIN_EMAIL` / `FIRST_ADMIN_PASSWORD`.
2. **Administration → Sources → loupe (Diagnostiquer)** : l'application lit `robots.txt`, cherche un flux RSS puis un sitemap, et affiche le résultat.
   « Appliquer et activer » configure la source. (Équivalent en ligne de commande : `docker compose exec api python -m app.tools.probe_sources --apply`.)
3. Si `robots.txt` interdit la collecte, ou si aucun flux n'existe, la source reste inactive : demandez une autorisation au média ou configurez un
   connecteur HTML (sélecteurs CSS à vérifier sur le site). Les protections techniques (403, 429, challenge anti-robot) ne sont **jamais contournées** :
   la source passe en « Erreur » avec le motif.
4. **Administration → Agent de collecte → Collecter maintenant**, puis suivez l'état et le journal en direct.

## Fonctionnement

```
Sources (RSS / sitemap / HTML) ──► Agent (worker) ──► PostgreSQL ◄── API FastAPI ◄── Interface React
                                      │  1. robots.txt, requête polie (délai, taille max, 304)
                                      │  2. liste des articles, URL canonique, doublons
                                      │  3. page article : texte (Trafilatura) + métadonnées
                                      │  4. enregistrement (date de publication ≠ date de collecte)
                                      └► Traitement IA : catégories (1 à 3) + résumé + entités, validés avant enregistrement
```

- **Dates** : `published_at` vient du flux ou de la page, jamais de la date de collecte. Sans date fiable (absente, dans le futur), elle reste vide et
  l'interface affiche « Date non disponible ». Le tri utilise une date technique séparée (`sort_date`).
- **Doublons** : (1) URL canonique normalisée (sans `utm_*`, sans `www`, sans `/` final) ; (2) même titre + début de texte **dans la même source**
  (republication sous une autre URL). Deux médias reprenant la même dépêche restent tous deux visibles (utile pour comparer la couverture).
- **IA** : une seule requête par article. Seules les catégories existantes sont acceptées ; confiance faible → « Autres » ; les entités absentes du texte
  sont supprimées ; texte trop court → pas de résumé (« Résumé non disponible ») ; une correction manuelle de l'administrateur n'est jamais écrasée.
  Échecs retentés 3 fois (15 min d'écart) ; quota 429 → le lot s'arrête sans pénalité. Fournisseur interchangeable : `AI_PROVIDER=gemini|openai|none`
  (`openai` accepte aussi un modèle local Ollama / LM Studio via `OPENAI_BASE_URL`).
- **Texte intégral** : stocké pour le traitement interne uniquement, jamais renvoyé par l'API. L'interface affiche titre, résumé IA, extrait du flux et lien
  vers l'original ; les images sont affichées depuis le site d'origine (non copiées).
- **Fréquence** : par source (`interval_minutes`) et valeur par défaut modifiable dans Administration → Agent. Après des échecs consécutifs, l'intervalle double (x2, x4, x8 max).

## Tests

```bash
docker compose exec api pytest -q
```
Tests d'intégration sur une vraie base PostgreSQL (`veille_test`) : authentification/RBAC, API des actualités, collecte contre un faux serveur HTTP
(doublons, dates, robots.txt, 403 non contourné), enrichissement IA avec un faux fournisseur (seuils, anti-invention, correction manuelle, quotas).
Aucun test n'appelle Gemini ni un vrai site.

## Commandes utiles

```bash
docker compose logs -f worker                                              # suivre la collecte et l'IA
docker compose exec api alembic revision --autogenerate -m "description"
docker compose exec api alembic upgrade head
./scripts/backup_db.sh        # ou .\scripts\backup_db.ps1 sous Windows
docker compose down -v        # repart de zéro (efface les données)
```
Si le port 5432 est déjà pris : `5433:5432` dans `docker-compose.yml`. Fichiers `.sql` / `.sh` en fins de ligne LF.

## Sécurité en place

Argon2 · JWT d'accès 30 min (gardé en mémoire côté navigateur) + refresh en cookie httpOnly (rotation) · RBAC `admin` / `user` · pas d'inscription publique ·
5 tentatives de connexion/min/IP · validation Pydantic · requêtes SQLAlchemy paramétrées · CORS restreint · clés API uniquement côté serveur ·
l'interface ne rend jamais de HTML venant des sites (React échappe tout).

## Limites connues / prochaines étapes

- **Playwright** (sites rendus en JavaScript) n'est pas activé : à ajouter source par source, seulement si le site l'exige **et** que la collecte est autorisée.
- Pour un déploiement en production : HTTPS, `COOKIE_SECURE=true`, `ENVIRONMENT=production`, build frontend (`npm run build`) servi par un serveur web, sauvegardes planifiées.
- Prévu par l'architecture mais non développé : alertes, tendances, sentiment, rapports PDF/Excel, revue de presse par e-mail, similarité vectorielle (pgvector est déjà installé).

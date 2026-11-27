-- Exécuté une seule fois, à la création du volume Postgres.
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS vector;

-- Base dédiée aux tests automatisés.
CREATE DATABASE veille_test;
\c veille_test
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS vector;

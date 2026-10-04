# TDR-0006: Backups mit restic auf eine SFTP-Backup-Speicher

* **Status:** accepted
* **Date:** 2026-10-04
* **Author:** Nicolas Mischler
* **Scope:** `docker/backup/`, `docker-compose.prod.yml` (Dienste `backup`, `restore`), Runbook

## Problem / Scope

Es existierten keine Backups für Datenbank und hochgeladene Bilder; ein Serververlust hätte alle Inhalte
und Anfragen vernichtet (ADR-0003 forderte Backups, umgesetzt waren sie nicht).

## Technical Decision

* Sidecar-Container auf Basis `postgres:16-alpine` (passender `pg_dump`) mit `restic`, Cron:
  täglich 02:30 Dump + `/media` → restic-Repository per SFTP (Port 23) auf der Storage Box,
  Aufbewahrung 7 täglich / 4 wöchentlich / 6 monatlich, sonntags `restic check --read-data-subset=5%`.
* Clientseitige Verschlüsselung (restic, `RESTIC_PASSWORD` zusätzlich offline aufbewahrt),
  optionaler Healthcheck-Ping (Start/Erfolg/Fehler).
* Wiederherstellung über Profil-Dienst `restore` (Medien-Volume beschreibbar), lokal end-to-end getestet.

## Rationale & Trade-offs

* **Why this approach:** verschlüsselt, dedupliziert, inkrementell, getrennter Standort, sehr günstig.
* **Alternatives evaluated:** Server-Snapshots allein (gleicher Provider/Account, keine Versionierung von
  Einzeldaten), S3 (zusätzlicher Anbieter).
* **Impact on existing code:** keine App-Änderung; Runbook beschreibt Einrichtung, Kontrolle und Restore.

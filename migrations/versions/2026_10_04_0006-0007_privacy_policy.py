"""Privacy policy update: hosting (Hosting), contact form, ALTCHA, cookies, fonts.

Replaces only untouched default texts (see migrations/_helpers.py). The new sections
5 (Cookies/Schriftarten) and 6 (Rechte) are seeded automatically at startup.

Revision ID: 0007_privacy_policy
Revises: 0006_contact_protection
Create Date: 2026-10-04 00:06:00 UTC

"""

# ruff: noqa: E501  (frozen default-text snapshots)

from collections.abc import Sequence

from _helpers import replace_default_texts
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007_privacy_policy"
down_revision: str | None = "0006_contact_protection"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# key -> (old default, new default)
CHANGES: dict[str, tuple[str, str]] = {
    "contact.privacy_note": (
        "Ihre Angaben werden streng vertraulich behandelt und ausschließlich zur Beantwortung Ihrer Anfrage genutzt.",
        "Ihre Angaben werden vertraulich behandelt und ausschliesslich zur Beantwortung Ihrer Anfrage genutzt. Details finden Sie in der Datenschutzerklärung.",
    ),
    "datenschutz.sec2_title": (
        "2. Erhebung von Daten bei Kontaktaufnahme",
        "2. Kontaktformular und E-Mail",
    ),
    "datenschutz.sec2_text": (
        "Wenn Sie das Kontaktformular ausfüllen oder eine E-Mail senden, werden die von Ihnen angegebenen Kontaktdaten (Name, E-Mail-Adresse, Telefonnummer, Nachricht) gespeichert, um Ihre Anfrage zu bearbeiten und allfällige Anschlussfragen zu klären. Diese Daten werden ohne Ihre ausdrückliche Zustimmung niemals an Dritte weitergegeben.",
        "Wenn Sie das Kontaktformular nutzen oder mir eine E-Mail senden, bearbeite ich Ihre Angaben (Name, E-Mail-Adresse, optional Telefonnummer, Betreff und Nachricht) ausschliesslich, um Ihre Anfrage zu beantworten. Zum Schutz vor Missbrauch wird zusätzlich die IP-Adresse gespeichert. Sie erhalten eine kurze automatische Empfangsbestätigung per E-Mail. Kontaktanfragen werden nach spätestens 12 Monaten automatisch gelöscht. Ihre Daten werden nicht an Dritte weitergegeben – ausgenommen die technischen Dienstleister für Hosting und E-Mail-Versand, die sie ausschliesslich in meinem Auftrag bearbeiten.",
    ),
    "datenschutz.sec3_title": (
        "3. Server-Logfiles & Sicherheit",
        "3. Hosting und Server-Logfiles",
    ),
    "datenschutz.sec3_text": (
        "Beim Aufruf dieser Website erhebt der Hosting-Provider (Standort Schweiz / Deutschland mit ISO 27001 Zertifizierung) automatisch technische Informationen (IP-Adresse, Datum, Uhrzeit, Browsertyp). Diese Daten dienen ausschließlich der Systemsicherheit und Fehleranalyse.",
        "Diese Website wird bei einer Hosting-Anbieterin in Rechenzentren in Deutschland bzw. Finnland (EU) betrieben; für die EU besteht gemäss DSG ein angemessenes Datenschutzniveau. Beim Aufruf der Website werden technisch notwendige Angaben (IP-Adresse, Datum und Uhrzeit, aufgerufene Seite, Browsertyp) in Server-Logfiles erfasst. Sie dienen ausschliesslich der Sicherheit und Fehleranalyse und werden regelmässig gelöscht.",
    ),
    "datenschutz.sec4_title": (
        "4. Ihre Rechte",
        "4. Schutz vor Spam und Missbrauch",
    ),
    "datenschutz.sec4_text": (
        "Sie haben jederzeit das Recht auf unentgeltliche Auskunft über Ihre gespeicherten personenbezogenen Daten, deren Herkunft und den Zweck der Datenbearbeitung sowie ein Recht auf Berichtigung, Sperrung oder Löschung dieser Daten.",
        "Das Kontaktformular ist mit ALTCHA geschützt – einer Sicherheitsprüfung, die vollständig auf diesem Server läuft. Ihr Browser löst dabei eine kleine Rechenaufgabe; es werden keine Cookies gesetzt und keine Daten an Dritte übermittelt.",
    ),
}


def upgrade() -> None:
    replace_default_texts(op.get_bind(), CHANGES, "Datenschutzerklärung aktualisiert")


def downgrade() -> None:
    # Previous texts remain restorable via the admin version history.
    pass

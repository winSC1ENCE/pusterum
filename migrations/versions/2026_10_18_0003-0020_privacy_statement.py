# ruff: noqa: E501  (frozen default-text snapshots)
"""Privacy statement after the EDÖB guidance (tech-debt #6, ADR-0006).

Data-only migration (see TDR-0003). Rewrites the sections for the information duty of
Art. 19 DSG: controller and contact, purposes, health data, retention per status, recipients
and countries, rights. Adds a short summary at the top (multi-level approach recommended by
the EDÖB); the new keys «datenschutz.summary» and «datenschutz.sec7-9_*» are seeded at startup.
The contact form note asks for no detailed health information. Replaces only untouched
default texts (see migrations/_helpers.py).

Revision ID: 0020_privacy_statement
Revises: 0019_contact_status_model
Create Date: 2026-10-18 00:03:00 UTC

"""

from collections.abc import Sequence

from _helpers import replace_default_texts
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0020_privacy_statement"
down_revision: str | None = "0019_contact_status_model"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# key -> (old default, new default)
CHANGES: dict[str, tuple[str, str]] = {
    "contact.privacy_note": (
        "Ihre Angaben werden vertraulich behandelt und ausschliesslich zur Beantwortung Ihrer Anfrage genutzt. Details finden Sie in der Datenschutzerklärung.",
        "Ihre Angaben werden verschlüsselt gespeichert und nur zur Beantwortung Ihrer Anfrage genutzt. Bitte schreiben Sie keine ausführlichen Gesundheitsangaben; das besprechen wir persönlich.",
    ),
    "datenschutz.intro": (
        "Der Schutz Ihrer persönlichen Daten ist mir ein wichtiges Anliegen. Diese Datenschutzerklärung informiert Sie über die Erhebung und Bearbeitung personenbezogener Daten beim Besuch dieser Website und bei der Kontaktaufnahme gemäss dem Schweizerischen Datenschutzgesetz (DSG).",
        "Der Schutz Ihrer persönlichen Daten ist mir ein wichtiges Anliegen. Diese Datenschutzerklärung informiert Sie nach dem Schweizer Datenschutzgesetz (DSG), welche Daten ich beim Besuch dieser Website und bei einer Kontaktaufnahme bearbeite, wozu und wie lange.",
    ),
    "datenschutz.sec1_title": (
        "1. Verantwortliche Person",
        "1. Verantwortliche Stelle",
    ),
    "datenschutz.sec1_text": (
        "Verantwortlich für die Datenbearbeitung auf dieser Webseite ist die Praxisinhaberin gemäss Angaben im Impressum.",
        "Verantwortlich für die Bearbeitung Ihrer Personendaten ist die Praxisinhaberin von PUSTERUM (Name und Adresse im Impressum).\n\nKontakt für alle Fragen zum Datenschutz: info@pusterum.be",
    ),
    "datenschutz.sec2_text": (
        "Wenn Sie das Kontaktformular nutzen oder mir eine E-Mail senden, bearbeite ich Ihre Angaben (Name, E-Mail-Adresse, optional Telefonnummer, Betreff und Nachricht) ausschliesslich, um Ihre Anfrage zu beantworten. Zum Schutz vor Missbrauch wird zusätzlich die IP-Adresse gespeichert. Sie erhalten eine kurze automatische Empfangsbestätigung per E-Mail. Kontaktanfragen werden nach spätestens 12 Monaten automatisch gelöscht. Ihre Daten werden nicht an Dritte weitergegeben \u2013 ausgenommen die technischen Dienstleister für Hosting und E-Mail-Versand, die sie ausschliesslich in meinem Auftrag bearbeiten.",
        "Wenn Sie mir über das Kontaktformular oder per E-Mail schreiben, bearbeite ich Ihren Namen, Ihre E-Mail-Adresse, falls angegeben Ihre Telefonnummer sowie Betreff und Nachricht. Ich nutze diese Angaben nur, um Ihre Anfrage zu beantworten und einen Termin zu vereinbaren.\n\nNachrichten können Angaben zu Ihrer Gesundheit enthalten. Das sind besonders schützenswerte Personendaten. Bitte schreiben Sie deshalb nur das Nötigste; Einzelheiten besprechen wir persönlich. Nachricht und Telefonnummer werden verschlüsselt gespeichert.\n\nÜber eine neue Anfrage werde ich per E-Mail benachrichtigt. Diese E-Mail enthält nur Ihren Vornamen und den Betreff, nicht Ihre Nachricht. Sie selbst erhalten eine kurze automatische Empfangsbestätigung.\n\nZum Schutz vor Missbrauch wird Ihre IP-Adresse gespeichert und nach 7 Tagen gelöscht.",
    ),
    "datenschutz.sec3_title": (
        "3. Hosting und Server-Logfiles",
        "3. Aufbewahrung und Löschung",
    ),
    "datenschutz.sec3_text": (
        "Diese Website wird bei einer Hosting-Anbieterin in Rechenzentren in Deutschland bzw. Finnland (EU) betrieben; für die EU besteht gemäss DSG ein angemessenes Datenschutzniveau. Beim Aufruf der Website werden technisch notwendige Angaben (IP-Adresse, Datum und Uhrzeit, aufgerufene Seite, Browsertyp) in Server-Logfiles erfasst. Sie dienen ausschliesslich der Sicherheit und Fehleranalyse und werden regelmässig gelöscht.",
        "Anfragen werden automatisch gelöscht: abgeschlossene Anfragen 6 Monate nach Abschluss, offensichtlicher Spam nach 7 Tagen, alle anderen spätestens 12 Monate nach Eingang. Auf Ihren Wunsch lösche ich sie sofort.\n\nDie Website wird täglich verschlüsselt gesichert. Gelöschte Daten können in diesen Sicherungen noch bis zu 6 Monate enthalten sein. Sie werden dort nicht verwendet und nach einer Wiederherstellung sofort erneut gelöscht.",
    ),
    "datenschutz.sec4_title": (
        "4. Schutz vor Spam und Missbrauch",
        "4. Empfänger und Bearbeitung im Ausland",
    ),
    "datenschutz.sec4_text": (
        "Das Kontaktformular ist mit ALTCHA geschützt \u2013 einer Sicherheitsprüfung, die vollständig auf diesem Server läuft. Ihr Browser löst dabei eine kleine Rechenaufgabe; es werden keine Cookies gesetzt und keine Daten an Dritte übermittelt.",
        "Ich gebe Ihre Daten nicht an Dritte weiter und verkaufe sie nicht. Zugriff haben nur Dienstleister, die sie in meinem Auftrag und nach meinen Weisungen bearbeiten (Auftragsbearbeiter):\n• Hosting der Website in einem Rechenzentrum in Deutschland;\n• E-Mail-Anbieterin mit Sitz in der Schweiz;\n• verschlüsselte Datensicherung in einem Rechenzentrum in der EU;\n• technische Betreuung der Website (siehe Impressum).\n\nDeutschland und die übrigen EU-Staaten haben nach Beurteilung des Bundesrates ein angemessenes Datenschutzniveau.",
    ),
    "datenschutz.sec5_title": (
        "5. Cookies und Schriftarten",
        "5. Besuch der Website",
    ),
    "datenschutz.sec5_text": (
        "Diese Website verwendet keine Analyse- oder Tracking-Dienste und keine Werbe-Cookies. Gesetzt werden ausschliesslich technisch notwendige Cookies: ein Sicherheits-Cookie zum Schutz der Formulare vor Missbrauch (CSRF-Schutz) sowie \u2013 nur für die Praxisinhaberin \u2013 ein Anmelde-Cookie für den Verwaltungsbereich. Alle Schriftarten werden direkt von diesem Server geladen; es besteht keine Verbindung zu Google oder anderen Drittanbietern. Wenn Sie die Schriftgrösse ändern, speichert Ihr Browser diese Einstellung lokal (Local Storage); sie wird nicht an den Server übertragen.",
        "Beim Aufruf der Website speichert der Server technisch notwendige Angaben: Datum und Uhrzeit, aufgerufene Seite, Browsertyp und eine gekürzte IP-Adresse, die keinen Rückschluss auf Sie zulässt. Diese Server-Logfiles dienen nur der Sicherheit und Fehleranalyse und werden fortlaufend überschrieben.",
    ),
    "datenschutz.sec6_title": (
        "6. Ihre Rechte",
        "6. Schutz vor Spam und Missbrauch",
    ),
    "datenschutz.sec6_text": (
        "Sie haben jederzeit das Recht auf unentgeltliche Auskunft über Ihre bei mir gespeicherten Personendaten sowie auf deren Berichtigung oder Löschung. Wenden Sie sich dazu an die im Impressum genannte E-Mail-Adresse. Zudem können Sie sich beim Eidgenössischen Datenschutz- und Öffentlichkeitsbeauftragten (EDÖB) beschweren.",
        "Das Kontaktformular ist mit ALTCHA geschützt, einer Sicherheitsprüfung, die vollständig auf diesem Server läuft. Ihr Browser löst dabei eine kleine Rechenaufgabe; es werden keine Cookies gesetzt und keine Daten an Dritte übermittelt.",
    ),
}


def upgrade() -> None:
    replace_default_texts(op.get_bind(), CHANGES, "Datenschutzerklärung nach EDÖB")


def downgrade() -> None:
    replace_default_texts(
        op.get_bind(),
        {key: (new, old) for key, (old, new) in CHANGES.items()},
        "Datenschutzerklärung zurückgesetzt",
    )

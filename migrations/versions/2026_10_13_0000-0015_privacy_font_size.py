"""Privacy policy default: mention the locally stored font size preference.

Data-only migration (see TDR-0003). The font size control keeps the visitor's choice in the
browser's Local Storage; section 5 of the privacy policy lists what the browser stores.
Replaces only the untouched default text (see migrations/_helpers.py).

Revision ID: 0015_privacy_font_size
Revises: 0014_address_placeholder
Create Date: 2026-10-13 00:00:00 UTC

"""

from collections.abc import Sequence

from _helpers import replace_default_texts
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0015_privacy_font_size"
down_revision: str | None = "0014_address_placeholder"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD = (
    "Diese Website verwendet keine Analyse- oder Tracking-Dienste und keine Werbe-Cookies. "
    "Gesetzt werden ausschliesslich technisch notwendige Cookies: ein Sicherheits-Cookie "
    "zum Schutz der Formulare vor Missbrauch (CSRF-Schutz) sowie – nur für die "
    "Praxisinhaberin – ein Anmelde-Cookie für den Verwaltungsbereich. Alle Schriftarten "
    "werden direkt von diesem Server geladen; es besteht keine Verbindung zu Google oder "
    "anderen Drittanbietern."
)
_NEW = (
    _OLD + " Wenn Sie die Schriftgrösse ändern, speichert Ihr Browser diese "
    "Einstellung lokal (Local Storage); sie wird nicht an den Server übertragen."
)

# key -> (old default, new default)
CHANGES: dict[str, tuple[str, str]] = {"datenschutz.sec5_text": (_OLD, _NEW)}


def upgrade() -> None:
    replace_default_texts(op.get_bind(), CHANGES, "Datenschutz: Schriftgrösse")


def downgrade() -> None:
    replace_default_texts(
        op.get_bind(),
        {key: (new, old) for key, (old, new) in CHANGES.items()},
        "Datenschutz: Schriftgrösse zurückgesetzt",
    )

# ruff: noqa: E501  (frozen default-text snapshots)
"""Rebranding «Hā Ola» → PUSTERUM: refresh untouched default content.

Data-only migration. The schema itself is created via ``Base.metadata.create_all``
at application startup, and ``_ensure_seed_data`` only inserts *missing* content keys.
Existing databases therefore still hold the former «Hā Ola» defaults. This revision
replaces every content block (and profile / practice field) whose current value is
still exactly the old default. Blocks edited by the practice owner stay untouched.
Each replacement is written as a new immutable version (ADR-0002), so the previous
text remains restorable via the admin version history.

Revision ID: 0001_pusterum_rebranding
Revises:
Create Date: 2026-10-04 00:00:00 UTC

"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_pusterum_rebranding"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AUTHOR_NAME = "System Migration"
CHANGE_SUMMARY = "Rebranding PUSTERUM"

# key -> (old default, new default, new block type)
CONTENT_CHANGES: dict[str, tuple[str, str, str]] = {
    "hero.badge": (
        "Atemtherapie Hā Ola • OdA KT • In Gemeinschaftspraxis Physiotherapie",
        "PUSTERUM • Atem- und Körpertherapie • In Gemeinschaftspraxis Physiotherapie",
        "text",
    ),
    "hero.title": (
        "Hā Ola.",
        "PUSTERUM.",
        "text",
    ),
    "hero.subtitle": (
        "Der heilsame Atem des Lebens.",
        "Raum zum Atmen – die Brücke zwischen Körper und Psyche.",
        "text",
    ),
    "hero.text": (
        "«Hā» (Atem, Lebenshauch) und «Ola» (Leben, Gesundheit & Heilung) verbinden sich zu einer tiefen Quelle für Regeneration. Eingebettet in eine moderne Physiotherapie-Gemeinschaftspraxis begleite ich Sie mit achtsamer Atem- und Körpertherapie bei Erschöpfung, Atemwegsbeschwerden, chronischen Schmerzen und innerer Unruhe.",
        "Der Atem begleitet uns durch unser ganzes Leben. Er ist die Verbindung zwischen Körper und Psyche: Er reagiert auf das, was uns beschäftigt, auf unsere Gefühle, auf Anspannung, Bewegung und Körperhaltung. Als einzige autonome Körperfunktion lässt sich der Atem jedoch willentlich aktiv beeinflussen. In der Praxis PUSTERUM nutzen wir diese Verbindung als direkten Zugang, um Anspannung loszulassen, zur Ruhe zu kommen und neue Kraft zu schöpfen.",
        "textarea",
    ),
    "hero.trust_1": (
        "Krankenkassen-Zusatzversicherung (EMR • ASCA • EGK • Visana)",
        "Ganzheitlich-Integrative Atemtherapie (IKP)",
        "text",
    ),
    "hero.trust_2": (
        "Interdisziplinäre Praxis • OdA KT Methode",
        "In Gemeinschaftspraxis Physiotherapie",
        "text",
    ),
    "about.title": (
        "Atemtherapie Hā Ola",
        "PUSTERUM",
        "text",
    ),
    "about.subtitle": (
        "Dipl. Komplementärtherapeutin OdA KT • Gemeinschaftspraxis Physiotherapie",
        "Praxis für Atem- und Körpertherapie • Stephanie",
        "text",
    ),
    "about.meaning_title": (
        "Die Bedeutung von «Hā Ola»",
        "PUSTERUM [ˈpuːsdəʀomʔ]",
        "text",
    ),
    "about.meaning_text": (
        "«Hā» ist das hawaiianische Wort für den lebendigen Atem, den Lebenshauch und die geistige Lebenskraft (Mana). «Ola» steht für Leben, Gesundheit und ganzheitliche Heilung. Zusammen verkörpert Hā Ola den heilsamen Lebensatem: Wenn wir lernen, dem eigenen Atem wieder Raum zu geben, entfaltet sich die natürliche Selbstheilungskraft unseres Körpers.",
        "Pusterum ist ein dänisches Wort und bedeutet auf Deutsch „Raum zum Atmen“ oder im übertragenen Sinne „Atempause“, „Erholungspause“ bzw. „Zufluchtsort“. Setzt man das Wort wörtlich aus den dänischen Begriffen zusammen, beschreibt es einen Freiraum oder Moment, in dem man durchatmen und dem Alltagsstress entfliehen kann.",
        "textarea",
    ),
    "about.bio": (
        "Der Atem ist unser unmittelbarster Lebensausdruck. In meiner Praxis für Atemtherapie verbinde ich fundierte Methoden der Komplementärtherapie OdA KT mit achtsamer, ressourcenorientierter Körperarbeit. In enger Zusammenarbeit mit den Physiotherapeuten der Gemeinschaftspraxis schaffen wir einen ganzheitlichen Raum für nachhaltige Erholung und Gesundheit.",
        "Willkommen in meiner Praxis für Atem- und Körpertherapie. Mein Name ist Stephanie. Der Gesundheits- und komplementärtherapeutische Bereich interessierte mich schon früh. Einerseits lernte ich im Laufe der Jahre unterschiedliche wirksame Therapiemethoden für verschiedene gesundheitliche Beschwerden kennen. Andererseits absolvierte ich in diesem Bereich zwei Ausbildungen – als Ernährungscoach und als Yogalehrerin – blieb jedoch weiterhin meiner kaufmännischen Haupttätigkeit treu.",
        "textarea",
    ),
    "about.interdisciplinary": (
        "In der Gemeinschaftspraxis in den Räumlichkeiten der Physiotherapie schätze ich den interdisziplinären Austausch besonders. Während die Physiotherapie den Bewegungsapparat funktionell stärkt, setzt die Atemtherapie an den feinen vegetativen Regulationsprozessen an: Atemmuster vertiefen sich, Muskelverspannungen lockern sich und das Nervensystem findet zurück in die Entspannung.",
        "Mit der Zeit wuchs in mir der Wunsch nach einer beruflichen Veränderung, die mehr Sinnhaftigkeit und persönlichen Ausgleich bietet. Den entscheidenden Impuls für diese Neuausrichtung gab schliesslich eine gesundheitlich herausfordernde Phase. Bei meiner Suche nach neuen Wegen bin ich auf die Atem- und Körpertherapie gestossen; sie hat mich von Anfang an tief begeistert. Der lebensnotwendige Atem ist so selbstverständlich und allgegenwärtig und dennoch unbeachtet, wird er jedoch bewusst wahrgenommen ist er äusserst kraftvoll. Die Arbeit mit dem Atem fasziniert mich durch ihre Direktheit und ihre ganzheitliche Wirkung auf Körper und Geist. Heute nutze ich die Erfahrungen, die ich in den bisherigen Jahren meiner Ausbildung sammeln durfte, um Menschen auf ihrem Weg zu mehr Wohlbefinden, Selbstheilung und innerer Balance kompetent zu begleiten.",
        "textarea",
    ),
    "about.quote": (
        "„Wenn der Atem frei fliesst, findet der Mensch zu seiner inneren Mitte und Lebendigkeit zurück.“",
        "«So wie du atmest, so geht es dir. So wie es dir geht, so atmest du.»\n– Ganzheitlich-Integrative Atemtherapie (IKP)",
        "text",
    ),
    "about.portrait": (
        "/static/images/ste_aquarel.png",
        "/static/images/stephanie_portrait.jpg",
        "image",
    ),
    "about.badge_title": (
        "OdA KT Diplom",
        "Atemtherapie IKP",
        "text",
    ),
    "about.badge_subtitle": (
        "Branchenzertifikat KT",
        "Ganzheitlich-Integrativ",
        "text",
    ),
    "about.credential_1": (
        "Diplomierte Komplementärtherapeutin OdA KT",
        "2023 – heute: Ausbildung Ganzheitlich integrative Atemtherapie, IKP Institut für Körperzentrierte Psychotherapie",
        "text",
    ),
    "about.credential_2": (
        "EMR • ASCA • EGK • OdA KT anerkannt",
        "2014: Diplom Yogalehrerin, International Sivananda Yoga Vedanta Centre",
        "text",
    ),
    "about.credential_3": (
        "Eingebettet in Physiotherapie-Gemeinschaftspraxis",
        "2006 – 2007: Diplom ErnährungsCoach, Klubschule Migros",
        "text",
    ),
    "about.credential_4": (
        "Abrechnung via Zusatzversicherung (VVG)",
        "In Gemeinschaftspraxis Physiotherapie",
        "text",
    ),
    "competencies.badge": (
        "Anwendungsbereiche & Indikationen",
        "Methode & Wirkung",
        "text",
    ),
    "competencies.title": (
        "Wann hilft Atemtherapie?",
        "Was ist Atem- und Körpertherapie?",
        "text",
    ),
    "competencies.subtitle": (
        "Atemtherapie eignet sich sowohl zur gezielten Behandlung körperlicher und seelischer Beschwerden als auch zur präventiven Gesundheitsförderung und Entspannung.",
        "Atem- und Körpertherapie – die Brücke zwischen Körper und Psyche.",
        "textarea",
    ),
    "services.badge": (
        "Transparente Tarife & Kostenübernahme",
        "Transparente Tarife & Behandlungsablauf",
        "text",
    ),
    "services.subtitle": (
        "Jede Behandlung wird individuell auf Ihre aktuelle Lebenssituation und Ihre körperlichen Bedürfnisse abgestimmt.",
        "Jede Behandlung wird individuell auf Ihre aktuelle Lebenssituation und Ihre persönlichen Bedürfnisse abgestimmt.",
        "textarea",
    ),
    "services.insurance_title": (
        "Kostenübernahme durch die Zusatzversicherung",
        "Therapie & Rahmenbedingungen",
        "text",
    ),
    "services.insurance_text": (
        "Als diplomierte Komplementärtherapeutin OdA KT bin ich bei den meisten Schweizer Krankenkassen (EMR, ASCA, EGK, Visana) registriert. Wenn Sie über eine entsprechende Zusatzversicherung für Komplementärmedizin verfügen, übernimmt Ihre Krankenkasse in der Regel einen Großteil der Behandlungskosten (ohne ärztliche Überweisung). Bitte erkundigen Sie sich vorab bei Ihrer Versicherung über Ihre individuellen Konditionen.",
        "Als Atem- und Körpertherapeutin in Ausbildung am IKP begleite ich Sie einfühlsam und fundiert. Behandlungen finden in geschützter Atmosphäre in den Räumen der Gemeinschaftspraxis Physiotherapie statt.",
        "textarea",
    ),
    "services.insurance_label_1": (
        "EMR Erfahrungsmedizinisches Register",
        "Ganzheitlich integrative Atemtherapie IKP",
        "text",
    ),
    "services.insurance_label_2": (
        "ASCA Schweizerische Stiftung für Komplementärmedizin",
        "Gemeinschaftspraxis Physiotherapie",
        "text",
    ),
    "practice.name": (
        "Atemtherapie Hā Ola",
        "PUSTERUM",
        "text",
    ),
    "practice.description": (
        "Die Praxis für Atemtherapie Hā Ola ist eingebettet in eine modern ausgestattete Physiotherapie-Gemeinschaftspraxis. Ein geschützter, ruhiger Raum mit angenehmer Atmosphäre lädt dazu ein, den Alltag hinter sich zu lassen und ganz bei sich und dem eigenen Atem anzukommen.",
        "Die Praxis PUSTERUM für Atem- und Körpertherapie ist eingebettet in eine modern ausgestattete Physiotherapie-Gemeinschaftspraxis. Ein geschützter, ruhiger Raum mit angenehmer Atmosphäre lädt dazu ein, den Alltag hinter sich zu lassen und ganz bei sich und dem eigenen Atem anzukommen.",
        "textarea",
    ),
    "practice.email": (
        "kontakt@ha-ola-atem.ch",
        "kontakt@pusterum.ch",
        "email",
    ),
    "contact.subtitle": (
        "Haben Sie Fragen zur Methode oder möchten Sie einen Termin vereinbaren? Ich freue mich auf Ihre Nachricht oder Ihren Anruf.",
        "Haben Sie Fragen zur Atem- und Körpertherapie oder möchten Sie einen Termin vereinbaren? Ich freue mich auf Ihre Nachricht oder Ihren Anruf.",
        "textarea",
    ),
    "impressum.recognition_title": (
        "Berufsbezeichnung & Anerkennung",
        "Ausbildung & Methode",
        "text",
    ),
    "impressum.recognition_text": (
        "Dipl. Komplementärtherapeutin OdA KT (Methode Atemtherapie)\nMitglied: Berufsverband für Atemtherapie Schweiz\nKrankenkassen-Anerkennung: EMR, ASCA, EGK, Visana (Zusatzversicherung).",
        "PUSTERUM – Praxis für Atem- und Körpertherapie\nStephanie\nAusbildung Ganzheitlich integrative Atemtherapie, IKP Institut für Körperzentrierte Psychotherapie\nEingebettet in Physiotherapie-Gemeinschaftspraxis.",
        "textarea",
    ),
    "footer.tagline": (
        "Dipl. Komplementärtherapeutin OdA KT Methode Atemtherapie. Eingebettet in eine interdisziplinäre Physiotherapie-Gemeinschaftspraxis.",
        "PUSTERUM – Praxis für Atem- und Körpertherapie. Stephanie.\nAusbildung Ganzheitlich integrative Atemtherapie (IKP).\nEingebettet in eine interdisziplinäre Physiotherapie-Gemeinschaftspraxis.",
        "textarea",
    ),
}
# (table, column) -> (old default, new default)
FIELD_CHANGES: dict[tuple[str, str], tuple[str, str]] = {
    ("therapist_profiles", "full_name"): ("Atemtherapie Hā Ola", "Stephanie"),
    ("therapist_profiles", "title"): (
        "Dipl. Komplementärtherapeutin OdA KT",
        "Praxis für Atem- und Körpertherapie",
    ),
    ("therapist_profiles", "diploma"): (
        "Methode Atemtherapie",
        "Ganzheitlich-Integrative Atemtherapie (IKP)",
    ),
    ("therapist_profiles", "tagline"): (
        "Atemtherapie Hā Ola – Der heilsame Atem des Lebens.",
        "PUSTERUM – Raum zum Atmen.",
    ),
    ("therapist_profiles", "quote"): (
        "Hā Ola – Wenn der Atem frei fliesst, entfaltet sich das Leben in seiner ganzen Kraft.",
        "«So wie du atmest, so geht es dir. So wie es dir geht, so atmest du.»\n"
        "– Ganzheitlich-Integrative Atemtherapie (IKP)",
    ),
    ("therapist_profiles", "profile_image_url"): (
        "/static/images/ste_aquarel.png",
        "/static/images/stephanie_portrait.jpg",
    ),
    ("practice_info", "name"): (
        "Atemtherapie Hā Ola (in Gemeinschaftspraxis Physiotherapie)",
        "PUSTERUM – Atem- und Körpertherapie (in Gemeinschaftspraxis Physiotherapie)",
    ),
    ("practice_info", "email"): ("kontakt@ha-ola.ch", "kontakt@pusterum.ch"),
}


def _refresh_content_blocks(bind: sa.engine.Connection) -> None:
    blocks = sa.table(
        "content_blocks",
        sa.column("key", sa.String),
        sa.column("block_type", sa.String),
        sa.column("current_version_number", sa.Integer),
        sa.column("current_content", sa.Text),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    versions = sa.table(
        "content_block_versions",
        sa.column("id", sa.Uuid),
        sa.column("block_key", sa.String),
        sa.column("version_number", sa.Integer),
        sa.column("content", sa.Text),
        sa.column("author_name", sa.String),
        sa.column("change_summary", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(UTC)
    rows = bind.execute(
        sa.select(blocks.c.key, blocks.c.current_version_number, blocks.c.current_content).where(
            blocks.c.key.in_(CONTENT_CHANGES)
        )
    ).all()
    for key, version_number, current in rows:
        old_content, new_content, new_type = CONTENT_CHANGES[key]
        if current != old_content:
            continue
        next_version = version_number + 1
        bind.execute(
            sa.insert(versions).values(
                id=uuid4(),
                block_key=key,
                version_number=next_version,
                content=new_content,
                author_name=AUTHOR_NAME,
                change_summary=CHANGE_SUMMARY,
                created_at=now,
            )
        )
        bind.execute(
            sa.update(blocks)
            .where(blocks.c.key == key)
            .values(
                block_type=new_type,
                current_version_number=next_version,
                current_content=new_content,
                updated_at=now,
            )
        )


def _refresh_fields(bind: sa.engine.Connection, existing: set[str]) -> None:
    for (table_name, column_name), (old_value, new_value) in FIELD_CHANGES.items():
        if table_name not in existing:
            continue
        table = sa.table(table_name, sa.column(column_name, sa.Text))
        column = table.c[column_name]
        bind.execute(sa.update(table).where(column == old_value).values({column_name: new_value}))


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())
    if {"content_blocks", "content_block_versions"} <= existing:
        _refresh_content_blocks(bind)
    _refresh_fields(bind, existing)


def downgrade() -> None:
    # Intentionally a no-op: previous texts remain restorable via the version history.
    pass

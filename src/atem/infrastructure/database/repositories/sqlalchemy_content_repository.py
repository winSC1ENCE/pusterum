"""SQLAlchemy 2.0 Async implementation of IContentRepository with Versioning."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from atem.domain.exceptions import EntityNotFoundException
from atem.domain.interfaces.content_repository import IContentRepository
from atem.domain.models.content import ContentBlock, ContentBlockType, ContentBlockVersion
from atem.infrastructure.database.models.content import ContentBlockModel, ContentBlockVersionModel

DEFAULT_CONTENT_BLOCKS: list[dict[str, str]] = [
    {
        "key": "hero.badge",
        "section": "hero",
        "type": "text",
        "content": "PUSTERUM • Atem- und Körpertherapie • In Gemeinschaftspraxis Physiotherapie",
    },
    {
        "key": "hero.title",
        "section": "hero",
        "type": "text",
        "content": "PUSTERUM.",
    },
    {
        "key": "hero.subtitle",
        "section": "hero",
        "type": "text",
        "content": "Raum zum Atmen – die Brücke zwischen Körper und Psyche.",
    },
    {
        "key": "hero.text",
        "section": "hero",
        "type": "textarea",
        "content": "",
    },
    {
        "key": "hero.image",
        "section": "hero",
        "type": "image",
        "content": "/static/images/dandelion_hero.png",
    },
    {
        "key": "hero.trust_1",
        "section": "hero",
        "type": "text",
        "content": "Ganzheitlich-Integrative Atemtherapie (IKP)",
    },
    {
        "key": "hero.trust_2",
        "section": "hero",
        "type": "text",
        "content": "In Gemeinschaftspraxis Physiotherapie",
    },
    {
        "key": "about.title",
        "section": "about",
        "type": "text",
        "content": "PUSTERUM",
    },
    {
        "key": "about.subtitle",
        "section": "about",
        "type": "text",
        "content": "Praxis für Atem- und Körpertherapie • Stephanie",
    },
    {
        "key": "about.meaning_title",
        "section": "about",
        "type": "text",
        "content": "PUSTERUM [ˈpuːsdəʀomʔ]",
    },
    {
        "key": "about.meaning_text",
        "section": "about",
        "type": "textarea",
        "content": (
            "Pusterum ist ein dänisches Wort und bedeutet auf Deutsch „Raum zum Atmen“ oder im"
            " übertragenen Sinne „Atempause“, „Erholungspause“ bzw. „Zufluchtsort“. Setzt man das"
            " Wort wörtlich aus den dänischen Begriffen zusammen, beschreibt es einen Freiraum"
            " oder Moment, in dem man durchatmen und dem Alltagsstress entfliehen kann."
        ),
    },
    {
        "key": "about.bio",
        "section": "about",
        "type": "textarea",
        "content": (
            "Willkommen in meiner Praxis für Atem- und Körpertherapie. Mein Name ist Stephanie."
            " Der Gesundheits- und komplementärtherapeutische Bereich interessierte mich schon"
            " früh."
            " Einerseits lernte ich im Laufe der Jahre unterschiedliche wirksame Therapiemethoden"
            " für verschiedene gesundheitliche Beschwerden kennen. Andererseits absolvierte ich in"
            " diesem Bereich zwei Ausbildungen – als Ernährungscoach und als Yogalehrerin – blieb"
            " jedoch weiterhin meiner kaufmännischen Haupttätigkeit treu."
        ),
    },
    {
        "key": "about.interdisciplinary",
        "section": "about",
        "type": "textarea",
        "content": (
            "Mit der Zeit wuchs in mir der Wunsch nach einer beruflichen Veränderung, die mehr"
            " Sinnhaftigkeit und persönlichen Ausgleich bietet. Den entscheidenden Impuls für diese"
            " Neuausrichtung gab schliesslich eine gesundheitlich herausfordernde Phase. Bei meiner"
            " Suche nach neuen Wegen bin ich auf die Atem- und Körpertherapie gestossen; sie hat"
            " mich"
            " von Anfang an tief begeistert. Der lebensnotwendige Atem ist so selbstverständlich"
            " und"
            " allgegenwärtig und dennoch unbeachtet, wird er jedoch bewusst wahrgenommen ist er"
            " äusserst kraftvoll. Die Arbeit mit dem Atem fasziniert mich durch ihre Direktheit und"
            " ihre ganzheitliche Wirkung auf Körper und Geist. Heute nutze ich die Erfahrungen, die"
            " ich in den bisherigen Jahren meiner Ausbildung sammeln durfte, um Menschen auf ihrem"
            " Weg zu mehr Wohlbefinden, Selbstheilung und innerer Balance kompetent zu begleiten."
        ),
    },
    {
        "key": "about.quote",
        "section": "about",
        "type": "text",
        "content": (
            "«So wie du atmest, so geht es dir. So wie es dir geht, so atmest du.»\n"
            "– Ganzheitlich-Integrative Atemtherapie (IKP)"
        ),
    },
    {
        "key": "about.portrait",
        "section": "about",
        "type": "image",
        "content": "/static/images/stephanie_portrait.jpg",
    },
    {
        "key": "about.badge_title",
        "section": "about",
        "type": "text",
        "content": "Atemtherapie IKP",
    },
    {
        "key": "about.badge_subtitle",
        "section": "about",
        "type": "text",
        "content": "Ganzheitlich-Integrativ",
    },
    {
        "key": "about.credential_1",
        "section": "about",
        "type": "text",
        "content": (
            "2023 – heute: Ausbildung Ganzheitlich integrative Atemtherapie,"
            " IKP Institut für Körperzentrierte Psychotherapie"
        ),
    },
    {
        "key": "about.credential_2",
        "section": "about",
        "type": "text",
        "content": "2014: Diplom Yogalehrerin, International Sivananda Yoga Vedanta Centre",
    },
    {
        "key": "about.credential_3",
        "section": "about",
        "type": "text",
        "content": "2006 – 2007: Diplom ErnährungsCoach, Klubschule Migros",
    },
    {
        "key": "about.credential_4",
        "section": "about",
        "type": "text",
        "content": "In Gemeinschaftspraxis Physiotherapie",
    },
    {
        "key": "competencies.badge",
        "section": "competencies",
        "type": "text",
        "content": "Methode & Wirkung",
    },
    {
        "key": "competencies.title",
        "section": "competencies",
        "type": "text",
        "content": "Was ist Atem- und Körpertherapie?",
    },
    {
        "key": "competencies.subtitle",
        "section": "competencies",
        "type": "textarea",
        "content": "Atem- und Körpertherapie – die Brücke zwischen Körper und Psyche.",
    },
    {
        "key": "competencies.bridge_p1",
        "section": "competencies",
        "type": "textarea",
        "content": (
            "Der Atem begleitet uns durch unser ganzes Leben. Er ist die Verbindung zwischen"
            " Körper und Psyche: Er reagiert auf das, was uns beschäftigt, auf unsere Gefühle, auf"
            " Anspannung, Bewegung und Körperhaltung. Als einzige autonome Körperfunktion lässt"
            " sich"
            " der Atem jedoch auch willentlich aktiv beeinflussen."
        ),
    },
    {
        "key": "competencies.bridge_p2",
        "section": "competencies",
        "type": "textarea",
        "content": (
            "In der Atem- und Körpertherapie nutzen wir diese Verbindung des direkten Zugangs"
            " zur Psyche. Dabei steht die achtsame Selbstwahrnehmung im Mittelpunkt. Es geht nicht"
            " darum, richtig zu atmen oder den Atem bewusst zu steuern, sondern den Atem in seiner"
            " natürlichen Bewegung wahrzunehmen und den eigenen Körper bewusster zu erleben."
        ),
    },
    {
        "key": "competencies.bridge_p3",
        "section": "competencies",
        "type": "textarea",
        "content": (
            "Durch diese sanfte und achtsame Arbeit können körperliche und seelische Spannungen"
            " und Blockaden gelöst und nachhaltig positiv beeinflusst werden. Das begleitende"
            " therapeutische Gespräch unterstützt dabei, die gemachten körperlichen und"
            " persönlichen"
            " Erfahrungen wahrzunehmen, zu reflektieren und besser einzuordnen."
        ),
    },
    {
        "key": "competencies.bridge_p4",
        "section": "competencies",
        "type": "textarea",
        "content": (
            "Diese bewussten Wahrnehmungen von Atem und Körper können helfen, Anspannung"
            " loszulassen, zur Ruhe zu kommen und die eigenen Kräfte und Ressourcen wieder stärker"
            " zu spüren. So können mehr Vertrauen in den eigenen Körper, ein vertieftes"
            " Körpergefühl"
            " und ein bewussterer Umgang mit den Herausforderungen und Belastungen des Alltags"
            " entstehen."
        ),
    },
    {
        "key": "competencies.for_whom_title",
        "section": "competencies",
        "type": "text",
        "content": "Für wen eignet sich Atem- und Körpertherapie?",
    },
    {
        "key": "competencies.for_whom_subtitle",
        "section": "competencies",
        "type": "textarea",
        "content": (
            "Atem- und Körpertherapie wirkt in vielen Bereichen – vor allem nutzt sie den direkten"
            " Zugang zur Psyche. Dabei steht nicht nur der Atem im Mittelpunkt. Atem- und"
            " Körperübungen, Körperbehandlungen auf der Liege und das begleitende Gespräch ergänzen"
            " sich. Die Therapieform kann unter anderem in folgenden Bereichen unterstützen:"
        ),
    },
    {
        "key": "competencies.for_whom_1",
        "section": "competencies",
        "type": "text",
        "content": "Stress, Anspannung und innerer Unruhe",
    },
    {
        "key": "competencies.for_whom_2",
        "section": "competencies",
        "type": "text",
        "content": "Erschöpfung und dem Gefühl, nicht mehr richtig abschalten zu können",
    },
    {
        "key": "competencies.for_whom_3",
        "section": "competencies",
        "type": "text",
        "content": "Verspannungen und körperlichen Beschwerden",
    },
    {
        "key": "competencies.for_whom_4",
        "section": "competencies",
        "type": "text",
        "content": "eingeschränkter oder oberflächlicher Atmung",
    },
    {
        "key": "competencies.for_whom_5",
        "section": "competencies",
        "type": "text",
        "content": "Schlafproblemen",
    },
    {
        "key": "competencies.for_whom_6",
        "section": "competencies",
        "type": "text",
        "content": "Ängsten und emotionalen Belastungen",
    },
    {
        "key": "competencies.for_whom_7",
        "section": "competencies",
        "type": "text",
        "content": "dem Wunsch nach mehr Körperwahrnehmung, Ruhe und innerer Balance",
    },
    {
        "key": "competencies.for_whom_8",
        "section": "competencies",
        "type": "text",
        "content": "als Begleitung in besonderen Lebenssituationen",
    },
    {
        "key": "quotes.1.text",
        "section": "quotes",
        "type": "textarea",
        "content": (
            "«Die Fähigkeit, bewusst zu atmen, ist das Geschenk, das uns hilft,"
            " das Leben voll auszukosten.»"
        ),
    },
    {
        "key": "quotes.1.author",
        "section": "quotes",
        "type": "text",
        "content": "James Nestor",
    },
    {
        "key": "quotes.2.text",
        "section": "quotes",
        "type": "textarea",
        "content": (
            "«Der Atem ist das Werkzeug, mit dem wir die Chemie unseres Körpers verändern können.»"
        ),
    },
    {
        "key": "quotes.2.author",
        "section": "quotes",
        "type": "text",
        "content": "Wim Hof",
    },
    {
        "key": "quotes.3.text",
        "section": "quotes",
        "type": "textarea",
        "content": "«Der Atem ist das Tor zur Gegenwart.»",
    },
    {
        "key": "quotes.3.author",
        "section": "quotes",
        "type": "text",
        "content": "Eckhart Tolle",
    },
    {
        "key": "quotes.4.text",
        "section": "quotes",
        "type": "textarea",
        "content": ("«Durch den Atem können wir die Energie des Lebens selbst kontrollieren.»"),
    },
    {
        "key": "quotes.4.author",
        "section": "quotes",
        "type": "text",
        "content": "Swami Sivananda",
    },
    {
        "key": "quotes.5.text",
        "section": "quotes",
        "type": "textarea",
        "content": (
            "«Atmen ist der einzige Prozess, der sowohl unbewusst als auch bewusst"
            " ablaufen kann – genau hier liegt seine transformierende Kraft.»"
        ),
    },
    {
        "key": "quotes.5.author",
        "section": "quotes",
        "type": "text",
        "content": "Leonard Orr",
    },
    {
        "key": "quotes.6.text",
        "section": "quotes",
        "type": "textarea",
        "content": (
            "«Lachen entspannt den ganzen Körper – eine innere Massage, die mit"
            " einem tiefen Atem beginnt.»"
        ),
    },
    {
        "key": "quotes.6.author",
        "section": "quotes",
        "type": "text",
        "content": "Norman Cousins",
    },
    {
        "key": "services.badge",
        "section": "services",
        "type": "text",
        "content": "Transparente Tarife & Behandlungsablauf",
    },
    {
        "key": "services.title",
        "section": "services",
        "type": "text",
        "content": "Angebote & Behandlungsablauf",
    },
    {
        "key": "services.subtitle",
        "section": "services",
        "type": "textarea",
        "content": (
            "Jede Behandlung wird individuell auf Ihre aktuelle Lebenssituation und Ihre"
            " persönlichen Bedürfnisse abgestimmt."
        ),
    },
    {
        "key": "services.insurance_title",
        "section": "services",
        "type": "text",
        "content": "Therapie & Rahmenbedingungen",
    },
    {
        "key": "services.insurance_text",
        "section": "services",
        "type": "textarea",
        "content": (
            "Als Atem- und Körpertherapeutin in Ausbildung am IKP begleite ich Sie einfühlsam und"
            " fundiert. Behandlungen finden in geschützter Atmosphäre in den Räumen der"
            " Gemeinschaftspraxis Physiotherapie statt."
        ),
    },
    {
        "key": "services.insurance_label_1",
        "section": "services",
        "type": "text",
        "content": "Ganzheitlich integrative Atemtherapie IKP",
    },
    {
        "key": "services.insurance_label_2",
        "section": "services",
        "type": "text",
        "content": "Gemeinschaftspraxis Physiotherapie",
    },
    {
        "key": "practice.name",
        "section": "practice",
        "type": "text",
        "content": "PUSTERUM",
    },
    {
        "key": "practice.setting",
        "section": "practice",
        "type": "text",
        "content": "Gemeinschaftspraxis • Raum für Ruhe & Ankommen",
    },
    {
        "key": "practice.title",
        "section": "practice",
        "type": "text",
        "content": "Die Praxisräume",
    },
    {
        "key": "practice.description",
        "section": "practice",
        "type": "textarea",
        "content": (
            "Die Praxis PUSTERUM für Atem- und Körpertherapie ist eingebettet in eine modern"
            " ausgestattete Physiotherapie-Gemeinschaftspraxis. Ein geschützter, ruhiger Raum mit"
            " angenehmer Atmosphäre lädt dazu ein, den Alltag hinter sich zu lassen und ganz bei"
            " sich und dem eigenen Atem anzukommen."
        ),
    },
    {
        "key": "practice.address",
        "section": "practice",
        "type": "text",
        "content": "Kramgasse 42, 3011 Bern",
    },
    {
        "key": "practice.phone",
        "section": "practice",
        "type": "phone",
        "content": "+41 31 310 00 00",
    },
    {
        "key": "practice.email",
        "section": "practice",
        "type": "email",
        "content": "kontakt@pusterum.ch",
    },
    {
        "key": "practice.directions",
        "section": "practice",
        "type": "textarea",
        "content": (
            "Zentral in der Berner Altstadt gelegen, ca. 8 Gehminuten vom Hauptbahnhof Bern"
            " entfernt. Tram 6, 7, 8 oder 9 bis Haltestelle Zytglogge. Parkmöglichkeiten im"
            " Parkhaus Rathaus (3 Min. Fussweg)."
        ),
    },
    {
        "key": "practice.accessibility",
        "section": "practice",
        "type": "textarea",
        "content": (
            "Die Praxisräume befinden sich im 1. Stock eines historischen Altstadthauses. Ein"
            " rollstuhlgängiger Lift und ein barrierefreier Zugang sind vorhanden."
        ),
    },
    {
        "key": "practice.interior_image",
        "section": "practice",
        "type": "image",
        "content": "/static/images/practice_interior.png",
    },
    {
        "key": "contact.badge",
        "section": "contact",
        "type": "text",
        "content": "Verbindung aufnehmen",
    },
    {
        "key": "contact.title",
        "section": "contact",
        "type": "text",
        "content": "Kontakt & Terminanfrage",
    },
    {
        "key": "contact.subtitle",
        "section": "contact",
        "type": "textarea",
        "content": (
            "Haben Sie Fragen zur Atem- und Körpertherapie oder möchten Sie einen Termin"
            " vereinbaren? Ich freue mich auf Ihre Nachricht oder Ihren Anruf."
        ),
    },
    {
        "key": "contact.phone_label",
        "section": "contact",
        "type": "text",
        "content": "Telefonische Erreichbarkeit",
    },
    {
        "key": "contact.email_label",
        "section": "contact",
        "type": "text",
        "content": "E-Mail",
    },
    {
        "key": "contact.privacy_note",
        "section": "contact",
        "type": "textarea",
        "content": (
            "Ihre Angaben werden streng vertraulich behandelt und ausschließlich zur"
            " Beantwortung Ihrer Anfrage genutzt."
        ),
    },
    {
        "key": "impressum.title",
        "section": "impressum",
        "type": "text",
        "content": "Impressum",
    },
    {
        "key": "impressum.responsible_title",
        "section": "impressum",
        "type": "text",
        "content": "Verantwortliche Stelle",
    },
    {
        "key": "impressum.recognition_title",
        "section": "impressum",
        "type": "text",
        "content": "Ausbildung & Methode",
    },
    {
        "key": "impressum.recognition_text",
        "section": "impressum",
        "type": "textarea",
        "content": (
            "PUSTERUM – Praxis für Atem- und Körpertherapie\nStephanie\n"
            "Ausbildung Ganzheitlich integrative Atemtherapie, IKP Institut für Körperzentrierte"
            " Psychotherapie\n"
            "Eingebettet in Physiotherapie-Gemeinschaftspraxis."
        ),
    },
    {
        "key": "impressum.disclaimer_title",
        "section": "impressum",
        "type": "text",
        "content": "Haftungsausschluss",
    },
    {
        "key": "impressum.disclaimer_text",
        "section": "impressum",
        "type": "textarea",
        "content": (
            "Die Inhalte dieser Webseite wurden mit grösstmöglicher Sorgfalt erstellt. Für die"
            " Richtigkeit, Vollständigkeit und Aktualität der Inhalte übernimmt die"
            " Praxisinhaberin keine Gewähr. Die bereitgestellten Informationen stellen keine"
            " medizinische Diagnose dar und ersetzen nicht die Konsultation einer Ärztin oder"
            " eines Arztes."
        ),
    },
    {
        "key": "datenschutz.title",
        "section": "datenschutz",
        "type": "text",
        "content": "Datenschutzerklärung",
    },
    {
        "key": "datenschutz.intro",
        "section": "datenschutz",
        "type": "textarea",
        "content": (
            "Der Schutz Ihrer persönlichen Daten ist mir ein wichtiges Anliegen. Diese"
            " Datenschutzerklärung informiert Sie über die Erhebung und Bearbeitung"
            " personenbezogener Daten beim Besuch dieser Website und bei der Kontaktaufnahme"
            " gemäss dem Schweizerischen Datenschutzgesetz (DSG)."
        ),
    },
    {
        "key": "datenschutz.sec1_title",
        "section": "datenschutz",
        "type": "text",
        "content": "1. Verantwortliche Person",
    },
    {
        "key": "datenschutz.sec1_text",
        "section": "datenschutz",
        "type": "textarea",
        "content": (
            "Verantwortlich für die Datenbearbeitung auf dieser Webseite ist die"
            " Praxisinhaberin gemäss Angaben im Impressum."
        ),
    },
    {
        "key": "datenschutz.sec2_title",
        "section": "datenschutz",
        "type": "text",
        "content": "2. Erhebung von Daten bei Kontaktaufnahme",
    },
    {
        "key": "datenschutz.sec2_text",
        "section": "datenschutz",
        "type": "textarea",
        "content": (
            "Wenn Sie das Kontaktformular ausfüllen oder eine E-Mail senden, werden die von Ihnen"
            " angegebenen Kontaktdaten (Name, E-Mail-Adresse, Telefonnummer, Nachricht)"
            " gespeichert, um Ihre Anfrage zu bearbeiten und allfällige Anschlussfragen zu"
            " klären. Diese Daten werden ohne Ihre ausdrückliche Zustimmung niemals an Dritte"
            " weitergegeben."
        ),
    },
    {
        "key": "datenschutz.sec3_title",
        "section": "datenschutz",
        "type": "text",
        "content": "3. Server-Logfiles & Sicherheit",
    },
    {
        "key": "datenschutz.sec3_text",
        "section": "datenschutz",
        "type": "textarea",
        "content": (
            "Beim Aufruf dieser Website erhebt der Hosting-Provider (Standort Schweiz /"
            " Deutschland mit ISO 27001 Zertifizierung) automatisch technische Informationen"
            " (IP-Adresse, Datum, Uhrzeit, Browsertyp). Diese Daten dienen ausschließlich der"
            " Systemsicherheit und Fehleranalyse."
        ),
    },
    {
        "key": "datenschutz.sec4_title",
        "section": "datenschutz",
        "type": "text",
        "content": "4. Ihre Rechte",
    },
    {
        "key": "datenschutz.sec4_text",
        "section": "datenschutz",
        "type": "textarea",
        "content": (
            "Sie haben jederzeit das Recht auf unentgeltliche Auskunft über Ihre gespeicherten"
            " personenbezogenen Daten, deren Herkunft und den Zweck der Datenbearbeitung sowie"
            " ein Recht auf Berichtigung, Sperrung oder Löschung dieser Daten."
        ),
    },
    {
        "key": "footer.tagline",
        "section": "footer",
        "type": "textarea",
        "content": (
            "PUSTERUM – Praxis für Atem- und Körpertherapie. Stephanie.\n"
            "Ausbildung Ganzheitlich integrative Atemtherapie (IKP).\n"
            "Eingebettet in eine interdisziplinäre Physiotherapie-Gemeinschaftspraxis."
        ),
    },
    {
        "key": "impressum.webdesign_title",
        "section": "impressum",
        "type": "text",
        "content": "Konzeption & Webdesign",
    },
    {
        "key": "impressum.webdesign_by",
        "section": "impressum",
        "type": "text",
        "content": "Webdesign bynico.",
    },
    {
        "key": "impressum.webdesign_notice",
        "section": "impressum",
        "type": "text",
        "content": "«bynico.» ist eine eingetragene Marke von Nicolas Mischler.",
    },
    {
        "key": "footer.webdesign",
        "section": "footer",
        "type": "text",
        "content": "Webdesign bynico.",
    },
    {
        "key": "footer.trademark_notice",
        "section": "footer",
        "type": "text",
        "content": "«bynico.» ist eine eingetragene Marke von Nicolas Mischler.",
    },
]


class SqlAlchemyContentRepository(IContentRepository):
    """PostgreSQL / SQLite async repository for live website content and versioning."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, model: ContentBlockModel) -> ContentBlock:
        return ContentBlock(
            id=UUID(int=0),  # String key is primary identifier
            key=model.key,
            section=model.section,
            block_type=ContentBlockType(model.block_type),
            current_version_number=model.current_version_number,
            current_content=model.current_content,
            updated_at=model.updated_at,
        )

    def _to_version_entity(self, model: ContentBlockVersionModel) -> ContentBlockVersion:
        return ContentBlockVersion(
            id=model.id,
            block_key=model.block_key,
            version_number=model.version_number,
            content=model.content,
            author_id=model.author_id,
            author_name=model.author_name,
            change_summary=model.change_summary,
            created_at=model.created_at,
        )

    async def _ensure_seed_data(self) -> None:
        """Seed initial default content blocks and ensure any missing defaults are added."""
        existing_stmt = select(ContentBlockModel.key)
        existing_res = await self._session.execute(existing_stmt)
        existing_keys = set(existing_res.scalars().all())

        missing_blocks = [
            item for item in DEFAULT_CONTENT_BLOCKS if item["key"] not in existing_keys
        ]
        if missing_blocks:
            now = datetime.now(UTC)
            for item in missing_blocks:
                block_model = ContentBlockModel(
                    key=item["key"],
                    section=item["section"],
                    block_type=item["type"],
                    current_version_number=1,
                    current_content=item["content"],
                    updated_at=now,
                )
                self._session.add(block_model)
                version_model = ContentBlockVersionModel(
                    block_key=item["key"],
                    version_number=1,
                    content=item["content"],
                    author_name="System Initialisierung",
                    change_summary="Standard-Inhalt",
                    created_at=now,
                )
                self._session.add(version_model)
            await self._session.commit()

    async def get_block(self, key: str) -> ContentBlock | None:
        await self._ensure_seed_data()
        stmt = select(ContentBlockModel).where(ContentBlockModel.key == key)
        res = await self._session.execute(stmt)
        model = res.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_all_blocks(self) -> dict[str, ContentBlock]:
        await self._ensure_seed_data()
        stmt = select(ContentBlockModel)
        res = await self._session.execute(stmt)
        models = res.scalars().all()
        return {m.key: self._to_entity(m) for m in models}

    async def save_version(
        self,
        key: str,
        content: str,
        author_name: str,
        author_id: UUID | None = None,
        change_summary: str | None = None,
    ) -> ContentBlockVersion:
        await self._ensure_seed_data()
        stmt = select(ContentBlockModel).where(ContentBlockModel.key == key)
        res = await self._session.execute(stmt)
        block_model = res.scalar_one_or_none()

        now = datetime.now(UTC)
        if not block_model:
            # Create new block
            new_version_num = 1
            block_model = ContentBlockModel(
                key=key,
                section=key.split(".", maxsplit=1)[0] if "." in key else "general",
                block_type=ContentBlockType.TEXT.value,
                current_version_number=new_version_num,
                current_content=content,
                updated_at=now,
            )
            self._session.add(block_model)
        else:
            new_version_num = block_model.current_version_number + 1
            block_model.current_version_number = new_version_num
            block_model.current_content = content
            block_model.updated_at = now

        version_model = ContentBlockVersionModel(
            block_key=key,
            version_number=new_version_num,
            content=content,
            author_id=author_id,
            author_name=author_name,
            change_summary=change_summary or "Aktualisierung",
            created_at=now,
        )
        self._session.add(version_model)
        await self._session.commit()
        await self._session.refresh(version_model)
        return self._to_version_entity(version_model)

    async def get_version_history(self, key: str) -> list[ContentBlockVersion]:
        await self._ensure_seed_data()
        stmt = (
            select(ContentBlockVersionModel)
            .where(ContentBlockVersionModel.block_key == key)
            .order_by(ContentBlockVersionModel.version_number.desc())
        )
        res = await self._session.execute(stmt)
        models = res.scalars().all()
        return [self._to_version_entity(m) for m in models]

    async def restore_version(
        self,
        key: str,
        target_version_number: int,
        author_name: str,
        author_id: UUID | None = None,
    ) -> ContentBlockVersion:
        await self._ensure_seed_data()
        stmt = select(ContentBlockVersionModel).where(
            ContentBlockVersionModel.block_key == key,
            ContentBlockVersionModel.version_number == target_version_number,
        )
        res = await self._session.execute(stmt)
        target_model = res.scalar_one_or_none()
        if not target_model:
            raise EntityNotFoundException("ContentBlockVersion", f"{key}#v{target_version_number}")

        summary = f"Wiederherstellung von Version v{target_version_number}"
        return await self.save_version(
            key=key,
            content=target_model.content,
            author_name=author_name,
            author_id=author_id,
            change_summary=summary,
        )

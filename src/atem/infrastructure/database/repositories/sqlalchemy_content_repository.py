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
        "content": "Atemtherapie Hā Ola • OdA KT • In Gemeinschaftspraxis Physiotherapie",
    },
    {
        "key": "hero.title",
        "section": "hero",
        "type": "text",
        "content": "Hā Ola.",
    },
    {
        "key": "hero.subtitle",
        "section": "hero",
        "type": "text",
        "content": "Der heilsame Atem des Lebens.",
    },
    {
        "key": "hero.text",
        "section": "hero",
        "type": "textarea",
        "content": (
            "«Hā» (Atem, Lebenshauch) und «Ola» (Leben, Gesundheit & Heilung) verbinden sich"
            " zu einer tiefen Quelle für Regeneration. Eingebettet in eine moderne"
            " Physiotherapie-Gemeinschaftspraxis begleite ich Sie mit achtsamer Atem- und"
            " Körpertherapie bei Erschöpfung, Atemwegsbeschwerden, chronischen Schmerzen"
            " und innerer Unruhe."
        ),
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
        "content": "Krankenkassen-Zusatzversicherung (EMR • ASCA • EGK • Visana)",
    },
    {
        "key": "hero.trust_2",
        "section": "hero",
        "type": "text",
        "content": "Interdisziplinäre Praxis • OdA KT Methode",
    },
    {
        "key": "about.title",
        "section": "about",
        "type": "text",
        "content": "Atemtherapie Hā Ola",
    },
    {
        "key": "about.subtitle",
        "section": "about",
        "type": "text",
        "content": "Dipl. Komplementärtherapeutin OdA KT • Gemeinschaftspraxis Physiotherapie",
    },
    {
        "key": "about.meaning_title",
        "section": "about",
        "type": "text",
        "content": "Die Bedeutung von «Hā Ola»",
    },
    {
        "key": "about.meaning_text",
        "section": "about",
        "type": "textarea",
        "content": (
            "«Hā» ist das hawaiianische Wort für den lebendigen Atem, den"
            " Lebenshauch und die geistige Lebenskraft (Mana). «Ola» steht für Leben,"
            " Gesundheit und ganzheitliche Heilung. Zusammen verkörpert Hā Ola den"
            " heilsamen Lebensatem: Wenn wir lernen, dem eigenen Atem wieder Raum zu"
            " geben, entfaltet sich die natürliche Selbstheilungskraft unseres Körpers."
        ),
    },
    {
        "key": "about.bio",
        "section": "about",
        "type": "textarea",
        "content": (
            "Der Atem ist unser unmittelbarster Lebensausdruck. In meiner Praxis für"
            " Atemtherapie verbinde ich fundierte Methoden der Komplementärtherapie OdA KT mit"
            " achtsamer, ressourcenorientierter Körperarbeit. In enger Zusammenarbeit mit den"
            " Physiotherapeuten der Gemeinschaftspraxis schaffen wir einen ganzheitlichen Raum"
            " für nachhaltige Erholung und Gesundheit."
        ),
    },
    {
        "key": "about.interdisciplinary",
        "section": "about",
        "type": "textarea",
        "content": (
            "In der Gemeinschaftspraxis in den Räumlichkeiten der Physiotherapie schätze ich den"
            " interdisziplinären Austausch besonders. Während die Physiotherapie den"
            " Bewegungsapparat funktionell stärkt, setzt die Atemtherapie an den feinen vegetativen"
            " Regulationsprozessen an: Atemmuster vertiefen sich, Muskelverspannungen lockern sich"
            " und das Nervensystem findet zurück in die Entspannung."
        ),
    },
    {
        "key": "about.quote",
        "section": "about",
        "type": "text",
        "content": (
            "„Wenn der Atem frei fliesst, findet der Mensch zu seiner inneren Mitte und"
            " Lebendigkeit zurück.“"
        ),
    },
    {
        "key": "about.portrait",
        "section": "about",
        "type": "image",
        "content": "/static/images/ste_aquarel.png",
    },
    {
        "key": "about.badge_title",
        "section": "about",
        "type": "text",
        "content": "OdA KT Diplom",
    },
    {
        "key": "about.badge_subtitle",
        "section": "about",
        "type": "text",
        "content": "Branchenzertifikat KT",
    },
    {
        "key": "about.credential_1",
        "section": "about",
        "type": "text",
        "content": "Diplomierte Komplementärtherapeutin OdA KT",
    },
    {
        "key": "about.credential_2",
        "section": "about",
        "type": "text",
        "content": "EMR • ASCA • EGK • OdA KT anerkannt",
    },
    {
        "key": "about.credential_3",
        "section": "about",
        "type": "text",
        "content": "Eingebettet in Physiotherapie-Gemeinschaftspraxis",
    },
    {
        "key": "about.credential_4",
        "section": "about",
        "type": "text",
        "content": "Abrechnung via Zusatzversicherung (VVG)",
    },
    {
        "key": "competencies.badge",
        "section": "competencies",
        "type": "text",
        "content": "Anwendungsbereiche & Indikationen",
    },
    {
        "key": "competencies.title",
        "section": "competencies",
        "type": "text",
        "content": "Wann hilft Atemtherapie?",
    },
    {
        "key": "competencies.subtitle",
        "section": "competencies",
        "type": "textarea",
        "content": (
            "Atemtherapie eignet sich sowohl zur gezielten Behandlung körperlicher und"
            " seelischer Beschwerden als auch zur präventiven Gesundheitsförderung und"
            " Entspannung."
        ),
    },
    {
        "key": "competencies.1.title",
        "section": "competencies",
        "type": "text",
        "content": "Atemwegserkrankungen & Rehabilitation",
    },
    {
        "key": "competencies.1.description",
        "section": "competencies",
        "type": "textarea",
        "content": (
            "Begleitung bei Asthma, COPD, Hyperventilation, Long Covid und chronischer"
            " Kurzatmigkeit. Gezielte Schulung der Zwerchfellatmung."
        ),
    },
    {
        "key": "competencies.2.title",
        "section": "competencies",
        "type": "text",
        "content": "Stress, Erschöpfung & Schlafstörungen",
    },
    {
        "key": "competencies.2.description",
        "section": "competencies",
        "type": "textarea",
        "content": (
            "Regulierung des vegetativen Nervensystems bei Burnout-Symptomen, chronischer"
            " Müdigkeit, innerer Unruhe und Ein- sowie Durchschlafproblemen."
        ),
    },
    {
        "key": "competencies.3.title",
        "section": "competencies",
        "type": "text",
        "content": "Schmerzen, Verspannungen & Trauma",
    },
    {
        "key": "competencies.3.description",
        "section": "competencies",
        "type": "textarea",
        "content": (
            "Lösung muskulärer Blockaden im Nacken-, Schulter- und Rückenbereich. Achtsame"
            " Körperarbeit bei psychosomatischen Schmerzmustern."
        ),
    },
    {
        "key": "services.badge",
        "section": "services",
        "type": "text",
        "content": "Transparente Tarife & Kostenübernahme",
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
            " körperlichen Bedürfnisse abgestimmt."
        ),
    },
    {
        "key": "services.insurance_title",
        "section": "services",
        "type": "text",
        "content": "Kostenübernahme durch die Zusatzversicherung",
    },
    {
        "key": "services.insurance_text",
        "section": "services",
        "type": "textarea",
        "content": (
            "Als diplomierte Komplementärtherapeutin OdA KT bin ich bei den meisten Schweizer"
            " Krankenkassen (EMR, ASCA, EGK, Visana) registriert. Wenn Sie über eine"
            " entsprechende Zusatzversicherung für Komplementärmedizin verfügen, übernimmt Ihre"
            " Krankenkasse in der Regel einen Großteil der Behandlungskosten (ohne ärztliche"
            " Überweisung). Bitte erkundigen Sie sich vorab bei Ihrer Versicherung über Ihre"
            " individuellen Konditionen."
        ),
    },
    {
        "key": "services.insurance_label_1",
        "section": "services",
        "type": "text",
        "content": "EMR Erfahrungsmedizinisches Register",
    },
    {
        "key": "services.insurance_label_2",
        "section": "services",
        "type": "text",
        "content": "ASCA Schweizerische Stiftung für Komplementärmedizin",
    },
    {
        "key": "practice.name",
        "section": "practice",
        "type": "text",
        "content": "Atemtherapie Hā Ola",
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
            "Die Praxis für Atemtherapie Hā Ola ist eingebettet in eine modern ausgestattete"
            " Physiotherapie-Gemeinschaftspraxis. Ein geschützter, ruhiger Raum mit angenehmer"
            " Atmosphäre lädt dazu ein, den Alltag hinter sich zu lassen und ganz bei sich und"
            " dem eigenen Atem anzukommen."
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
        "content": "kontakt@ha-ola-atem.ch",
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
            "Haben Sie Fragen zur Methode oder möchten Sie einen Termin vereinbaren? Ich"
            " freue mich auf Ihre Nachricht oder Ihren Anruf."
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
        "content": "Berufsbezeichnung & Anerkennung",
    },
    {
        "key": "impressum.recognition_text",
        "section": "impressum",
        "type": "textarea",
        "content": (
            "Dipl. Komplementärtherapeutin OdA KT (Methode Atemtherapie)\nMitglied:"
            " Berufsverband für Atemtherapie Schweiz\nKrankenkassen-Anerkennung: EMR, ASCA, EGK,"
            " Visana (Zusatzversicherung)."
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
        "type": "text",
        "content": (
            "Dipl. Komplementärtherapeutin OdA KT Methode Atemtherapie. Eingebettet in eine"
            " interdisziplinäre Physiotherapie-Gemeinschaftspraxis."
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

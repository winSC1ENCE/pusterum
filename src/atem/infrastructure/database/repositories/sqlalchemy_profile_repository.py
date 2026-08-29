"""SQLAlchemy implementation of IProfileRepository."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from atem.domain.interfaces.profile_repository import IProfileRepository
from atem.domain.models.profile import Competency, PracticeInfo, ServiceOffering, TherapistProfile
from atem.infrastructure.database.models.profile import (
    CompetencyModel,
    PracticeInfoModel,
    ServiceOfferingModel,
    TherapistProfileModel,
)


class SqlAlchemyProfileRepository(IProfileRepository):
    """SQLAlchemy 2.0 Async repository for Therapist Profile and Content."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_profile(self) -> TherapistProfile:
        """Fetch the active profile or default if empty."""
        stmt = select(TherapistProfileModel).limit(1)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            # Default placeholder profile for initialization
            return TherapistProfile(
                full_name="Atemtherapie Haʻa Ola",
                title="Dipl. Komplementärtherapeutin OdA KT",
                diploma="Methode Atemtherapie",
                tagline="Atemtherapie Haʻa Ola – Der heilsame Atem des Lebens.",
                bio=(
                    "Willkommen bei Atemtherapie Haʻa Ola. Der Name verbindet die "
                    "hawaiianischen Begriffe «Haʻa» (Atem) und «Ola» (Leben, Gesundheit, Heilung). "
                    "In unserer Gemeinschaftspraxis in den Räumlichkeiten der Physiotherapie "
                    "begleite ich Sie mit achtsamer Atem- und Körperarbeit auf Ihrem Weg zu "
                    "nachhaltiger Genesung, Entlastung und innerer Balance."
                ),
                quote=(
                    "Haʻa Ola – Wenn der Atem frei fliesst, "
                    "entfaltet sich das Leben in seiner ganzen Kraft."
                ),
                profile_image_url="/static/images/therapist_portrait.png",
                booking_external_url=None,
            )

        return TherapistProfile(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            full_name=model.full_name,
            title=model.title,
            diploma=model.diploma,
            tagline=model.tagline,
            bio=model.bio,
            quote=model.quote,
            profile_image_url=model.profile_image_url,
            booking_external_url=model.booking_external_url,
        )

    async def save_profile(self, profile: TherapistProfile) -> TherapistProfile:
        """Create or update profile."""
        stmt = select(TherapistProfileModel).limit(1)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            model = TherapistProfileModel(
                id=profile.id,
                full_name=profile.full_name,
                title=profile.title,
                diploma=profile.diploma,
                tagline=profile.tagline,
                bio=profile.bio,
                quote=profile.quote,
                profile_image_url=profile.profile_image_url,
                booking_external_url=profile.booking_external_url,
            )
            self._session.add(model)
        else:
            model.full_name = profile.full_name
            model.title = profile.title
            model.diploma = profile.diploma
            model.tagline = profile.tagline
            model.bio = profile.bio
            model.quote = profile.quote
            model.profile_image_url = profile.profile_image_url
            model.booking_external_url = profile.booking_external_url

        await self._session.flush()
        profile.id = model.id
        return profile

    async def get_competencies(self, *, active_only: bool = True) -> list[Competency]:
        """Fetch list of competencies."""
        stmt = select(CompetencyModel).order_by(CompetencyModel.sort_order.asc())
        if active_only:
            stmt = stmt.where(CompetencyModel.is_active.is_(True))
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [
            Competency(
                id=m.id,
                created_at=m.created_at,
                updated_at=m.updated_at,
                title=m.title,
                description=m.description,
                icon_name=m.icon_name,
                sort_order=m.sort_order,
                is_active=m.is_active,
            )
            for m in models
        ]

    async def get_services(self, *, active_only: bool = True) -> list[ServiceOffering]:
        """Fetch list of active service offerings."""
        stmt = select(ServiceOfferingModel).order_by(ServiceOfferingModel.sort_order.asc())
        if active_only:
            stmt = stmt.where(ServiceOfferingModel.is_active.is_(True))
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [
            ServiceOffering(
                id=m.id,
                created_at=m.created_at,
                updated_at=m.updated_at,
                title=m.title,
                slug=m.slug,
                subtitle=m.subtitle,
                description=m.description,
                duration_minutes=m.duration_minutes,
                price_chf=m.price_chf,
                is_health_insurance_recognized=m.is_health_insurance_recognized,
                sort_order=m.sort_order,
                is_active=m.is_active,
            )
            for m in models
        ]

    async def get_service_by_id(self, service_id: UUID) -> ServiceOffering | None:
        """Fetch single service offering by ID."""
        stmt = select(ServiceOfferingModel).where(ServiceOfferingModel.id == service_id)
        result = await self._session.execute(stmt)
        m = result.scalar_one_or_none()
        if not m:
            return None
        return ServiceOffering(
            id=m.id,
            created_at=m.created_at,
            updated_at=m.updated_at,
            title=m.title,
            slug=m.slug,
            subtitle=m.subtitle,
            description=m.description,
            duration_minutes=m.duration_minutes,
            price_chf=m.price_chf,
            is_health_insurance_recognized=m.is_health_insurance_recognized,
            sort_order=m.sort_order,
            is_active=m.is_active,
        )

    async def save_service(self, service: ServiceOffering) -> ServiceOffering:
        """Create or update a service offering."""
        stmt = select(ServiceOfferingModel).where(ServiceOfferingModel.id == service.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            model = ServiceOfferingModel(
                id=service.id,
                title=service.title,
                slug=service.slug,
                subtitle=service.subtitle,
                description=service.description,
                duration_minutes=service.duration_minutes,
                price_chf=service.price_chf,
                is_health_insurance_recognized=service.is_health_insurance_recognized,
                sort_order=service.sort_order,
                is_active=service.is_active,
            )
            self._session.add(model)
        else:
            model.title = service.title
            model.slug = service.slug
            model.subtitle = service.subtitle
            model.description = service.description
            model.duration_minutes = service.duration_minutes
            model.price_chf = service.price_chf
            model.is_health_insurance_recognized = service.is_health_insurance_recognized
            model.sort_order = service.sort_order
            model.is_active = service.is_active

        await self._session.flush()
        service.id = model.id
        return service

    async def delete_service(self, service_id: UUID) -> bool:
        """Delete a service offering by ID."""
        stmt = delete(ServiceOfferingModel).where(ServiceOfferingModel.id == service_id)
        result = await self._session.execute(stmt)
        return bool(getattr(result, "rowcount", 0) > 0)

    async def get_practice_info(self) -> PracticeInfo | None:
        """Fetch practice location info."""
        stmt = select(PracticeInfoModel).limit(1)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return PracticeInfo(
                name="Atemtherapie Haʻa Ola (in Gemeinschaftspraxis Physiotherapie)",
                street="Praxisgasse 10",
                zip_code="3000",
                city="Bern",
                canton="BE",
                country="Schweiz",
                phone="+41 31 123 45 67",
                email="kontakt@haa-ola.ch",
                directions_info=(
                    "In den Praxisräumen der Physiotherapie-Gemeinschaftspraxis. "
                    "Zentral gelegen und bestens mit ÖV und Auto erreichbar."
                ),
                accessibility_info=(
                    "Vollständig rollstuhlgängig (Lift im Haus, ebenerdiger Zugang)."
                ),
            )
        return PracticeInfo(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            name=model.name,
            street=model.street,
            zip_code=model.zip_code,
            city=model.city,
            canton=model.canton,
            country=model.country,
            phone=model.phone,
            email=model.email,
            directions_info=model.directions_info,
            accessibility_info=model.accessibility_info,
            latitude=model.latitude,
            longitude=model.longitude,
        )

    async def save_practice_info(self, practice: PracticeInfo) -> PracticeInfo:
        """Save practice location info."""
        stmt = select(PracticeInfoModel).limit(1)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            model = PracticeInfoModel(
                id=practice.id,
                name=practice.name,
                street=practice.street,
                zip_code=practice.zip_code,
                city=practice.city,
                canton=practice.canton,
                country=practice.country,
                phone=practice.phone,
                email=practice.email,
                directions_info=practice.directions_info,
                accessibility_info=practice.accessibility_info,
                latitude=practice.latitude,
                longitude=practice.longitude,
            )
            self._session.add(model)
        else:
            model.name = practice.name
            model.street = practice.street
            model.zip_code = practice.zip_code
            model.city = practice.city
            model.canton = practice.canton
            model.country = practice.country
            model.phone = practice.phone
            model.email = practice.email
            model.directions_info = practice.directions_info
            model.accessibility_info = practice.accessibility_info
            model.latitude = practice.latitude
            model.longitude = practice.longitude

        await self._session.flush()
        practice.id = model.id
        return practice

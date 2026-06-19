from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.linkedin_profile import LinkedInProfile
from app.utils.linkedin_links import ParsedLinkedInProfile, normalize_linkedin_profile


class LinkedInProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active_for_user(self, user_id: int) -> list[LinkedInProfile]:
        result = await self._session.execute(
            select(LinkedInProfile).where(
                LinkedInProfile.user_id == user_id,
                LinkedInProfile.is_active.is_(True),
            )
        )
        return list(result.scalars().all())

    async def list_all_for_user(self, user_id: int) -> list[LinkedInProfile]:
        result = await self._session.execute(
            select(LinkedInProfile)
            .where(LinkedInProfile.user_id == user_id, LinkedInProfile.is_active.is_(True))
            .order_by(LinkedInProfile.id)
        )
        return list(result.scalars().all())

    async def add_profile(
        self,
        user_id: int,
        raw: str,
        *,
        title: str | None = None,
        linkedin_urn: str | None = None,
    ) -> str | None:
        try:
            parsed = normalize_linkedin_profile(raw)
        except ValueError:
            return None

        return await self.add_parsed(user_id, parsed, title=title, linkedin_urn=linkedin_urn)

    async def add_parsed(
        self,
        user_id: int,
        parsed: ParsedLinkedInProfile,
        *,
        title: str | None = None,
        linkedin_urn: str | None = None,
    ) -> str | None:
        result = await self._session.execute(
            select(LinkedInProfile).where(
                LinkedInProfile.user_id == user_id,
                LinkedInProfile.profile_slug == parsed.slug,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            if existing.is_active:
                return "exists"
            existing.is_active = True
            if title:
                existing.title = title
            if linkedin_urn:
                existing.linkedin_urn = linkedin_urn
            await self._session.flush()
            return "new"

        profile = LinkedInProfile(
            user_id=user_id,
            profile_url=parsed.url,
            profile_slug=parsed.slug,
            profile_type=parsed.profile_type,
            title=title or parsed.title,
            linkedin_urn=linkedin_urn or parsed.linkedin_urn,
            is_active=True,
        )
        self._session.add(profile)
        await self._session.flush()
        return "new"

    async def remove_profile(self, user_id: int, slug: str) -> bool:
        key = slug.lower().removeprefix("@").split("/")[-1]
        result = await self._session.execute(
            select(LinkedInProfile).where(
                LinkedInProfile.user_id == user_id,
                LinkedInProfile.profile_slug == key,
            )
        )
        profile = result.scalar_one_or_none()
        if not profile:
            return False
        profile.is_active = False
        await self._session.flush()
        return True

    async def count_active(self, user_id: int) -> int:
        return len(await self.list_active_for_user(user_id))

    async def update_profile_urn(self, profile_id: int, linkedin_urn: str) -> None:
        result = await self._session.execute(
            select(LinkedInProfile).where(LinkedInProfile.id == profile_id)
        )
        profile = result.scalar_one_or_none()
        if profile and linkedin_urn:
            profile.linkedin_urn = linkedin_urn
            await self._session.flush()

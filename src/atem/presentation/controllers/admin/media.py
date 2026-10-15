"""Image library and uploads for the inline editor."""

from dataclasses import asdict
from typing import Annotated, Any

from litestar import Controller, get, post
from litestar.datastructures import UploadFile
from litestar.di import NamedDependency
from litestar.enums import RequestEncodingType
from litestar.params import Body

from atem.application.services.media_service import MediaService
from atem.presentation.security.admin_auth import require_admin


class AdminMediaController(Controller):
    """List and upload images (uploads are verified and re-encoded by MediaService)."""

    path = "/admin/images"
    guards = [require_admin]  # noqa: RUF012 - Litestar controller attribute
    include_in_schema = False

    @get("/list")
    async def list_images(
        self, media_service: NamedDependency[MediaService]
    ) -> list[dict[str, Any]]:
        """Uploaded images and bundled theme images."""
        return [asdict(item) for item in media_service.list_images()]

    @post("/upload")
    async def upload_image(
        self,
        media_service: NamedDependency[MediaService],
        data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)],
    ) -> dict[str, Any]:
        """Upload an image: content is verified and re-encoded (no SVG, no metadata)."""
        return asdict(media_service.store_upload(await data.read()))

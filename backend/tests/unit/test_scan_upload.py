from io import BytesIO
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from starlette.datastructures import Headers, UploadFile

from api.routers.compras_comerciais import ocr
from domain.exceptions import ValidationError


@pytest.mark.asyncio
@pytest.mark.parametrize("mime", ["image/jpeg", "image/jpg", "image/pjpeg"])
async def test_camera_jpeg_aliases_reach_reader_with_standard_mime(mime):
    from types import SimpleNamespace

    service = SimpleNamespace(ler=AsyncMock(return_value="read"))
    tenant = uuid4()
    file = UploadFile(
        BytesIO(b"photo"), filename="camera.jpg", headers=Headers({"content-type": mime})
    )
    result = await ocr.__wrapped__(
        request=None, arquivo=file, fornecedor_id=None, tenant=tenant, service=service
    )
    assert result == "read"
    service.ler.assert_awaited_once_with(tenant, b"photo", "image/jpeg", None)


@pytest.mark.asyncio
async def test_oversized_file_identifies_upload_field():
    file = UploadFile(
        BytesIO(b"x" * (8 * 1024 * 1024 + 1)),
        filename="camera.jpg",
        headers=Headers({"content-type": "image/jpeg"}),
    )
    with pytest.raises(ValidationError) as error:
        await ocr.__wrapped__(
            request=None, arquivo=file, fornecedor_id=None, tenant=uuid4(), service=None
        )
    assert error.value.field == "arquivo"

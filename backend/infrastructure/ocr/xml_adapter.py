"""Importa dados de XML NF-e/NFC-e enviado pelo usuário, sem consultas externas."""

from xml.etree import ElementTree

from domain.compras.extraction import ItemOCR, ResultadoOCR, validate_receipt
from domain.exceptions import ValidationError

_NS = {"n": "http://www.portalfiscal.inf.br/nfe"}


def parse_nfe_xml(content: bytes) -> ResultadoOCR:
    # Não aceita DTD nem entidades, inclusive em documentos UTF-16/32.
    searchable = content.replace(b"\x00", b"").upper()
    if len(content) > 8 * 1024 * 1024 or b"<!DOCTYPE" in searchable or b"<!ENTITY" in searchable:
        raise ValidationError("XML fiscal inválido ou muito grande.")
    try:
        root = ElementTree.fromstring(content)
        if root.tag not in {f"{{{_NS['n']}}}NFe", f"{{{_NS['n']}}}nfeProc"}:
            raise ValueError("Tipo de documento inválido")
        info = (
            root.find("n:infNFe", _NS)
            if root.tag.endswith("}NFe")
            else root.find("n:NFe/n:infNFe", _NS)
        )
        if info is None or info.findtext("n:ide/n:mod", namespaces=_NS) not in {"55", "65"}:
            raise ValueError("NF-e/NFC-e ausente")
        items = []
        for detail in info.findall("n:det", _NS):
            product = detail.find("n:prod", _NS)
            if product is None:
                raise ValueError("Produto ausente")
            fields = [
                product.findtext("n:" + field, namespaces=_NS)
                for field in ("xProd", "qCom", "uCom", "vUnCom", "vProd")
            ]
            items.append(ItemOCR(*fields))
        result = ResultadoOCR(
            items,
            info.findtext("n:total/n:ICMSTot/n:vNF", namespaces=_NS),
            info.findtext("n:emit/n:xNome", namespaces=_NS),
            info.findtext("n:ide/n:dhEmi", namespaces=_NS),
            fonte="xml_nfe",
        )
        return validate_receipt(result)
    except (ElementTree.ParseError, ValueError, TypeError):
        raise ValidationError("Não conseguimos ler o XML NF-e/NFC-e. Confira o arquivo.") from None


class DocumentReceiptExtractor:
    def __init__(self, image):
        self.image = image

    async def processar_imagem(self, content: bytes, mime_type="image/jpeg") -> ResultadoOCR:
        if mime_type in {"application/xml", "text/xml"}:
            return parse_nfe_xml(content)
        return await self.image.processar_imagem(content, mime_type)

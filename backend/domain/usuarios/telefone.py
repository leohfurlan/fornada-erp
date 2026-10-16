"""Identidade telefônica internacional, independente do provedor de mensagem."""
import phonenumbers

from domain.exceptions import ValidationError


def normalizar_telefone(numero: str, regiao: str) -> str:
    """Valida região/número e preserva todos os dígitos no formato E.164."""
    if regiao.upper() not in phonenumbers.SUPPORTED_REGIONS:
        raise ValidationError("Selecione um país/região válido", field="regiao")
    try:
        telefone = phonenumbers.parse(numero, regiao.upper())
    except phonenumbers.NumberParseException as exc:
        raise ValidationError("Informe um número de WhatsApp válido com DDD", field="telefone") from exc
    if not phonenumbers.is_valid_number(telefone):
        raise ValidationError("Informe um número de WhatsApp válido com DDD", field="telefone")
    if regiao.upper() == "BR" and (telefone.country_code != 55 or len(str(telefone.national_number)) != 11):
        raise ValidationError("Informe o celular brasileiro com DDD e nove dígitos", field="telefone")
    return phonenumbers.format_number(telefone, phonenumbers.PhoneNumberFormat.E164)

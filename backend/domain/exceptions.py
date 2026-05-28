class FornadaError(Exception):
    """Base para todas as exceções de domínio."""

    def __init__(self, message: str, code: str = "domain_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(FornadaError):
    def __init__(self, entity: str, entity_id: str | None = None) -> None:
        msg = f"{entity} não encontrado"
        if entity_id:
            msg += f": {entity_id}"
        super().__init__(msg, code="not_found")


class ConflictError(FornadaError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="conflict")


class PermissionError(FornadaError):
    def __init__(self, message: str = "Sem permissão para esta ação") -> None:
        super().__init__(message, code="permission_denied")


class ValidationError(FornadaError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="validation_error")


class AuthError(FornadaError):
    def __init__(self, message: str = "Credenciais inválidas") -> None:
        super().__init__(message, code="auth_error")


class EstoqueInsuficienteError(FornadaError):
    def __init__(self, ingrediente: str, disponivel: float, necessario: float) -> None:
        msg = (
            f"Estoque insuficiente de {ingrediente}: "
            f"disponível {disponivel}, necessário {necessario}"
        )
        super().__init__(msg, code="estoque_insuficiente")

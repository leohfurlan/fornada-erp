"""Erros da porta remota, sem dados sensíveis de transporte."""


class IfoodAPIError(Exception):
    def __init__(self, status: int = 0, retry_after: int = 30) -> None:
        self.status = status
        self.retry_after = retry_after
        super().__init__(
            f"iFood indisponível (HTTP {status})" if status else "Falha de conexão iFood"
        )

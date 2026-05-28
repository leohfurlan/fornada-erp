# Atalhos de desenvolvimento do Fornada para Windows / PowerShell
# Uso: .\fornada.ps1 <comando>
# Equivalente ao Makefile (que requer 'make', ausente no Windows por padrão).

param(
    [Parameter(Position = 0)]
    [string]$Command = "help"
)

switch ($Command) {
    "up" {
        docker compose up -d
    }
    "build" {
        docker compose up -d --build
    }
    "down" {
        docker compose down
    }
    "restart" {
        docker compose restart
    }
    "logs" {
        docker compose logs -f
    }
    "migrate" {
        docker compose exec backend alembic upgrade head
    }
    "migrate-new" {
        $msg = Read-Host "Descricao da migration"
        docker compose exec backend alembic revision --autogenerate -m $msg
    }
    "test-backend" {
        docker compose exec backend pytest --tb=short -q
    }
    "test-backend-cov" {
        docker compose exec backend pytest --cov=. --cov-report=term-missing
    }
    "test-frontend" {
        docker compose exec frontend pnpm test --run
    }
    "typecheck-frontend" {
        docker compose exec frontend pnpm tsc --noEmit
    }
    "shell-backend" {
        docker compose exec backend bash
    }
    "shell-db" {
        docker compose exec db psql -U fornada -d fornada
    }
    "setup" {
        if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
        docker compose up -d --build
        Start-Sleep -Seconds 8
        docker compose exec backend alembic upgrade head
        Write-Host "Ambiente pronto! Backend: http://localhost:8000/docs | Frontend: http://localhost:3000" -ForegroundColor Green
    }
    default {
        Write-Host "Comandos disponiveis:" -ForegroundColor Cyan
        Write-Host "  .\fornada.ps1 build              # sobe tudo com rebuild"
        Write-Host "  .\fornada.ps1 up                 # sobe os servicos"
        Write-Host "  .\fornada.ps1 down               # derruba os servicos"
        Write-Host "  .\fornada.ps1 logs               # acompanha os logs"
        Write-Host "  .\fornada.ps1 migrate            # roda as migrations"
        Write-Host "  .\fornada.ps1 migrate-new        # gera nova migration"
        Write-Host "  .\fornada.ps1 test-backend       # testes do backend"
        Write-Host "  .\fornada.ps1 test-backend-cov   # testes com cobertura"
        Write-Host "  .\fornada.ps1 test-frontend      # testes do frontend"
        Write-Host "  .\fornada.ps1 typecheck-frontend # checagem de tipos TS"
        Write-Host "  .\fornada.ps1 shell-backend      # shell no container backend"
        Write-Host "  .\fornada.ps1 shell-db           # psql no banco"
        Write-Host "  .\fornada.ps1 setup              # setup completo (primeira vez)"
    }
}

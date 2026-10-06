"""Empacota fontes atuais (inclusive alteracoes locais), sem segredos ou caches."""

import hashlib
import subprocess
import tarfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
output = root / "dist" / "fornada-source.tar.gz"
output.parent.mkdir(exist_ok=True)
files = subprocess.check_output(
    ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=root
).decode("utf-8").split("\0")
examples = {".env.example", ".env.pilot.example", ".env.production.example"}
with tarfile.open(output, "w:gz") as archive:
    for name in sorted(set(files)):
        if not name:
            continue
        relative = Path(name)
        if any(part.startswith(".env") for part in relative.parts) and name not in examples:
            continue
        if any(part in {"dist", ".git", "node_modules", ".venv", ".next", ".pnpm-store"}
               for part in relative.parts):
            continue
        path = root / relative
        if path.is_file() and not path.is_symlink():
            archive.add(path, arcname=name, recursive=False)
digest = hashlib.sha256(output.read_bytes()).hexdigest()
output.with_suffix(output.suffix + ".sha256").write_text(
    f"{digest}  {output.name}\n", encoding="utf-8"
)
print(f"Created: {output.name}; SHA256: {digest}")

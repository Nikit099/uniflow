import hashlib
import secrets
from pathlib import Path


class FileSystemStorage:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes) -> tuple[str, str]:
        key = f"{secrets.token_hex(16)}.bin"
        destination = self.root / key
        destination.write_bytes(data)
        return key, hashlib.sha256(data).hexdigest()

    def read(self, key: str) -> bytes:
        if Path(key).name != key:
            raise FileNotFoundError
        return (self.root / key).read_bytes()

    def delete(self, key: str) -> None:
        path = self.root / Path(key).name
        if path.exists():
            path.unlink()

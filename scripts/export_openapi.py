from pathlib import Path

import yaml

from app.main import app


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    content = yaml.safe_dump(app.openapi(), allow_unicode=True, sort_keys=False)
    (root / "openapi.yaml").write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()

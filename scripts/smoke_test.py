import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app


def run() -> int:
    app = create_app()
    client = app.test_client()
    response = client.get("/health")
    if response.status_code == 200 and response.json and response.json.get("status") == "ok":
        print("Smoke test passed.")
        return 0
    print("Smoke test failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(run())

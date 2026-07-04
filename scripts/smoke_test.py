from app import create_app


def run() -> int:
    app = create_app()
    client = app.test_client()
    response = client.get("/health")
    if response.status_code == 200 and response.json == {"status": "ok"}:
        print("Smoke test passed.")
        return 0
    print("Smoke test failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(run())

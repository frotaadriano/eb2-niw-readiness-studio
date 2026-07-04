import json
from pathlib import Path

from app import BASE_DIR, build_export_payload


def export_demo_report() -> Path:
    profile = {
        "full_name": "Demo Candidate",
        "headline": "Applied AI Engineer",
        "target_domain": "Machine Learning Systems",
    }
    evidences = [
        {
            "category": "publications",
            "title": "Demo Technical Article",
            "impact_level": 3,
            "is_private": False,
        },
        {
            "category": "recommendation_support",
            "title": "Private Draft Letter",
            "impact_level": 2,
            "is_private": True,
        },
    ]

    payload = build_export_payload(profile, evidences)
    output_dir = BASE_DIR / "exports"
    output_dir.mkdir(exist_ok=True)
    out_file = output_dir / "demo_report.json"
    out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Exported demo report to: {out_file}")
    return out_file


if __name__ == "__main__":
    export_demo_report()

"""KIS API SSOT CSV loader."""

import csv
import os
from pathlib import Path
from typing import Any


class APISpecNotFoundError(Exception):
    """API spec not found error."""

    def __init__(self, api_name_or_tr_id: str):
        super().__init__(f"API spec not found: {api_name_or_tr_id}")
        self.api_name_or_tr_id = api_name_or_tr_id


class SpecLoader:
    """KIS API spec loader from CSV files."""

    def __init__(self, api_docs_dir: str | None = None):
        """Initialize spec loader."""
        if api_docs_dir is None:
            # Check environment variable first
            api_docs_dir = os.getenv("API_DOCS_DIR")
            if api_docs_dir is None:
                # Default to api_docs/ in project root
                # spec_loader.py is at: packages/brokers/kis_direct/spec_loader.py
                # Go up 4 levels to reach project root
                project_root = Path(__file__).resolve().parents[3]
                api_docs_dir = str(project_root / "api_docs")
        self.api_docs_dir = Path(api_docs_dir)
        if not self.api_docs_dir.exists():
            raise FileNotFoundError(f"API docs directory not found: {api_docs_dir}")
        self._specs: dict[str, dict] = {}
        self._indexed = False

    def _load_all_specs(self) -> None:
        """Load all API specs from CSV files."""
        if self._indexed:
            return

        csv_files = list(self.api_docs_dir.glob("*.csv"))
        if not csv_files:
            raise FileNotFoundError(f"No CSV files found in {self.api_docs_dir}")

        for csv_file in csv_files:
            try:
                spec = self._parse_csv(csv_file)
                if spec:
                    # Index by API ID, TR_ID (실전), TR_ID (모의)
                    api_id = spec.get("api_id")
                    tr_id_real = spec.get("tr_id_real")
                    tr_id_paper = spec.get("tr_id_paper")
                    api_name = spec.get("api_name")

                    if api_id:
                        self._specs[api_id] = spec
                    if tr_id_real:
                        self._specs[tr_id_real] = spec
                    if tr_id_paper:
                        self._specs[tr_id_paper] = spec
                    if api_name:
                        self._specs[api_name] = spec
            except Exception as e:
                # Log but continue
                print(f"Warning: Failed to parse {csv_file}: {e}")

        self._indexed = True

    def _parse_csv(self, csv_file: Path) -> dict[str, Any] | None:
        """Parse a single CSV file into API spec."""
        spec = {
            "api_name": None,
            "api_id": None,
            "tr_id_real": None,
            "tr_id_paper": None,
            "http_method": None,
            "url": None,
            "domain_real": None,
            "domain_paper": None,
            "request_headers": [],
            "request_query_params": [],
            "request_body": [],
            "response_headers": [],
            "response_body": [],
        }

        with open(csv_file, encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        if not rows:
            return None

        # Parse header section
        i = 0
        while i < len(rows) and rows[i][0] != "Layout":
            row = rows[i]
            if len(row) > 1:
                key = row[0].strip()
                value = row[1].strip() if len(row) > 1 else ""

                if key == "API 명":
                    spec["api_name"] = value
                elif key == "API ID":
                    spec["api_id"] = value
                elif key == "실전 TR_ID":
                    spec["tr_id_real"] = value
                elif key == "모의 TR_ID":
                    spec["tr_id_paper"] = value
                elif key == "HTTP Method":
                    spec["http_method"] = value.upper()
                elif key == "URL 명":
                    spec["url"] = value
                elif key == "실전 Domain":
                    spec["domain_real"] = value
                elif key == "모의 Domain":
                    spec["domain_paper"] = value
            i += 1

        # Find Layout section
        layout_start = None
        for j, row in enumerate(rows):
            if row[0] == "Layout":
                layout_start = j + 1
                break

        if layout_start is None:
            return spec

        # Parse Layout section
        # Format: 구분,Element,한글명,Type,Required,Length,Description
        for j in range(layout_start, len(rows)):
            row = rows[j]
            if len(row) < 2:
                continue

            section = row[0].strip()
            element = row[1].strip() if len(row) > 1 else ""
            korean_name = row[2].strip() if len(row) > 2 else ""
            field_type = row[3].strip() if len(row) > 3 else ""
            required = row[4].strip() if len(row) > 4 else ""
            length = row[5].strip() if len(row) > 5 else ""
            description = row[6].strip() if len(row) > 6 else ""

            field_spec = {
                "element": element,
                "korean_name": korean_name,
                "type": field_type,
                "required": required.upper() == "Y",
                "length": length,
                "description": description,
            }

            if section == "Request Header":
                spec["request_headers"].append(field_spec)
            elif section == "Request Query Parameter":
                spec["request_query_params"].append(field_spec)
            elif section == "Request Body":
                spec["request_body"].append(field_spec)
            elif section == "Response Header":
                spec["response_headers"].append(field_spec)
            elif section == "Response Body":
                spec["response_body"].append(field_spec)

        return spec

    def list_available_apis(self) -> list[str]:
        """List all available API names/IDs."""
        self._load_all_specs()
        return list(set(self._specs.keys()))

    def get_api(self, name_or_tr_id: str) -> dict[str, Any]:
        """Get API spec by name or TR_ID."""
        self._load_all_specs()
        if name_or_tr_id not in self._specs:
            raise APISpecNotFoundError(name_or_tr_id)
        return self._specs[name_or_tr_id].copy()

    def validate_request(
        self, api_spec: dict[str, Any], payload: dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """Validate request payload against API spec."""
        errors = []

        # Check required headers
        for header_spec in api_spec.get("request_headers", []):
            if header_spec.get("required") and header_spec.get("element") not in payload.get(
                "headers", {}
            ):
                errors.append(f"Missing required header: {header_spec['element']}")

        # Check required query params
        for param_spec in api_spec.get("request_query_params", []):
            if param_spec.get("required") and param_spec.get("element") not in payload.get(
                "query_params", {}
            ):
                errors.append(f"Missing required query param: {param_spec['element']}")

        # Check required body fields
        for body_spec in api_spec.get("request_body", []):
            if body_spec.get("required") and body_spec.get("element") not in payload.get(
                "body", {}
            ):
                errors.append(f"Missing required body field: {body_spec['element']}")

        return len(errors) == 0, errors

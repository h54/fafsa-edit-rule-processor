from typing import Any

from fastapi.testclient import TestClient

from tests.helpers import set_path

URL = "/v1/applications/validate"


def test_valid_application(
    client: TestClient, valid_application_data: dict[str, Any]
) -> None:
    response = client.post(URL, json=valid_application_data)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "VALID"
    assert body["rulesetVersion"] == "2026-27.1"
    assert body["summary"] == {
        "total": 7,
        "passed": 6,
        "failed": 0,
        "skipped": 1,  # single, so the spouse rule doesn't apply
        "errored": 0,
    }


def test_invalid_application_reports_every_violation(
    client: TestClient, invalid_application_data: dict[str, Any]
) -> None:
    response = client.post(URL, json=invalid_application_data)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "INVALID"
    assert body["summary"]["failed"] == 7
    ssn = next(r for r in body["results"] if r["ruleId"] == "SSN_FORMAT")
    assert ssn == {
        "ruleId": "SSN_FORMAT",
        "outcome": "FAILED",
        "severity": "ERROR",
        "message": "SSN must be exactly 9 digits, with no dashes or spaces.",
        "fields": ["studentInfo.ssn"],
    }


def test_malformed_application_is_rejected_with_422(
    client: TestClient, valid_application_data: dict[str, Any]
) -> None:
    data = set_path(valid_application_data, "studentInfo.dateOfBirth", ...)

    response = client.post(URL, json=data)

    assert response.status_code == 422
    (error,) = response.json()["detail"]
    assert error["loc"] == ["body", "studentInfo", "dateOfBirth"]
    assert "input" not in error
    assert valid_application_data["studentInfo"]["firstName"] not in response.text

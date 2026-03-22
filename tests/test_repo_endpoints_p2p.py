from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EndpointExpectation:
    path: str
    method: str
    public: bool
    expected_status_range: tuple[int, int]


def validate_endpoint_catalog(endpoints: list[EndpointExpectation]) -> list[str]:
    issues: list[str] = []

    for endpoint in endpoints:
        if not endpoint.path.startswith("/"):
            issues.append(f"{endpoint.path} must start with '/'")

        if endpoint.method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            issues.append(f"{endpoint.path} uses unsupported method {endpoint.method}")

        start, end = endpoint.expected_status_range
        if start < 100 or end > 599 or start > end:
            issues.append(f"{endpoint.path} has invalid status range {start}-{end}")

        if endpoint.public and endpoint.path.startswith("/admin"):
            issues.append(f"{endpoint.path} should not be marked public")

    return issues


def infer_contract_risk(endpoints: list[EndpointExpectation]) -> str:
    public_count = sum(1 for endpoint in endpoints if endpoint.public)
    write_count = sum(1 for endpoint in endpoints if endpoint.method in {"POST", "PUT", "PATCH", "DELETE"})

    if public_count >= 8 and write_count >= 4:
        return "high"
    if public_count >= 4 or write_count >= 1:
        return "medium"
    return "low"


def test_p2p_001_enterprise_endpoint_catalog_validates_with_no_issues() -> None:
    endpoints = [
        EndpointExpectation(path="/health/live/", method="GET", public=True, expected_status_range=(200, 299)),
        EndpointExpectation(path="/health/ready/", method="GET", public=True, expected_status_range=(200, 503)),
        EndpointExpectation(
            path="/enterprise/change-risk/evaluate/",
            method="POST",
            public=True,
            expected_status_range=(200, 400),
        ),
        EndpointExpectation(path="/learning-path/planner/", method="POST", public=False, expected_status_range=(200, 400)),
        EndpointExpectation(path="/current-user/", method="GET", public=False, expected_status_range=(200, 401)),
    ]

    issues = validate_endpoint_catalog(endpoints)

    assert issues == []


def test_p2p_002_catalog_rejects_non_slash_prefixed_paths() -> None:
    endpoints = [
        EndpointExpectation(path="health/live/", method="GET", public=True, expected_status_range=(200, 299)),
    ]

    issues = validate_endpoint_catalog(endpoints)

    assert any("must start with '/'" in issue for issue in issues)


def test_p2p_003_catalog_rejects_invalid_http_methods() -> None:
    endpoints = [
        EndpointExpectation(path="/health/live/", method="TRACE", public=True, expected_status_range=(200, 299)),
    ]

    issues = validate_endpoint_catalog(endpoints)

    assert any("unsupported method" in issue for issue in issues)


def test_p2p_004_catalog_rejects_invalid_status_ranges() -> None:
    endpoints = [
        EndpointExpectation(path="/health/ready/", method="GET", public=True, expected_status_range=(700, 799)),
    ]

    issues = validate_endpoint_catalog(endpoints)

    assert any("invalid status range" in issue for issue in issues)


def test_p2p_005_catalog_rejects_public_admin_endpoint() -> None:
    endpoints = [
        EndpointExpectation(path="/admin/", method="GET", public=True, expected_status_range=(200, 401)),
    ]

    issues = validate_endpoint_catalog(endpoints)

    assert any("should not be marked public" in issue for issue in issues)


def test_p2p_006_risk_inference_low_for_minimal_public_surface() -> None:
    endpoints = [
        EndpointExpectation(path="/health/live/", method="GET", public=True, expected_status_range=(200, 299)),
        EndpointExpectation(path="/health/ready/", method="GET", public=True, expected_status_range=(200, 503)),
    ]

    risk = infer_contract_risk(endpoints)

    assert risk == "low"


def test_p2p_007_risk_inference_medium_for_mixed_read_write_surface() -> None:
    endpoints = [
        EndpointExpectation(path="/health/live/", method="GET", public=True, expected_status_range=(200, 299)),
        EndpointExpectation(path="/health/ready/", method="GET", public=True, expected_status_range=(200, 503)),
        EndpointExpectation(path="/current-user/", method="GET", public=False, expected_status_range=(200, 401)),
        EndpointExpectation(path="/learning-path/planner/", method="POST", public=False, expected_status_range=(200, 400)),
    ]

    risk = infer_contract_risk(endpoints)

    assert risk == "medium"


def test_p2p_008_risk_inference_high_for_large_public_write_surface() -> None:
    endpoints = [
        EndpointExpectation(path=f"/api/public/{index}/", method="GET", public=True, expected_status_range=(200, 299))
        for index in range(8)
    ] + [
        EndpointExpectation(path="/api/public/create/", method="POST", public=True, expected_status_range=(200, 201)),
        EndpointExpectation(path="/api/public/update/", method="PUT", public=True, expected_status_range=(200, 200)),
        EndpointExpectation(path="/api/public/patch/", method="PATCH", public=True, expected_status_range=(200, 200)),
        EndpointExpectation(path="/api/public/delete/", method="DELETE", public=True, expected_status_range=(200, 204)),
    ]

    risk = infer_contract_risk(endpoints)

    assert risk == "high"

from __future__ import annotations

from typing import Any


SECURITY_HEADERS = {
    "content-security-policy": "CSP",
    "strict-transport-security": "HSTS",
    "x-content-type-options": "X-Content-Type-Options",
    "x-frame-options": "X-Frame-Options",
    "referrer-policy": "Referrer-Policy",
    "permissions-policy": "Permissions-Policy",
}


def audit_headers(headers: dict[str, str]) -> dict[str, Any]:
    normalized = {k.lower(): v for k, v in headers.items()}
    present = {}
    missing = []
    for key, display in SECURITY_HEADERS.items():
        if key in normalized:
            present[display] = normalized[key]
        else:
            missing.append(display)

    cors = normalized.get("access-control-allow-origin")
    findings: list[dict[str, str]] = []
    if cors == "*":
        findings.append(
            {
                "severity": "info",
                "title": "Wildcard CORS observed",
                "detail": "Access-Control-Allow-Origin is '*'. Review whether this is intended for the resource.",
            }
        )
    if "content-security-policy" not in normalized:
        findings.append(
            {
                "severity": "info",
                "title": "CSP header not observed",
                "detail": "No Content-Security-Policy header was present in the captured response.",
            }
        )

    return {
        "present_security_headers": present,
        "missing_security_headers": missing,
        "cors_allow_origin": cors,
        "findings": findings,
    }


def audit_cookies(cookies: list[dict]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for cookie in cookies:
        issues = []
        if not cookie.get("secure"):
            issues.append("Secure flag not observed")
        if not cookie.get("httpOnly"):
            issues.append("HttpOnly flag not observed")
        same_site = cookie.get("sameSite")
        if not same_site:
            issues.append("SameSite attribute not observed")
        if issues:
            findings.append(
                {
                    "name": cookie.get("name"),
                    "domain": cookie.get("domain"),
                    "issues": issues,
                }
            )
    return findings

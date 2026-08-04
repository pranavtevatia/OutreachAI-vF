"""
Hunter.io integration for email finding, verification, and alternate prospect discovery.
"""

import requests
import streamlit as st


def get_hunter_key():
    return st.secrets.get("HUNTER_API_KEY", "")


def verify_email(email):
    """Verify if an email address is valid and deliverable."""
    key = get_hunter_key()
    if not key:
        return {"status": "skipped", "message": "Hunter API key not configured"}
    try:
        resp = requests.get(
            "https://api.hunter.io/v2/email-verifier",
            params={"email": email, "api_key": key},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            status = data.get("status", "unknown")  # valid, invalid, accept_all, webmail, disposable, unknown
            score = data.get("score", 0)
            return {
                "status": status,
                "score": score,
                "email": email,
                "result": data.get("result", "unknown"),  # deliverable, undeliverable, risky
                "message": f"Email is {status} (score: {score})",
            }
        else:
            return {"status": "error", "message": f"Hunter API error: {resp.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def find_email(first_name, last_name, domain):
    """Find an email address given a name and company domain."""
    key = get_hunter_key()
    if not key:
        return None
    try:
        resp = requests.get(
            "https://api.hunter.io/v2/email-finder",
            params={
                "domain": domain,
                "first_name": first_name,
                "last_name": last_name,
                "api_key": key,
            },
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            email = data.get("email")
            if email:
                return {
                    "email": email,
                    "confidence": data.get("confidence", 0),
                    "first_name": data.get("first_name", first_name),
                    "last_name": data.get("last_name", last_name),
                    "position": data.get("position", ""),
                    "linkedin_url": data.get("linkedin", ""),
                }
        return None
    except Exception:
        return None


def domain_search(domain, limit=5):
    """Search for people at a company domain. Returns list of contacts."""
    key = get_hunter_key()
    if not key:
        return []
    try:
        resp = requests.get(
            "https://api.hunter.io/v2/domain-search",
            params={
                "domain": domain,
                "limit": limit,
                "api_key": key,
            },
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            emails = data.get("emails", [])
            contacts = []
            for e in emails:
                contacts.append({
                    "email": e.get("value", ""),
                    "first_name": e.get("first_name", ""),
                    "last_name": e.get("last_name", ""),
                    "position": e.get("position", ""),
                    "department": e.get("department", ""),
                    "seniority": e.get("seniority", ""),
                    "linkedin": e.get("linkedin", ""),
                    "confidence": e.get("confidence", 0),
                })
            return contacts
        return []
    except Exception:
        return []

"""Data cleaning and cautious, single-page extraction utilities for AI DataScout."""
from __future__ import annotations

import json
import time
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser

import re
from datetime import date
import pandas as pd
import requests
from bs4 import BeautifulSoup

REQUIRED_COLUMNS = ["clinic_name", "suburb", "state", "postcode", "phone", "website", "services", "source_url", "last_verified"]
USER_AGENT = "AIDataScoutDemo/1.0 (educational project; contact: project-owner@example.com)"
ALLOWED_SCHEMES = {"http", "https"}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column labels and map common aliases to the project schema."""
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    aliases = {
        "name": "clinic_name", "practice_name": "clinic_name", "provider_name": "clinic_name",
        "city": "suburb", "locality": "suburb", "state_territory": "state",
        "postal_code": "postcode", "zip": "postcode", "telephone": "phone",
        "url": "website", "web": "website", "source": "source_url",
        "verified_date": "last_verified", "services_offered": "services",
    }
    df = df.rename(columns={c: aliases[c] for c in df.columns if c in aliases})
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[REQUIRED_COLUMNS]


def clean_clinics(df: pd.DataFrame) -> pd.DataFrame:
    """Clean a clinic dataframe without inventing missing values."""
    df = normalize_columns(df)
    for col in REQUIRED_COLUMNS:
        df[col] = df[col].fillna("").astype(str).str.strip()
    df["clinic_name"] = df["clinic_name"].str.replace(r"\s+", " ", regex=True)
    df["suburb"] = df["suburb"].str.replace(r"\s+", " ", regex=True)
    df["state"] = df["state"].str.upper()
    df["postcode"] = df["postcode"].str.replace(r"\.0$", "", regex=True)
    # Keep phone as text to preserve leading zeroes and country codes.
    df["phone"] = df["phone"].str.replace(r"\s+", " ", regex=True)
    df["website"] = df["website"].str.rstrip("/")
    df["source_url"] = df["source_url"].str.strip()
    # Deduplicate on name + suburb + state, keeping the first source row.
    key = df["clinic_name"].str.casefold() + "|" + df["suburb"].str.casefold() + "|" + df["state"].str.casefold()
    df = df.loc[key.ne("||")].copy()
    df["_dedupe_key"] = key.loc[df.index]
    df = df.drop_duplicates("_dedupe_key", keep="first").drop(columns="_dedupe_key")
    return df.reset_index(drop=True)


def robots_allows(url: str, user_agent: str = USER_AGENT, timeout: int = 8) -> bool:
    """Return whether robots.txt permits this user agent to fetch this URL.

    Fail closed: if robots.txt cannot be fetched or parsed, return False.
    This check is not a substitute for reviewing the site's terms and permissions.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES or not parsed.netloc:
        return False
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        response = requests.get(robots_url, headers={"User-Agent": user_agent}, timeout=timeout)
        if response.status_code >= 400:
            return False
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(response.text.splitlines())
        return parser.can_fetch(user_agent, url)
    except requests.RequestException:
        return False


def extract_clinic_jsonld(url: str, confirmed_permission: bool = False, min_delay_seconds: float = 2.0) -> list[dict]:
    """Fetch ONE explicitly authorized page and extract relevant JSON-LD entities.

    Does not crawl links. Requires explicit caller confirmation of permission and
    robots.txt approval. For real deployments, replace the demo contact email in
    USER_AGENT with a monitored project contact.
    """
    if not confirmed_permission:
        raise PermissionError("Confirm that the source terms permit this use before fetching.")
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES or not parsed.netloc:
        raise ValueError("Provide a valid http/https URL.")
    if not robots_allows(url):
        raise PermissionError("robots.txt does not allow this fetch, or could not be checked.")
    time.sleep(max(0.0, min(float(min_delay_seconds), 30.0)))
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=12)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    records = []


def extract_clinic_listing_html(
    url,
    confirmed_permission=False,
    min_delay_seconds=2.0,
):
    """Extract candidate clinic links from one permitted listing page."""

    if not confirmed_permission:
        raise PermissionError(
            "Confirm permission to collect this website's data first."
        )

    if not robots_allows(url):
        raise PermissionError(
            "robots.txt blocks this URL or could not be checked."
        )

    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    response.raise_for_status()

    time.sleep(max(0.0, min(float(min_delay_seconds), 30.0)))

    soup = BeautifulSoup(response.text, "html.parser")
    page_host = urlparse(url).netloc.lower()

    # Prefer the main page content over navigation menus.
    containers = soup.select("main, article, .entry-content")
    search_roots = containers or [soup]

    records = []
    seen_urls = set()

    for root in search_roots:
        for link in root.find_all("a", href=True):
            name = link.get_text(" ", strip=True)
            target = urljoin(url, link["href"])
            parsed = urlparse(target)

            if not name or parsed.netloc.lower() != page_host:
                continue

            # Skip non-page links.
            if parsed.scheme not in ("http", "https"):
                continue
            if parsed.path in ("", "/"):
                continue
            if parsed.path.lower().endswith(
                (".pdf", ".jpg", ".jpeg", ".png", ".zip")
            ):
                continue

            # Conservative candidate filter; review results manually.
            if not re.search(
                r"clinic|medical|doctor|practice|health|gp",
                name,
                re.IGNORECASE,
            ):
                continue

            canonical_url = (
                f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}/"
            )

            if canonical_url in seen_urls:
                continue

            seen_urls.add(canonical_url)

            records.append({
                "clinic_name": name,
                "suburb": "",
                "state": "",
                "postcode": "",
                "phone": "",
                "website": canonical_url,
                "services": "",
                "source_url": url,
                "last_verified": date.today().isoformat(),
            })

        if records:
            break

    return records


import time
import requests
from datetime import datetime, timezone


WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_CATEGORY_URL = (
    "https://en.wikipedia.org/wiki/"
    "Category:Australian_general_practitioners"
)


def scrape_wikipedia_category(max_pages=30):
    """
    Collect live Wikipedia category members and summaries.

    max_pages limits the number of article records requested.
    Uses the public MediaWiki API, with pagination and a delay.
    """
    if not 1 <= max_pages <= 100:
        raise ValueError("max_pages must be between 1 and 100.")

    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "AIDataScout/1.0 "
            "(educational data intelligence project)"
        )
    })

    records = []
    continuation = {}
    collected_at = datetime.now(timezone.utc).isoformat()

    while len(records) < max_pages:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": "Category:Australian general practitioners",
            "cmtype": "page",
            "cmlimit": min(50, max_pages - len(records)),
            "format": "json",
            **continuation,
        }

        response = session.get(
            WIKIPEDIA_API,
            params=params,
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()

        members = payload.get("query", {}).get(
            "categorymembers", []
        )

        if not members:
            break

        page_ids = [
            str(item["pageid"])
            for item in members
            if "pageid" in item
        ]

        # Fetch article extracts in one API request per batch.
        details = {}
        if page_ids:
            detail_response = session.get(
                WIKIPEDIA_API,
                params={
                    "action": "query",
                    "pageids": "|".join(page_ids),
                    "prop": "extracts",
                    "exintro": 1,
                    "explaintext": 1,
                    "exchars": 700,
                    "format": "json",
                },
                timeout=20,
            )
            detail_response.raise_for_status()
            details = detail_response.json().get(
                "query", {}
            ).get("pages", {})

        for item in members:
            title = item["title"]
            page_id = item.get("pageid")
            detail = details.get(str(page_id), {})

            records.append({
                "title": title,
                "page_id": page_id,
                "article_url": (
                    "https://en.wikipedia.org/wiki/"
                    + title.replace(" ", "_")
                ),
                "summary": detail.get("extract", ""),
                "source_category": WIKIPEDIA_CATEGORY_URL,
                "collected_at_utc": collected_at,
            })

        continuation = payload.get("continue", {})
        if not continuation:
            break

        # Be polite to the service.
        time.sleep(1)

    return records


    def walk(obj):
        if isinstance(obj, list):
            for item in obj:
                walk(item)
        elif isinstance(obj, dict):
            typ = obj.get("@type", [])
            types = {typ} if isinstance(typ, str) else set(typ or [])
            if types.intersection({"MedicalClinic", "Physician", "MedicalOrganization", "LocalBusiness"}):
                address = obj.get("address", {})
                if isinstance(address, str):
                    address_text = address
                    suburb = state = postcode = ""
                elif isinstance(address, dict):
                    address_text = ", ".join(str(address.get(k, "")).strip() for k in ["streetAddress", "addressLocality", "addressRegion", "postalCode"] if address.get(k))
                    suburb = str(address.get("addressLocality", ""))
                    state = str(address.get("addressRegion", ""))
                    postcode = str(address.get("postalCode", ""))
                else:
                    address_text = suburb = state = postcode = ""
                website = obj.get("url", url)
                if isinstance(website, dict):
                    website = website.get("@id", url)
                records.append({
                    "clinic_name": obj.get("name", ""),
                    "suburb": suburb,
                    "state": state,
                    "postcode": postcode,
                    "phone": obj.get("telephone", ""),
                    "website": urljoin(url, str(website)) if website else url,
                    "services": "; ".join(
                        [str(x.get("name", "")) if isinstance(x, dict) else str(x)
                         for x in (obj.get("medicalSpecialty", []) if isinstance(obj.get("medicalSpecialty", []), list)
                                   else [obj.get("medicalSpecialty")]) if x]
                    ),
                    "source_url": url,
                    "last_verified": pd.Timestamp.now(tz="UTC").date().isoformat(),
                })
            for value in obj.values():
                if isinstance(value, (dict, list)):
                    walk(value)

    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            walk(json.loads(tag.string or tag.get_text()))
        except (json.JSONDecodeError, TypeError):
            continue
    return clean_clinics(pd.DataFrame(records)) .to_dict(orient="records") if records else []


def quality_report(df: pd.DataFrame) -> dict:
    """Return simple completeness and duplicate metrics for a cleaned dataset."""
    clean = normalize_columns(df)
    total = len(clean)
    tracked = ["clinic_name", "suburb", "state", "postcode", "phone", "website", "source_url"]
    missing = {c: int(clean[c].fillna("").astype(str).str.strip().eq("").sum()) for c in tracked}
    completeness = 100.0 if total == 0 else round(
        100 * sum(total - v for v in missing.values()) / (total * len(tracked)), 1
    )
    return {"rows": total, "missing_by_column": missing, "completeness_pct": completeness}

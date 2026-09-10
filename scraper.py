import json
import re
import time
from datetime import datetime, date
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser


BASE_URL = "https://sarkariresult.com.cm"
LATEST_URL = f"{BASE_URL}/latest-jobs/"

OUTPUT_FILE = "jobs.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    )
}


session = requests.Session()
session.headers.update(HEADERS)


# ---------------------------------------------------------
# FETCH PAGE
# ---------------------------------------------------------

def fetch_page(url):
    try:
        response = session.get(url, timeout=20)

        if response.status_code != 200:
            print(
                f"[ERROR] HTTP {response.status_code}: {url}"
            )
            return None

        return response.text

    except requests.RequestException as e:
        print(f"[ERROR] Could not fetch {url}")
        print(e)
        return None


# ---------------------------------------------------------
# DATE PARSER
# ---------------------------------------------------------

def parse_date(text):
    if not text:
        return None

    text = text.strip()

    patterns = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b\d{1,2}[/-][A-Za-z]{3,9}[/-]\d{2,4}\b",
        r"\b[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}\b",
        r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b",
    ]

    for pattern in patterns:

        match = re.search(pattern, text)

        if not match:
            continue

        value = match.group(0)

        try:
            parsed = date_parser.parse(
                value,
                dayfirst=True
            )

            return parsed.date().isoformat()

        except (ValueError, OverflowError):
            continue

    return None


# ---------------------------------------------------------
# FIND DATE AFTER LABEL
# ---------------------------------------------------------

def find_date_after_label(text, labels):
    text_lower = text.lower()

    for label in labels:

        position = text_lower.find(label.lower())

        if position == -1:
            continue

        section = text[
            position:
            position + 250
        ]

        parsed = parse_date(section)

        if parsed:
            return parsed

    return None


# ---------------------------------------------------------
# EXTRACT NUMBER OF POSTS
# ---------------------------------------------------------

def extract_posts(text):

    patterns = [
        r"total\s+post[s]?\s*[:\-]?\s*([\d,]+)",
        r"total\s+vacanc(?:y|ies)\s*[:\-]?\s*([\d,]+)",
        r"no\.?\s+of\s+post[s]?\s*[:\-]?\s*([\d,]+)",
        r"number\s+of\s+post[s]?\s*[:\-]?\s*([\d,]+)",
        r"vacanc(?:y|ies)\s*[:\-]?\s*([\d,]+)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            try:
                return int(
                    match.group(1).replace(",", "")
                )

            except ValueError:
                pass

    return None


# ---------------------------------------------------------
# EXTRACT JOB DETAILS
# ---------------------------------------------------------

def extract_job_page(url, html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    title = ""

    if soup.title:
        title = soup.title.get_text(
            " ",
            strip=True
        )

    # Prefer H1
    h1 = soup.find("h1")

    if h1:
        title = h1.get_text(
            " ",
            strip=True
        )

    text = soup.get_text(
        " ",
        strip=True
    )

    # -----------------------------------------------------
    # DATES
    # -----------------------------------------------------

    start_date = find_date_after_label(
        text,
        [
            "application start date",
            "apply start date",
            "online application start",
            "start date",
            "application begin",
            "registration start",
        ]
    )

    last_date = find_date_after_label(
        text,
        [
            "last date",
            "last date to apply",
            "application last date",
            "apply last date",
            "closing date",
            "registration last date",
        ]
    )

    notification_date = find_date_after_label(
        text,
        [
            "notification date",
            "advertisement date",
            "published date",
            "notice date",
        ]
    )

    posts = extract_posts(text)

    return {
        "title": title,
        "url": url,
        "notification_date": notification_date,
        "application_start": start_date,
        "application_end": last_date,
        "posts": posts,
    }


# ---------------------------------------------------------
# GET JOB LINKS FROM LATEST JOBS
# ---------------------------------------------------------

def get_job_links(html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    links = []

    for a in soup.find_all("a", href=True):

        href = a["href"].strip()

        title = a.get_text(
            " ",
            strip=True
        )

        if not title:
            continue

        absolute_url = urljoin(
            BASE_URL,
            href
        )

        if not absolute_url.startswith(BASE_URL):
            continue

        # Skip obvious navigation links
        ignored = [
            "/contact",
            "/about",
            "/privacy",
            "/disclaimer",
            "/sitemap",
        ]

        if any(
            x in absolute_url.lower()
            for x in ignored
        ):
            continue

        links.append({
            "title": title,
            "url": absolute_url
        })

    # Remove duplicates
    unique = {}

    for job in links:
        unique[job["url"]] = job

    return list(unique.values())


# ---------------------------------------------------------
# CLASSIFY JOB
# ---------------------------------------------------------

def classify_job(job):

    today = date.today()

    start = None
    end = None

    if job.get("application_start"):

        try:
            start = date.fromisoformat(
                job["application_start"]
            )

        except ValueError:
            pass

    if job.get("application_end"):

        try:
            end = date.fromisoformat(
                job["application_end"]
            )

        except ValueError:
            pass

    # -----------------------------------------------------
    # UPCOMING
    # -----------------------------------------------------

    if start and start > today:

        return "upcoming"

    # -----------------------------------------------------
    # CRITICAL
    # -----------------------------------------------------

    if end:

        days_left = (
            end - today
        ).days

        if 0 <= days_left <= 5:

            return "critical"

        # -------------------------------------------------
        # OLD
        # -------------------------------------------------

        if days_left < 0:

            return "old"

    # -----------------------------------------------------
    # OPEN
    # -----------------------------------------------------

    if start:

        if start <= today:

            if end is None or end >= today:

                return "open"

    # -----------------------------------------------------
    # UNKNOWN
    # -----------------------------------------------------

    return "unknown"


# ---------------------------------------------------------
# ADD DAYS LEFT
# ---------------------------------------------------------

def add_status_data(job):

    today = date.today()

    job["status"] = classify_job(job)

    job["days_left"] = None

    if job.get("application_end"):

        try:

            end = date.fromisoformat(
                job["application_end"]
            )

            job["days_left"] = (
                end - today
            ).days

        except ValueError:
            pass

    return job


# ---------------------------------------------------------
# SCRAPE
# ---------------------------------------------------------

def scrape():

    print("=" * 70)
    print("GOVERNMENT JOB TRACKER")
    print("=" * 70)

    print("\nFetching latest jobs...")

    html = fetch_page(
        LATEST_URL
    )

    if not html:

        print(
            "Could not fetch latest jobs page."
        )

        return

    links = get_job_links(
        html
    )

    print(
        f"Found {len(links)} links."
    )

    jobs = []

    seen_urls = set()

    for index, item in enumerate(
        links,
        start=1
    ):

        url = item["url"]

        if url in seen_urls:
            continue

        seen_urls.add(url)

        print(
            f"\n[{index}] {item['title']}"
        )

        page = fetch_page(
            url
        )

        if not page:

            continue

        try:

            job = extract_job_page(
                url,
                page
            )

            # If article parser didn't get title,
            # use listing title.
            if not job["title"]:

                job["title"] = item["title"]

            # If title is garbage, use listing title
            if len(job["title"]) > 300:

                job["title"] = item["title"]

            job = add_status_data(
                job
            )

            jobs.append(
                job
            )

            print(
                f"    Start: {job['application_start']}"
            )

            print(
                f"    End:   {job['application_end']}"
            )

            print(
                f"    Posts: {job['posts']}"
            )

            print(
                f"    Status: {job['status']}"
            )

        except Exception as e:

            print(
                f"    [ERROR] {e}"
            )

        # Don't hammer the website
        time.sleep(0.5)

    # -----------------------------------------------------
    # SORT
    # -----------------------------------------------------

    def sort_key(job):

        date_value = (
            job.get("notification_date")
            or job.get("application_start")
            or "1900-01-01"
        )

        return date_value

    jobs.sort(
        key=sort_key,
        reverse=True
    )

    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    output = {
        "last_updated": datetime.now().isoformat(),
        "source": LATEST_URL,
        "jobs": jobs
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False
        )

    print("\n" + "=" * 70)

    print(
        f"Saved {len(jobs)} jobs to {OUTPUT_FILE}"
    )

    print("=" * 70)


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

if __name__ == "__main__":

    scrape()

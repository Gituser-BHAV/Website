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

        response = session.get(
            url,
            timeout=20
        )

        if response.status_code != 200:

            print(
                f"[ERROR] HTTP {response.status_code}: {url}"
            )

            return None

        return response.text

    except requests.RequestException as e:

        print(
            f"[ERROR] Could not fetch {url}"
        )

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

        match = re.search(
            pattern,
            text
        )

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

        position = text_lower.find(
            label.lower()
        )

        if position == -1:

            continue

        section = text[
            position:
            position + 250
        ]

        parsed = parse_date(
            section
        )

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

    # Prefer H1
    h1 = soup.find("h1")

    if h1:

        title = h1.get_text(
            " ",
            strip=True
        )

    # Fall back to page title
    if not title and soup.title:

        title = soup.title.get_text(
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
            "online form start",
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
            "last date for apply",
        ]
    )

    notification_date = find_date_after_label(
        text,
        [
            "notification date",
            "advertisement date",
            "published date",
            "notice date",
            "publication date",
        ]
    )

    posts = extract_posts(
        text
    )

    return {
        "title": title,
        "url": url,
        "notification_date": notification_date,
        "application_start": start_date,
        "application_end": last_date,
        "posts": posts,
    }


# ---------------------------------------------------------
# DETERMINE WHETHER LINK IS A REAL JOB PAGE
# ---------------------------------------------------------

def is_job_link(url, title):

    url_lower = url.lower()
    title_lower = title.lower().strip()

    # -----------------------------------------------------
    # NEVER ACCEPT THESE SITE-WIDE PAGES
    # -----------------------------------------------------

    ignored_paths = [

        "/",
        "/latest-jobs/",
        "/admit-card/",
        "/result/",
        "/admission/",
        "/syllabus/",
        "/answer-key/",
        "/contact/",
        "/about/",
        "/privacy/",
        "/disclaimer/",
        "/sitemap/",
        "/category/",
        "/search/",
        "/wp-admin/",
        "/feed/",
    ]

    for path in ignored_paths:

        if url_lower.rstrip("/") == (
            BASE_URL + path
        ).rstrip("/"):

            return False

    # -----------------------------------------------------
    # IGNORE COMMON NAVIGATION TITLES
    # -----------------------------------------------------

    ignored_titles = {

        "home",
        "latest job",
        "latest jobs",
        "admit card",
        "result",
        "results",
        "admission",
        "syllabus",
        "answer key",
        "answer keys",
        "contact us",
        "about us",
        "privacy policy",
        "disclaimer",
        "sitemap",
    }

    if title_lower in ignored_titles:

        return False

    # -----------------------------------------------------
    # IGNORE CATEGORY / NAVIGATION URLS
    # -----------------------------------------------------

    ignored_url_parts = [

        "/category/",
        "/tag/",
        "/author/",
        "/page/",
        "?s=",
        "/feed",
        "/wp-json/",
    ]

    for part in ignored_url_parts:

        if part in url_lower:

            return False

    # -----------------------------------------------------
    # JOB-RELATED KEYWORDS
    # -----------------------------------------------------

    job_keywords = [

        "recruitment",
        "recruitment-2026",
        "recruitment-2025",
        "vacancy",
        "vacancies",
        "online-form",
        "online-form-2026",
        "online-form-2025",
        "apply-online",
        "application-form",
        "job",
        "jobs",
        "bharti",
        "bharti-2026",
        "bharti-2025",
        "apprentice",
        "apprentices",
        "teacher",
        "constable",
        "sub-inspector",
        "si-",
        "junior-engineer",
        "je-",
        "assistant",
        "officer",
        "clerk",
        "staff",
        "group-",
        "post",
        "posts",
        "10+2",
        "cpo",
        "ssc-",
        "upsc-",
        "rrb-",
        "ibps-",
        "bank-",
        "mpesb-",
        "bpssc-",
        "bssc-",
        "upsssc-",
        "upsc",
        "railway",
        "police",
        "army",
        "navy",
        "air-force",
    ]

    # Accept if title or URL contains a job-related keyword.
    combined = (
        title_lower + " " + url_lower
    )

    for keyword in job_keywords:

        if keyword in combined:

            return True

    return False


# ---------------------------------------------------------
# GET JOB LINKS FROM LATEST JOBS
# ---------------------------------------------------------

def get_job_links(html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    links = []

    for a in soup.find_all(
        "a",
        href=True
    ):

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

        # Only same website
        if not absolute_url.startswith(
            BASE_URL
        ):

            continue

        # Only HTTP/HTTPS
        if not absolute_url.startswith(
            ("http://", "https://")
        ):

            continue

        if not is_job_link(
            absolute_url,
            title
        ):

            continue

        links.append(
            {
                "title": title,
                "url": absolute_url
            }
        )

    # -----------------------------------------------------
    # REMOVE DUPLICATES
    # -----------------------------------------------------

    unique = {}

    for job in links:

        unique[job["url"]] = job

    return list(
        unique.values()
    )


# ---------------------------------------------------------
# CLASSIFY JOB
# ---------------------------------------------------------

def classify_job(job):

    today = date.today()

    start = None
    end = None

    # -----------------------------------------------------
    # START DATE
    # -----------------------------------------------------

    if job.get(
        "application_start"
    ):

        try:

            start = date.fromisoformat(
                job["application_start"]
            )

        except ValueError:

            pass

    # -----------------------------------------------------
    # END DATE
    # -----------------------------------------------------

    if job.get(
        "application_end"
    ):

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

    if start and start <= today:

        if end is None or end >= today:

            return "open"

    # -----------------------------------------------------
    # UNKNOWN
    # -----------------------------------------------------

    return "unknown"


# ---------------------------------------------------------
# ADD STATUS DATA
# ---------------------------------------------------------

def add_status_data(job):

    today = date.today()

    job["status"] = classify_job(
        job
    )

    job["days_left"] = None

    if job.get(
        "application_end"
    ):

        try:

            end = date.fromisoformat(
                job["application_end"]
            )

            job["days_left"] = (
                end - today
            ).days

        except ValueError:

            pass

    # -----------------------------------------------------
    # ADD SCRAPE DATE
    # -----------------------------------------------------

    job["scraped_date"] = (
        today.isoformat()
    )

    return job


# ---------------------------------------------------------
# SORT JOBS
# ---------------------------------------------------------

def sort_jobs(jobs):

    critical = [
        job
        for job in jobs
        if job["status"] == "critical"
    ]

    open_jobs = [
        job
        for job in jobs
        if job["status"] == "open"
    ]

    upcoming = [
        job
        for job in jobs
        if job["status"] == "upcoming"
    ]

    old = [
        job
        for job in jobs
        if job["status"] == "old"
    ]

    unknown = [
        job
        for job in jobs
        if job["status"] == "unknown"
    ]

    # -----------------------------------------------------
    # CRITICAL
    # Nearest deadline first
    # -----------------------------------------------------

    critical.sort(
        key=lambda job: (
            job.get("application_end")
            or "9999-12-31"
        )
    )

    # -----------------------------------------------------
    # OPEN
    # Nearest deadline first
    # -----------------------------------------------------

    open_jobs.sort(
        key=lambda job: (
            job.get("application_end")
            or "9999-12-31"
        )
    )

    # -----------------------------------------------------
    # UPCOMING
    # Earliest application start first
    # -----------------------------------------------------

    upcoming.sort(
        key=lambda job: (
            job.get("application_start")
            or "9999-12-31"
        )
    )

    # -----------------------------------------------------
    # OLD
    # Most recently expired first
    # -----------------------------------------------------

    old.sort(
        key=lambda job: (
            job.get("application_end")
            or "1900-01-01"
        ),
        reverse=True
    )

    # -----------------------------------------------------
    # UNKNOWN
    # Newest-looking entries first
    # -----------------------------------------------------

    unknown.sort(
        key=lambda job: (
            job.get("application_start")
            or job.get("notification_date")
            or "1900-01-01"
        ),
        reverse=True
    )

    return (
        critical
        + open_jobs
        + upcoming
        + old
        + unknown
    )


# ---------------------------------------------------------
# PRINT SUMMARY
# ---------------------------------------------------------

def print_summary(jobs):

    counts = {
        "critical": 0,
        "open": 0,
        "upcoming": 0,
        "old": 0,
        "unknown": 0,
    }

    for job in jobs:

        status = job.get(
            "status",
            "unknown"
        )

        if status in counts:

            counts[status] += 1

    print("\n")
    print("=" * 70)
    print("SCRAPER SUMMARY")
    print("=" * 70)

    print(
        f"Total jobs: {len(jobs)}"
    )

    print(
        f"Critical:   {counts['critical']}"
    )

    print(
        f"Open:       {counts['open']}"
    )

    print(
        f"Upcoming:   {counts['upcoming']}"
    )

    print(
        f"Old:        {counts['old']}"
    )

    print(
        f"Unknown:    {counts['unknown']}"
    )

    print("=" * 70)


# ---------------------------------------------------------
# SCRAPE
# ---------------------------------------------------------

def scrape():

    print("=" * 70)
    print("GOVERNMENT JOB TRACKER")
    print("=" * 70)

    print(
        "\nFetching latest jobs..."
    )

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
        f"Found {len(links)} possible job links."
    )

    if not links:

        print(
            "[WARNING] No job links found."
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

        seen_urls.add(
            url
        )

        print(
            f"\n[{index}/{len(links)}] {item['title']}"
        )

        print(
            f"    URL: {url}"
        )

        page = fetch_page(
            url
        )

        if not page:

            print(
                "    Skipped: page could not be fetched."
            )

            continue

        try:

            job = extract_job_page(
                url,
                page
            )

            # -------------------------------------------------
            # If article parser didn't get title,
            # use listing title.
            # -------------------------------------------------

            if not job["title"]:

                job["title"] = item["title"]

            # -------------------------------------------------
            # If title is garbage, use listing title.
            # -------------------------------------------------

            if len(
                job["title"]
            ) > 300:

                job["title"] = item["title"]

            # -------------------------------------------------
            # If extracted title is clearly a navigation title,
            # skip it.
            # -------------------------------------------------

            if not is_job_link(
                url,
                job["title"]
            ):

                print(
                    "    Skipped: not a job page."
                )

                continue

            job = add_status_data(
                job
            )

            jobs.append(
                job
            )

            print(
                f"    Start:  {job['application_start']}"
            )

            print(
                f"    End:    {job['application_end']}"
            )

            print(
                f"    Posts:  {job['posts']}"
            )

            print(
                f"    Status: {job['status']}"
            )

        except Exception as e:

            print(
                f"    [ERROR] {e}"
            )

        # -----------------------------------------------------
        # Don't hammer the website
        # -----------------------------------------------------

        time.sleep(
            0.5
        )

    # ---------------------------------------------------------
    # SORT
    # ---------------------------------------------------------

    jobs = sort_jobs(
        jobs
    )

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------

    print_summary(
        jobs
    )

    # ---------------------------------------------------------
    # SAVE
    # ---------------------------------------------------------

    output = {

        "last_updated":
            datetime.now().isoformat(),

        "source":
            LATEST_URL,

        "total_jobs":
            len(jobs),

        "jobs":
            jobs,
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

    print(
        f"\nSaved {len(jobs)} jobs to {OUTPUT_FILE}"
    )

    print(
        f"Output file: {OUTPUT_FILE}"
    )

    print("=" * 70)


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

if __name__ == "__main__":

    scrape()

#!/usr/bin/env python3
"""
Fetches job data from SimplifyJobs README and optionally a Google Sheet CSV,
then updates README.md with a formatted markdown table.
"""

import csv
import os
import re
import sys
from datetime import datetime, timezone
from io import StringIO

import requests

# Google Sheet published CSV URL (optional)
# Set via environment variable or leave empty to use only SimplifyJobs data
SHEET_CSV_URL = os.environ.get("SHEET_CSV_URL", "")

# SimplifyJobs Summer 2026 Internships README URL
SIMPLIFY_README_URL = "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/README.md"

# Expected column headers (case-insensitive matching)
EXPECTED_COLUMNS = ["company", "role", "location", "apply link"]

README_HEADER = """# Hardware Internships

A curated list of hardware engineering internships.

**Last updated:** {timestamp}

---

"""

README_TABLE_HEADER = """| Company | Role | Location | Apply |
|---------|------|----------|-------|
"""


def fetch_csv_data(url: str) -> str:
    """Fetch CSV content from the published Google Sheet URL."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def parse_csv(csv_content: str) -> list[dict]:
    """Parse CSV content and return list of job entries."""
    reader = csv.DictReader(StringIO(csv_content))

    # Normalize column names to lowercase for matching
    if reader.fieldnames is None:
        return []

    # Create mapping from expected columns to actual column names
    column_mapping = {}
    for field in reader.fieldnames:
        field_lower = field.lower().strip()
        for expected in EXPECTED_COLUMNS:
            if expected in field_lower or field_lower in expected:
                column_mapping[expected] = field
                break

    jobs = []
    for row in reader:
        job = {}
        for expected, actual in column_mapping.items():
            job[expected] = row.get(actual, "").strip()

        # Only include rows that have at least company and role
        if job.get("company") and job.get("role"):
            jobs.append(job)

    return jobs


def fetch_simplify_hardware_jobs() -> list[dict]:
    """Fetch hardware internships from SimplifyJobs README."""
    try:
        response = requests.get(SIMPLIFY_README_URL, timeout=30)
        response.raise_for_status()
        readme = response.text
    except requests.RequestException as e:
        print(f"Warning: Could not fetch SimplifyJobs README: {e}")
        return []

    # Find the hardware engineering section
    hw_section_header = "## 🔧 Hardware Engineering"
    hw_start = readme.find(hw_section_header)
    if hw_start == -1:
        print("Warning: Hardware Engineering section not found in SimplifyJobs README")
        return []

    # Find the next section (starts with ##)
    hw_end = readme.find("\n## ", hw_start + len(hw_section_header))
    if hw_end == -1:
        hw_section = readme[hw_start:]
    else:
        hw_section = readme[hw_start:hw_end]

    # Parse table rows
    jobs = []
    for match in re.finditer(r'<tr>(.*?)</tr>', hw_section, re.DOTALL):
        row = match.group(1)

        # Skip closed positions (🔒)
        if '🔒' in row:
            continue

        # Skip continuation rows (↳)
        if '>↳<' in row or '<td>↳</td>' in row:
            continue

        # Extract table cells
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
        if len(cells) < 4:
            continue

        # Cell 0: Company name (in <strong><a href="...">NAME</a></strong>)
        company_match = re.search(r'<a[^>]*>([^<]+)</a>', cells[0])
        company = company_match.group(1).strip() if company_match else ""

        # Cell 1: Role title
        role = re.sub(r'<[^>]+>', '', cells[1]).strip()

        # Cell 2: Location
        location = re.sub(r'<[^>]+>', '', cells[2]).strip()

        # Cell 3: Apply link (first href in the cell)
        apply_match = re.search(r'<a[^>]*href="([^"]+)"', cells[3])
        apply_url = apply_match.group(1).strip() if apply_match else ""

        # Only include if we have company and role
        if company and role:
            jobs.append({
                "company": company,
                "role": role,
                "location": location,
                "apply link": apply_url,
            })

    return jobs


def merge_jobs(sheet_jobs: list[dict], simplify_jobs: list[dict]) -> list[dict]:
    """Merge jobs from both sources, deduplicating by (company, role).

    Google Sheet entries take priority over SimplifyJobs entries.
    """
    # Create a set of (company, role) tuples from sheet jobs for deduplication
    seen = set()
    merged = []

    # Add sheet jobs first (they take priority)
    for job in sheet_jobs:
        key = (job.get("company", "").lower(), job.get("role", "").lower())
        if key not in seen:
            seen.add(key)
            merged.append(job)

    # Add SimplifyJobs entries that aren't duplicates
    for job in simplify_jobs:
        key = (job.get("company", "").lower(), job.get("role", "").lower())
        if key not in seen:
            seen.add(key)
            merged.append(job)

    return merged


def generate_table_row(job: dict) -> str:
    """Generate a markdown table row for a job entry."""
    company = job.get("company", "")
    role = job.get("role", "")
    location = job.get("location", "")
    apply_link = job.get("apply link", "")

    # Escape pipe characters in content
    company = company.replace("|", "\\|")
    role = role.replace("|", "\\|")
    location = location.replace("|", "\\|")

    # Create apply button/link (HTML used for target="_blank")
    if apply_link:
        apply_cell = f'<a href="{apply_link}" target="_blank">Apply</a>'
    else:
        apply_cell = "—"

    return f"| {company} | {role} | {location} | {apply_cell} |\n"


def generate_readme(jobs: list[dict]) -> str:
    """Generate the complete README.md content."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    readme = README_HEADER.format(timestamp=timestamp)

    if jobs:
        readme += "✨ Preparing for hardware interviews? Check out [LogiCode](https://logi-code.com/)! ✨\n\n"
        readme += "## Internships\n\n"
        readme += README_TABLE_HEADER
        for job in jobs:
            readme += generate_table_row(job)
    else:
        readme += "*No internship listings available yet.*\n"

    return readme


def main():
    """Main function to fetch data and update README."""
    sheet_jobs = []
    simplify_jobs = []

    # Fetch from Google Sheet if configured
    if SHEET_CSV_URL:
        print("Fetching data from Google Sheet...")
        try:
            csv_content = fetch_csv_data(SHEET_CSV_URL)
            print("Parsing CSV data...")
            sheet_jobs = parse_csv(csv_content)
            print(f"Found {len(sheet_jobs)} job listings from Google Sheet")
        except requests.RequestException as e:
            print(f"Warning: Could not fetch Google Sheet CSV: {e}")
    else:
        print("No Google Sheet URL configured, skipping...")

    # Fetch from SimplifyJobs README
    print("Fetching hardware internships from SimplifyJobs...")
    simplify_jobs = fetch_simplify_hardware_jobs()
    print(f"Found {len(simplify_jobs)} hardware internships from SimplifyJobs")

    # Merge both sources
    jobs = merge_jobs(sheet_jobs, simplify_jobs)
    print(f"Total after merge: {len(jobs)} job listings")

    if not jobs:
        print("No jobs found from any source")
        sys.exit(1)

    print("Generating README...")
    readme_content = generate_readme(jobs)

    # Read existing README if it exists
    readme_path = "README.md"
    existing_content = ""
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            existing_content = f.read()

    # Check if content changed (ignoring timestamp line)
    def strip_timestamp(content):
        lines = content.split("\n")
        return "\n".join(line for line in lines if not line.startswith("**Last updated:**"))

    if strip_timestamp(existing_content) == strip_timestamp(readme_content):
        print("No changes detected (excluding timestamp)")
        sys.exit(0)

    # Write new README
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

    print("README.md updated successfully!")
    sys.exit(0)


if __name__ == "__main__":
    main()

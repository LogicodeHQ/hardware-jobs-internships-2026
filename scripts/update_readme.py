#!/usr/bin/env python3
"""
Fetches hardware internship data and updates README.md with a formatted markdown table.
"""

import csv
import os
import re
import sys
from datetime import datetime, timezone
from io import StringIO

import requests

# Google Sheet published CSV URL (optional)
SHEET_CSV_URL = os.environ.get("SHEET_CSV_URL", "")

# Primary data source URL
DATA_SOURCE_URL = os.environ.get("DATA_SOURCE_URL", "")

# Expected column headers (case-insensitive matching)
EXPECTED_COLUMNS = ["company", "role", "location", "apply link", "age"]

README_HEADER = """# Hardware Internships

A curated list of hardware engineering internships.

**Last updated:** {timestamp}

---

"""

README_TABLE_HEADER = """| Company | Role | Location | Apply | Age |
|---------|------|----------|-------|-----|
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


def fetch_hardware_jobs() -> list[dict]:
    """Fetch hardware internships from the primary data source."""
    try:
        response = requests.get(DATA_SOURCE_URL, timeout=30)
        response.raise_for_status()
        readme = response.text
    except requests.RequestException as e:
        print(f"Warning: Could not fetch data source: {e}")
        return []

    # Find the hardware engineering section
    hw_section_header = "## 🔧 Hardware Engineering"
    hw_start = readme.find(hw_section_header)
    if hw_start == -1:
        print("Warning: Hardware Engineering section not found")
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
        if len(cells) < 5:
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

        # Cell 4: Age (e.g., "2d", "1w")
        age = re.sub(r'<[^>]+>', '', cells[4]).strip()

        # Only include if we have company and role
        if company and role:
            jobs.append({
                "company": company,
                "role": role,
                "location": location,
                "apply link": apply_url,
                "age": age,
            })

    return jobs


def merge_jobs(sheet_jobs: list[dict], source_jobs: list[dict]) -> list[dict]:
    """Merge jobs from both sources, deduplicating by (company, role)."""
    seen = set()
    merged = []

    for job in sheet_jobs:
        key = (job.get("company", "").lower(), job.get("role", "").lower())
        if key not in seen:
            seen.add(key)
            merged.append(job)

    for job in source_jobs:
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
    age = job.get("age", "")

    # Escape pipe characters in content
    company = company.replace("|", "\\|")
    role = role.replace("|", "\\|")
    location = location.replace("|", "\\|")
    age = age.replace("|", "\\|")

    # Create apply button/link (HTML used for target="_blank")
    if apply_link:
        apply_cell = f'<a href="{apply_link}" target="_blank">Apply</a>'
    else:
        apply_cell = "—"

    return f"| {company} | {role} | {location} | {apply_cell} | {age} |\n"


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
    if not DATA_SOURCE_URL:
        print("Error: DATA_SOURCE_URL environment variable not set")
        sys.exit(1)

    sheet_jobs = []
    source_jobs = []

    if SHEET_CSV_URL:
        print("Fetching data from Google Sheet...")
        try:
            csv_content = fetch_csv_data(SHEET_CSV_URL)
            sheet_jobs = parse_csv(csv_content)
            print(f"Found {len(sheet_jobs)} listings from Google Sheet")
        except requests.RequestException as e:
            print(f"Warning: Could not fetch Google Sheet: {e}")

    print("Fetching hardware internships...")
    source_jobs = fetch_hardware_jobs()
    print(f"Found {len(source_jobs)} hardware internships")

    jobs = merge_jobs(sheet_jobs, source_jobs)
    print(f"Total: {len(jobs)} listings")

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

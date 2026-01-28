#!/usr/bin/env python3
"""
Fetches job data from a published Google Sheet CSV and updates README.md
with a formatted markdown table.
"""

import csv
import os
import sys
from datetime import datetime, timezone
from io import StringIO

import requests

# Google Sheet published CSV URL
# Set via environment variable or replace with your published CSV URL
SHEET_CSV_URL = os.environ.get("SHEET_CSV_URL", "")

# Expected column headers (case-insensitive matching)
EXPECTED_COLUMNS = ["company", "role", "location", "apply link", "type"]

# Job type categories (order matters - first match wins)
TYPE_INTERNSHIP = "internship"
TYPE_NEW_GRAD = "new grad"

README_HEADER = """# Hardware Jobs & Internships

A curated list of hardware engineering jobs and internships, automatically updated from a Google Sheet.

**Last updated:** {timestamp}

---

"""

README_TABLE_HEADER = """| Company | Role | Location | Apply |
|---------|------|----------|-------|
"""

README_FOOTER = """
---

## Contributing

Want to add a job posting? Submit it to our [Google Sheet]({sheet_url}) and it will appear here automatically!

## About

This repository is automatically updated every 4 hours using GitHub Actions.

Data is sourced from a community-maintained Google Sheet and synced via the published CSV export.
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


def categorize_jobs(jobs: list[dict]) -> tuple[list[dict], list[dict]]:
    """Separate jobs into internships and new grad positions."""
    internships = []
    new_grad = []

    for job in jobs:
        job_type = job.get("type", "").lower().strip()

        if "intern" in job_type:
            internships.append(job)
        elif "new grad" in job_type or "newgrad" in job_type or "entry" in job_type:
            new_grad.append(job)
        else:
            # Default to new grad if type is unspecified or unrecognized
            new_grad.append(job)

    return internships, new_grad


def generate_readme(jobs: list[dict], sheet_url: str = "") -> str:
    """Generate the complete README.md content."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    readme = README_HEADER.format(timestamp=timestamp)

    if jobs:
        internships, new_grad = categorize_jobs(jobs)

        # Internships section
        readme += "## Internships\n\n"
        if internships:
            readme += README_TABLE_HEADER
            for job in internships:
                readme += generate_table_row(job)
        else:
            readme += "*No internship listings available yet.*\n"

        readme += "\n"

        # New Grad section
        readme += "## New Grad Positions\n\n"
        if new_grad:
            readme += README_TABLE_HEADER
            for job in new_grad:
                readme += generate_table_row(job)
        else:
            readme += "*No new grad listings available yet.*\n"
    else:
        readme += "*No job listings available yet. Check back soon!*\n"

    # Extract base sheet URL for contributing section
    if sheet_url:
        # Convert CSV export URL to regular sheet URL for display
        base_url = sheet_url.split("/pub")[0] if "/pub" in sheet_url else sheet_url
        readme += README_FOOTER.format(sheet_url=base_url)
    else:
        readme += README_FOOTER.format(sheet_url="#")

    return readme


def main():
    """Main function to fetch data and update README."""
    if not SHEET_CSV_URL:
        print("Error: SHEET_CSV_URL environment variable not set")
        print("Please set it to your published Google Sheet CSV URL")
        sys.exit(1)

    print(f"Fetching data from Google Sheet...")

    try:
        csv_content = fetch_csv_data(SHEET_CSV_URL)
    except requests.RequestException as e:
        print(f"Error fetching CSV: {e}")
        sys.exit(1)

    print("Parsing CSV data...")
    jobs = parse_csv(csv_content)
    print(f"Found {len(jobs)} job listings")

    print("Generating README...")
    readme_content = generate_readme(jobs, SHEET_CSV_URL)

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

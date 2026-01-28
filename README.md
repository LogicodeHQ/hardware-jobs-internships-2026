# Hardware Jobs & Internships

A curated list of hardware engineering jobs and internships, automatically updated from a Google Sheet.

**Last updated:** Not yet synced

---

*No job listings available yet. Configure your Google Sheet and run the sync workflow!*

---

## Setup Instructions

1. **Create a Google Sheet** with these columns:
   - Company
   - Role
   - Location
   - Apply Link

2. **Publish the sheet as CSV:**
   - Go to File → Share → Publish to web
   - Select your sheet and choose "Comma-separated values (.csv)"
   - Click Publish and copy the URL

3. **Add the secret to this repository:**
   - Go to Settings → Secrets and variables → Actions
   - Create a new secret named `SHEET_CSV_URL`
   - Paste your published CSV URL as the value

4. **Run the workflow:**
   - Go to Actions → "Sync Jobs from Google Sheet"
   - Click "Run workflow"

The README will automatically update with your job listings!

---

## Contributing

Want to add a job posting? Submit it to our Google Sheet and it will appear here automatically!

## About

This repository is automatically updated every 4 hours using GitHub Actions.

Data is sourced from a community-maintained Google Sheet and synced via the published CSV export.

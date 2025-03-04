# LinkedIn Jobs Scraper

A Python-based Playwright scraper that automates searching for jobs on LinkedIn and stores them in a local SQLite database.  
This was created to streamline job-hunting for specific roles and locations while filtering out unwanted positions

## Features

- **Chrome CDP Connection**: Launches or connects to Google Chrome via the [Chrome DevTools Protocol (CDP)](https://chromedevtools.github.io/devtools-protocol/)

- **Job Searching**: Automatically fills in the job title and location on LinkedIn Jobs, then iterates through paginated results

- **Duplicate Check**: Skips any job that has already been scraped and stored in the `jobs` table

- **Company Tracking**: Records the company (employer) in a separate `employers` table, if not already present

- **Blocklist**: Filters out job postings containing unwanted terms (e.g., `Sr`, `DevOps`, etc.) so you can target only relevant positions

- **SQLite Database**: Stores all new jobs in a local SQLite file, making it easy to query for references or data analysis later

## Getting Started

### Prerequisites

- **Python 3.8+**  
- **Google Chrome** (with remote debugging enabled via the script)
- **Playwright**  
- **SQLite** (installed by default with most Python distributions)  
- A basic understanding of environment variables and Python virtual environments

### Installation

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/ThatDudeAlex/LinkedIn-Jobs-Scraper.git
   cd LinkedIn-Jobs-Scraper
   ```

2. **Create and Activate a Virtual Environment (Recommended)**:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

   Then install the required browser binaries:
   ```bash
   playwright install
   ```

4. **Set Up Environment Variables**:

   Create a file named `.env` in the project root and populate it with the following variables (modify according to your environment). For example:

   ```bash
   # .env
   CDP_URL=http://127.0.0.1:9222

   CHROME_PATH=/usr/bin/google-chrome

   CHROME_PROFILE_PATH=/home/youruser/.config/google-chrome

   CHROME_PROFILE_NAME=Default

   DATABASE_PATH=/absolute/path/to/jobs.db

   LOGGING_PATH=/absolute/path/to/logs.txt

   JOB_SEARCH_BASE_URL=https://www.linkedin.com/jobs/search/

   JOBS_PAGE_BASE_URL=https://www.linkedin.com/jobs/view/

   TERMS_BLOCKLIST=Sr,DevOps

   STATE=Florida
   ```

   * **CDP_URL**: The URL where Chrome is listening for remote debugging (default is `http://127.0.0.1:9222`)

   * **CHROME_PATH**: Path to your Google Chrome installation

   * **CHROME_PROFILE_PATH**: Path to your Chrome user profile data folder

   * **CHROME_PROFILE_NAME**: Specific user profile name (default is `"Default"`)

   * **DATABASE_PATH**: Full path to the SQLite database file (`jobs.db` for example)

   * **LOGGING_PATH**: Full path for the log file output

   * **JOB_SEARCH_BASE_URL**: The base URL used for searching jobs on LinkedIn

   * **JOBS_PAGE_BASE_URL**: Used to construct direct links to individual jobs

   * **TERMS_BLOCKLIST**: Comma-separated list of terms that will cause a job post to be skipped

   * **STATE**: The state (or region) you want to record for new employers

5. **Run the Scraper**:

   ```bash
   python -m scraper.main -s "Software Engineer" -l "Miami, FL"
   ```

   The arguments `-s` (or `--job_search`) and `-l` (or `--location`) are required:

   * `--job_search`: Job title, skill, or company to search for.
   * `--location`: City, state, or zip code.

### Project Structure

```bash
LinkedIn-Jobs-Scraper/
│
├── scraper/
│   ├── __init__.py
│   ├── main.py
│   ├── job_scraper.py
│   ├── browser_manager.py
│   ├── database_manager.py
│   └── page_handler.py
│
│
├── .env
├── .gitignore
├── README.md
├── locators.py
└── ...
```

### How It Works

1. **BrowserManager**:

   * Starts or connects to a running Chrome instance via CDP on the specified port

   * Manages the browser context and page

2. **DatabaseManager**:

   * Creates and manages a SQLite database with two tables: `jobs` and `employers`

   * Checks for existing job IDs and employer entries

3. **PageHandler**:

   * Encapsulates Playwright actions (click, fill, scroll into view, etc.)

   * Implements short random waits to mimic human interaction
   
4. **JobScraper**:

   * Ties everything together:

       * Initializes the database and Chrome

       * Loads LinkedIn Jobs search page and filters by search keywords and location

       * Iterates over paginated results, storing new jobs and new employers in the database

## Troubleshooting

* **Chrome Not Launching**: Make sure the paths `CHROME_PATH` and `CHROME_PROFILE_PATH` are valid. Check your environment variables

* **Remote Debugging Failure**: If `CDP_URL` is already in use, kill any existing Chrome processes or change the port number

* **No Jobs Found**: Confirm your search terms actually produce results on LinkedIn. Also check the blocklist for accidental filtering

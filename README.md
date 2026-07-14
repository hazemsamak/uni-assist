# Uni-Assist Application Status API

A containerized FastAPI service that scrapes the uni-assist portal to retrieve your application names and status, exposing them via a clean JSON API.

## Features

- **Automated Scraping**: Uses Playwright to navigate, authenticate, and extract application status details in headless mode.
- **FastAPI Interface**: Exposes a simple `GET /status` API endpoint.
- **Session Caching**: Stores the login state in `data/auth.json` to bypass credentials-based login on subsequent requests, avoiding rate limits or CAPTCHA triggers.
- **Docker-Ready**: Comes with `Dockerfile` and `docker-compose.yml` pre-configured to easily build and run anywhere.
- **Debugging & Screenshots**: Saves page screenshots and page HTML source on success and failure for easy troubleshooting.

---

## Configuration

The application reads credentials for a single account from a local `.env` file.

1. Create a `.env` file in the root directory (if it does not exist already):
   ```env
   UNI_ASSIST_EMAIL=your-email@example.com
   UNI_ASSIST_PASSWORD=your-password
   ```

---

## Usage with Docker (Recommended)

Running with Docker manages all browser dependencies and drivers automatically.

### 1. Build and Run the Container
Start the API in the background:
```bash
docker compose up --build -d
```

### 2. View Logs
Ensure the container started successfully:
```bash
docker compose logs -f
```

### 3. Stop the Container
To stop and remove the container:
```bash
docker compose down
```

---

## Usage without Docker (Local Machine)

To run the application directly on your local system:

### 1. Set Up a Virtual Environment (Optional but recommended)
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies
Install Python packages and setup Playwright browser binaries:
```bash
pip install -r requirements.txt
playwright install chromium
```
### 3. Start the FastAPI Server
Run the application using Uvicorn:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Running/Testing with Python Scripts directly
You can execute the Python scripts directly for manual verification or standalone execution:

- **Run the FastAPI Server via Python**:
  ```bash
  python app.py
  ```
  This starts the FastAPI server locally on port `8000` (identical to running it via `uvicorn app:app`).

- **Run the Standalone Scraper (with Browser GUI / Interactive Login)**:
  ```bash
  python scrape_status.py
  ```
  This runs the original scraper logic. If `data/auth.json` is missing or expired, a visible Chromium browser window will open. Complete the login, navigate to the applications page, then press **Enter** in your terminal to save the session to `data/auth.json`.

- **Run the Standalone Scraper (Headless)**:
  If a valid `data/auth.json` is already present, check statuses silently in the terminal without opening a GUI browser:
  ```bash
  python scrape_status.py --headless
  ```

---

## API Endpoints

Once the application is running (locally or inside Docker), you can interact with it at `http://localhost:8000`.

### `GET /`
- **Description**: Health check endpoint.
- **Response**:
  ```json
  {
    "status": "running",
    "message": "Uni-Assist Scraper API is running. Call GET /status to fetch applications."
  }
  ```

### `GET /status`
- **Description**: Logs in (if needed), scrapes your applications, saves the session cache, and returns the status list.
- **Response**:
  ```json
  {
    "status": "success",
    "count": 2,
    "applications": [
      {
        "subject": "Mechatronik, B.Sc. - bilinguale Studienvariante",
        "degree": "Bachelor of Science",
        "university": "Technische Hochschule Mittelhessen (THM)",
        "status": "Faulty"
      },
      {
        "subject": "Applied Artificial Intelligence",
        "degree": "Bachelor",
        "university": "Technische Hochschule Rosenheim",
        "status": "Faulty"
      }
    ]
  }
  ```

---

## Debugging and Troubleshooting

When the API runs, it outputs debug files in the `data/` directory:
- **`data/auth.json`**: Caches the authenticated localStorage/cookies session. Do not delete unless you need to force a re-login.
- **`data/applications_screenshot.png`**: Viewport screenshot of the portal pages taken during the scrape process.
- **`data/applications_page.html`**: Saved HTML source of the application portal page.
- **`data/error_screenshot.png`**: Automatically captured if the scraping sequence throws an exception.

import os
import sys
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from playwright.sync_api import sync_playwright

# Load environment variables from .env file if it exists (for local testing)
load_dotenv()

app = FastAPI(
    title="Uni-Assist Application Status API",
    description="API to scrape and retrieve uni-assist application names and statuses.",
    version="1.0.0"
)

# Directory to store session state and debug assets
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

AUTH_FILE = os.path.join(DATA_DIR, "auth.json")
TARGET_URL = "https://my.uni-assist.de/antragsuebersicht"

def run_scraping():
    email = os.getenv("UNI_ASSIST_EMAIL")
    password = os.getenv("UNI_ASSIST_PASSWORD")
    
    if not email or not password:
        raise HTTPException(
            status_code=500,
            detail="UNI_ASSIST_EMAIL or UNI_ASSIST_PASSWORD environment variable is not configured."
        )

    with sync_playwright() as p:
        # Launch browser in headless mode. 
        # Inside Docker, we need to pass sandboxing flags to avoid Chromium crashes.
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        
        # Load the saved session state if it exists
        if os.path.exists(AUTH_FILE):
            print(f"Loading session state from '{AUTH_FILE}'...")
            context = browser.new_context(storage_state=AUTH_FILE)
        else:
            print("No saved session state found. Creating fresh context...")
            context = browser.new_context()
            
        page = context.new_page()
        
        try:
            print(f"Navigating to {TARGET_URL}...")
            page.goto(TARGET_URL)
            
            # Wait dynamically until either the cards load (logged in) or we are redirected to login/auth
            try:
                page.wait_for_function(
                    "() => window.location.href.includes('login') || "
                    "window.location.href.includes('auth') || "
                    "document.querySelector('[data-test=\"auswahlliste-item\"]') !== null",
                    timeout=15000
                )
            except Exception:
                print("Timeout waiting for initial page state detection.")
            
            current_url = page.url
            print(f"Current page URL: {current_url}")
            
            # Check if session has expired or is redirected to login page
            is_login_page = "login" in current_url.lower() or "auth" in current_url.lower()
            
            if is_login_page or not os.path.exists(AUTH_FILE):
                print("Session expired or missing. Attempting automated login...")
                
                # E-mail selector strategies
                email_input = None
                for selector in ['input[type="email"]', 'input[name="email"]', 'input[id*="email" i]', 'input[placeholder*="mail" i]']:
                    try:
                        if page.locator(selector).is_visible():
                            email_input = page.locator(selector)
                            break
                    except Exception:
                        continue
                
                # Password selector strategies
                password_input = None
                for selector in ['input[type="password"]', 'input[name="password"]', 'input[id*="password" i]', 'input[placeholder*="pass" i]']:
                    try:
                        if page.locator(selector).is_visible():
                            password_input = page.locator(selector)
                            break
                    except Exception:
                        continue
                
                if not email_input or not password_input:
                    raise Exception("Could not find email or password input fields on the login page.")
                
                email_input.fill(email)
                password_input.fill(password)
                print("Credentials entered.")
                
                # Submit button strategies
                submit_button = None
                for selector in ['button[type="submit"]', 'button:has-text("Log in")', 'button:has-text("Anmelden")', 'button:has-text("Sign in")']:
                    try:
                        if page.locator(selector).is_visible():
                            submit_button = page.locator(selector)
                            break
                    except Exception:
                        continue
                
                if not submit_button:
                    raise Exception("Could not locate login submit button.")
                
                submit_button.click()
                print("Clicking submit. Waiting for navigation away from login...")
                
                # Wait to see if we navigate away from the login page
                try:
                    page.wait_for_function(
                        "() => !window.location.href.includes('login') && !window.location.href.includes('auth')",
                        timeout=15000
                    )
                except Exception:
                    raise Exception("Automated login failed. Please verify credentials or check for CAPTCHA/MFA block.")
                
                # Save session storage state
                context.storage_state(path=AUTH_FILE)
                print(f"Session state saved successfully to '{AUTH_FILE}'.")
            
            # Ensure we are on the target overview page
            if "antragsuebersicht" not in page.url.lower():
                print(f"Current URL is '{page.url}'. Navigating back to '{TARGET_URL}'...")
                page.goto(TARGET_URL)
            
            # Ensure application cards are loaded
            try:
                page.wait_for_selector('[data-test="auswahlliste-item"]', timeout=15000)
            except Exception:
                print("Timeout waiting for application list cards.")
            
            # Save page source and screenshot for debugging
            try:
                page.screenshot(path=os.path.join(DATA_DIR, "applications_screenshot.png"))
                with open(os.path.join(DATA_DIR, "applications_page.html"), "w", encoding="utf-8") as f:
                    f.write(page.content())
                print(f"Saved debug screenshot and HTML to '{DATA_DIR}/'. Current URL: {page.url}")
            except Exception as se:
                print(f"Failed to save debug assets: {se}")
                
            cards = page.locator('[data-test="auswahlliste-item"]')
            count = cards.count()
            print(f"Extracted application count: {count}")
            
            applications = []
            for i in range(count):
                card = cards.nth(i)
                
                # Extract course name
                subject = "Unknown"
                subject_loc = card.locator('[data-test="studienfach-name"]')
                if subject_loc.count() > 0:
                    subject = subject_loc.first.inner_text().strip()
                    
                # Extract university name
                university = "Unknown"
                univ_loc = card.locator('[data-test="hochschule-name"]')
                if univ_loc.count() > 0:
                    university = univ_loc.first.inner_text().strip()
                    
                # Extract degree name
                degree = "Unknown"
                degree_loc = card.locator('[data-test="abschluss-name"]')
                if degree_loc.count() > 0:
                    degree = degree_loc.first.inner_text().strip()
                    
                # Extract status
                status_text = "Unknown"
                status_loc = card.locator('[data-test="application-status"]')
                if status_loc.count() > 0:
                    raw_status = status_loc.first.inner_text().strip()
                    if raw_status.startswith("checklist"):
                        status_text = raw_status.replace("checklist", "", 1).strip()
                    else:
                        status_text = raw_status
                
                applications.append({
                    "subject": subject,
                    "degree": degree,
                    "university": university,
                    "status": status_text.strip()
                })
            
            return {
                "status": "success",
                "count": len(applications),
                "applications": applications
            }
            
        except Exception as e:
            # Capture screenshot on failure inside container directory for troubleshooting
            try:
                page.screenshot(path=os.path.join(DATA_DIR, "error_screenshot.png"))
                print(f"Saved error screenshot to '{DATA_DIR}/error_screenshot.png'")
            except Exception:
                pass
            raise HTTPException(
                status_code=500,
                detail=f"Scraping failed: {str(e)}"
            )
        finally:
            browser.close()

@app.get("/")
def read_root():
    return {
        "status": "running",
        "message": "Uni-Assist Scraper API is running. Call GET /status to fetch applications."
    }

@app.get("/status")
def get_applications_status():
    """Scrapes the uni-assist portal and returns application status."""
    return run_scraping()

if __name__ == "__main__":
    import uvicorn
    # Allow running directly via python app.py
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

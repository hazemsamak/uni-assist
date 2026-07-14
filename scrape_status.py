#!/usr/bin/env python3
import os
import sys
import time
import getpass
from dotenv import load_dotenv, set_key
from playwright.sync_api import sync_playwright

# Load environment variables from .env file if it exists
ENV_FILE = ".env"
load_dotenv(ENV_FILE)

# Directory to store session state and debug assets
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

AUTH_FILE = os.path.join(DATA_DIR, "auth.json")
TARGET_URL = "https://my.uni-assist.de/antragsuebersicht"

def get_credentials():
    """Retrieves credentials from environment variables or prompts user to input and optionally store them."""
    email = os.getenv("UNI_ASSIST_EMAIL")
    password = os.getenv("UNI_ASSIST_PASSWORD")

    if not email or not password:
        print("\n" + "="*70)
        print("CREDENTIALS STORAGE CONFIGURATION")
        print("="*70)
        print("To automate the login process, we need your uni-assist credentials.")
        print("Your credentials can be stored securely in a local '.env' file.")
        print("="*70 + "\n")
        
        if not email:
            email = input("Enter your uni-assist E-mail: ").strip()
        if not password:
            password = getpass.getpass("Enter your uni-assist Password: ").strip()
            
        save_choice = input("\nWould you like to store these credentials in .env for future runs? (y/n): ").strip().lower()
        if save_choice in ['y', 'yes']:
            # Create .env if it doesn't exist
            if not os.path.exists(ENV_FILE):
                open(ENV_FILE, 'w').close()
            set_key(ENV_FILE, "UNI_ASSIST_EMAIL", email)
            set_key(ENV_FILE, "UNI_ASSIST_PASSWORD", password)
            print(f"[SUCCESS] Credentials saved to '{ENV_FILE}'. Make sure to keep this file secure.")
            
    return email, password

def setup_session(email=None, password=None):
    """Attempts automated login using credentials. Falls back to manual login if needed."""
    print("\n" + "="*70)
    print("SESSION SETUP MODE")
    print("="*70)
    print("1. A visible Chromium browser window will open shortly.")
    
    if email and password:
        print("2. The script will attempt to log in automatically with your credentials.")
        print("3. If a CAPTCHA or verification is encountered, please complete it manually.")
    else:
        print("2. Please log in manually in the browser window.")
        
    print(f"4. Navigate to your application overview page if not automatically redirected:")
    print(f"   {TARGET_URL}")
    print("5. Once you are logged in and see your applications, return to this terminal")
    print("   and press Enter to save your login session.")
    print("="*70 + "\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        print(f"Navigating to {TARGET_URL}...")
        page.goto(TARGET_URL)
        
        # If credentials are provided, attempt automated login
        if email and password:
            try:
                print("Attempting automated login...")
                # Allow page to load the login form
                page.wait_for_timeout(3000)
                
                # E-mail selector strategies
                email_input = None
                for selector in ['input[type="email"]', 'input[name="email"]', 'input[id*="email" i]', 'input[placeholder*="mail" i]']:
                    if page.locator(selector).is_visible():
                        email_input = page.locator(selector)
                        break
                
                # Password selector strategies
                password_input = None
                for selector in ['input[type="password"]', 'input[name="password"]', 'input[id*="password" i]', 'input[placeholder*="pass" i]']:
                    if page.locator(selector).is_visible():
                        password_input = page.locator(selector)
                        break
                
                if email_input and password_input:
                    email_input.fill(email)
                    password_input.fill(password)
                    print("Filled in credentials.")
                    
                    # Submit button strategies
                    submit_button = None
                    for selector in ['button[type="submit"]', 'button:has-text("Log in")', 'button:has-text("Anmelden")', 'button:has-text("Sign in")']:
                        if page.locator(selector).is_visible():
                            submit_button = page.locator(selector)
                            break
                    
                    if submit_button:
                        submit_button.click()
                        print("Clicked submit button. Waiting for page redirection...")
                        page.wait_for_timeout(5000)
                    else:
                        print("[WARNING] Submit button selector not found. Please click log in manually.")
                else:
                    print("[WARNING] Could not locate email/password input fields automatically.")
                    print("Please enter them manually in the opened browser window.")
            except Exception as e:
                print(f"[WARNING] Automated login failed due to an error: {e}")
                print("Please log in manually in the opened browser window.")
        
        # User verification/fallback step
        input("\n>>> Press Enter here in the terminal ONCE YOU ARE LOGGED IN and see your applications... <<<")
        
        # Save storage state
        context.storage_state(path=AUTH_FILE)
        print(f"\n[SUCCESS] Session successfully saved to '{AUTH_FILE}'.")
        print("Closing browser...")
        browser.close()

def check_status(headless=False):
    """Loads the saved session and checks the application status."""
    if not os.path.exists(AUTH_FILE):
        print(f"[WARNING] Session file '{AUTH_FILE}' not found. Initiating setup...")
        email, password = get_credentials()
        setup_session(email, password)
        return

    print("\n" + "="*70)
    print("CHECKING APPLICATION STATUS")
    print("="*70)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(storage_state=AUTH_FILE)
        page = context.new_page()
        
        print(f"Navigating to {TARGET_URL}...")
        page.goto(TARGET_URL)
        
        # Wait a few seconds for dynamic JS/Angular content to load
        page.wait_for_timeout(5000)
        
        current_url = page.url
        print(f"Current page URL: {current_url}")
        
        # Check if session has expired
        if "login" in current_url.lower() or "auth" in current_url.lower():
            print("\n[WARNING] Session appears to have expired (redirected to login).")
            print(f"Removing old '{AUTH_FILE}' and requesting fresh login...")
            try:
                os.remove(AUTH_FILE)
            except OSError:
                pass
            browser.close()
            email, password = get_credentials()
            setup_session(email, password)
            return
            
        print("Successfully logged in. Extracting application details...")
        
        # Take a screenshot for visual verification
        screenshot_path = os.path.join(DATA_DIR, "applications_screenshot.png")
        page.screenshot(path=screenshot_path)
        print(f"Saved viewport screenshot to '{screenshot_path}'")
        
        # Save page source for debugging
        source_path = os.path.join(DATA_DIR, "applications_page.html")
        with open(source_path, "w", encoding="utf-8") as f:
            f.write(page.content())
        print(f"Saved raw page HTML source to '{source_path}'")
        
        # Extract applications
        print("\n--- EXTRACTED APPLICATIONS ---")
        try:
            page.wait_for_selector('[data-test="auswahlliste-item"]', timeout=15000)
        except Exception:
            print("[WARNING] Timeout waiting for application card selector.")
            
        cards = page.locator('[data-test="auswahlliste-item"]')
        count = cards.count()
        print(f"Total number of applications found: {count}\n")
        
        for i in range(count):
            card = cards.nth(i)
            
            # Extract subject/course name
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
                # Clean up icon name (e.g. "checklist") if it is prepended
                if raw_status.startswith("checklist"):
                    status_text = raw_status.replace("checklist", "", 1).strip()
                else:
                    status_text = raw_status
            
            print(f"- {subject} ({degree}) at {university}")
            print(f"  status: {status_text.lower()}")
            print("-" * 50)
                
        print("\n" + "="*70)
        print(f"Extraction complete. You can inspect the full HTML structure in '{DATA_DIR}/applications_page.html'")
        print(f"or view the screenshot in '{DATA_DIR}/applications_screenshot.png' for visual verification.")
        print("="*70)
        
        browser.close()

if __name__ == "__main__":
    # If auth session doesn't exist, get credentials and run setup first
    if not os.path.exists(AUTH_FILE):
        email, password = get_credentials()
        setup_session(email, password)
    else:
        # If session exists, run status check
        is_headless = "--headless" in sys.argv
        check_status(headless=is_headless)

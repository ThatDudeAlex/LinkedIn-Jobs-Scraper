import socket
import sys
from playwright.async_api import async_playwright, Playwright
from locators import LOCATORS
from dotenv import load_dotenv
import sqlite3
import math
import asyncio
import os
import random
import logging
import subprocess
import time

load_dotenv()


class BrowserManager:
    def __init__(self, logger):
        self.logger = logger
        self.browser = None
        self.context = None
        self.page = None
        self.chrome_process = None
        self.playwright = None

    
    def get_chrome_profile_path(self):
        if sys.platform == "darwin":  # macOS
            default_path = os.path.expanduser("~/Library/Application Support/Google/Chrome")
        elif sys.platform == "win32":  # Windows
            default_path = os.path.join(os.getenv("LOCALAPPDATA"), "Google", "Chrome", "User Data")
        elif sys.platform == "linux":  # Linux (Chromium or Chrome)
            default_path = os.path.expanduser("~/.config/google-chrome")
        else:
            raise RuntimeError("Unsupported operating system")

        return os.getenv("CHROME_PROFILE_PATH", default_path)
    

    def get_chrome_executable_path(self):
        if sys.platform == "darwin":  # macOS
            default_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

        elif sys.platform == "win32":  # Windows
            program_files = os.getenv("PROGRAMFILES", "C:\\Program Files")
            default_path = os.path.join(program_files, "Google", "Chrome", "Application", "chrome.exe")
            
            # Check if running on 32-bit Windows
            if not os.path.exists(default_path):
                default_path = os.path.join(os.getenv("PROGRAMFILES(X86)", "C:\\Program Files (x86)"), "Google", "Chrome", "Application", "chrome.exe")
            
        elif sys.platform == "linux":  # Linux
            possible_paths = [
                "/usr/bin/google-chrome",
                "/usr/local/bin/google-chrome",
                "/opt/google/chrome/google-chrome"
            ]
            default_path = next((path for path in possible_paths if os.path.exists(path)), possible_paths[0])
        else:
            raise RuntimeError("Unsupported operating system")

        return os.getenv("CHROME_PATH", default_path)


    async def connect_to_existing_chrome(self, cdp_url):
        """
        Connects to an existing Chrome session via CDP.
        """
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.connect_over_cdp(cdp_url)
        self.context = self.browser.contexts[0] if self.browser.contexts else await self.browser.new_context()

        if self.context.pages:
            self.page = self.context.pages[0]  # Reuse existing page
        else:
            self.page = await self.context.new_page()

        self.logger.info("✅ Browser Connected to existing Chrome")
        return self.page


    async def start_chrome_with_cdp(self):
        """
        Starts a new Chrome process with a specific user profile and connects Playwright to it
        """
        cdp_url = os.getenv('CDP_URL', 'http://127.0.0.1:9222')
        host, port = cdp_url.replace("http://", "").split(":")
        port = int(port)

        # Sets up the correct Chrome profile name and profile name
        chrome_profile_name = os.getenv('CHROME_PROFILE_NAME', "Default")
        chrome_profile_path = self.get_chrome_profile_path()
        chrome_path = self.get_chrome_executable_path()

        # Checks if Chrome is already running before launching
        if self.is_chrome_running():
            self.logger.info("✅ Chrome is already running. Skipping startup.")
        else:
            self.logger.info("🔄 Stopping existing Chrome processes...")
            self.kill_chrome_process()

            self.logger.info(f"🔄 Starting Chrome on {host}:{port} using profile {chrome_profile_path}/{chrome_profile_name}...")

            self.chrome_process = subprocess.Popen([
                chrome_path,
                f"--remote-debugging-port={port}",
                f"--user-data-dir={chrome_profile_path}",
                f"--profile-directory={chrome_profile_name}",  # This sets the actual profile
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-background-mode",
                "--disable-extensions",
                "--disable-sync",
                "--disable-default-apps",
                "--disable-popup-blocking",
                "--disable-gpu",
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            time.sleep(3)  # Wait for Chrome to start

        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.connect_over_cdp(cdp_url)
            self.context = self.browser.contexts[0] if self.browser.contexts else await self.browser.new_context()
            self.page = await self.context.new_page()
            self.logger.info("✅ Chrome Started and Connected via CDP")
            return self.page

        except Exception as e:
            self.logger.critical(f"❌ Failed to start or connect to Chrome via CDP: {e}")
            if self.playwright:
                await self.playwright.stop()
            raise e


    def is_chrome_running(self):
        """
        Checks if Chrome is already running with CDP enabled.
        """
        cdp_url = os.getenv('CDP_URL', 'http://127.0.0.1:9222')
        host, port = cdp_url.replace("http://", "").split(":")
        port = int(port)

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0  # If port is open, Chrome is running
        except Exception:
            return False
        

    def kill_chrome_process(self):
        """
        Kills any existing Chrome processes before launching a new one.
        """
        subprocess.run(["pkill", "-f", "Google Chrome"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


    async def cleanup_context(self):
        """
        Closes extra Playwright pages to free up memory.
        """
        if len(await self.context.pages()) > 5:
            self.logger.info("🧹 Closing extra pages to free up memory...")
            for page in (await self.context.pages())[1:]:
                await page.close()


    async def close_browser(self):
        """
        Closes the Playwright browser session and kills Chrome if needed.
        """
        if self.browser:
            await self.browser.close()
            self.logger.info("✅ Successfully closed the browser")

        if self.chrome_process:
            self.logger.info("🛑 Stopping Chrome process...")
            self.chrome_process.terminate()


class PageHandler:
    def __init__(self, page, logger: logging.Logger):
        self.page = page
        self.logger = logger


    async def go_to_url(self, url, wait_min=3, wait_max=7):
        self.logger.info(f"Goto URL: {url}")
        await self.page.goto(url, wait_until="domcontentloaded")
        await self.random_wait(wait_min, wait_max)


    async def random_wait(self, wait_min=5, wait_max=12):
        wait_time = math.floor(random.random() * (wait_max - wait_min + 1)) + wait_min
        await asyncio.sleep(wait_time)

    
    async def get_element_text(self, target):
        try:
            text_content = ''

            if isinstance(target, str):
                text_content = await self.page.locator(target).text_content()
            
            text_content = await target.text_content()
            return text_content.strip()
        except Exception as error:
            self.logger.warning(f"Error finding element with selector {target}: {error}")
            return None
    

    async def get_element_property(self, target, property):
        try:
            if isinstance(target, str):
                locator = self.page.locator(target)
                return await locator.get_attribute(property)
            
            return await target.get_attribute(property)
        except Exception as e:
            self.logger.warning(f"get_element_property() Error occurred while getting element property: {e}")
            return None


    async def click_and_wait(self, target, name, wait_min=2, wait_max=4):
        """Clicks target and waits before continuing"""
        try:
            if isinstance(target, str):
                await self.page.locator(target).click()
            else:
                await target.click()
            
            self.logger.debug(f"Clicked Button {name}")
            await self.random_wait(wait_min, wait_max)
        except Exception as e:
            self.logger.warning(f'click_and_wait() Error occurred clicking element: {e}')


    async def fill_element(self, target, value, name, wait_min=2, wait_max=4):
        try:
            """Fills target with text value"""
            if isinstance(target, str):
                locator = self.page.locator(target)
                await locator.fill(value)
            else:
                await target.fill(value)
            
            self.logger.debug(f"Filled Element: {name}")
            await self.random_wait(wait_min, wait_max)
        except Exception as e:
            self.logger.warning(f"fill_element() Error trying to fill element {name}: {e}")


    async def get_elements(self, selector):
        try:
            return await self.page.locator(selector).all()
        except Exception as e:
            self.logger.warning(f'get_elements() Error getting elements: {e}')
            return None
    
    
    async def scroll_element_into_view(self, target, name, wait_min=2, wait_max=4):
        """Scrolls the target element into view"""
        try:
            # Convert Playwright Locator to an ElementHandle if necessary
            if isinstance(target, str):
                element_handle = await self.page.locator(target).element_handle()
            elif hasattr(target, "element_handle"):
                element_handle = await target.element_handle()
            else:
                element_handle = target  

            if element_handle:
                await self.page.evaluate("""
                async (element) => {
                    element.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
                    await new Promise(resolve => setTimeout(resolve, 1500));
                }
                """, element_handle)
                self.logger.debug(f"Scrolled Into View: {name}")
            else:
                self.logger.warning(f"Failed to scroll to element {name}: Element not found.")

            await self.random_wait(wait_min, wait_max)
        except Exception as e:
            self.logger.warning(f'Error occurred scrolling element into view: {e}')


class DatabaseManager:
    def __init__(self, logger: logging.Logger):
        self.logger = logger


    def create_database(self):
        try:
            with sqlite3.connect(os.getenv('DATABASE_PATH')) as conn:
                cursor = conn.cursor()
                # Table that holds potential jobs that are available
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS jobs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        jobid TEXT,
                        title TEXT,
                        company TEXT,
                        location TEXT,
                        remote_status TEXT,
                        linkedin_url TEXT
                    )
                ''')
                conn.commit()
        except sqlite3.Error as e:
            self.logger.critical(f"Error creating jobs table: {e}")
            raise e
        
        try:
            with sqlite3.connect(os.getenv('DATABASE_PATH')) as conn:
                cursor = conn.cursor()
                # Table that holds employers for a career within a state
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS employers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        company TEXT,
                        state TEXT
                    )
                ''')
                conn.commit()
        except sqlite3.Error as e:
            self.logger.critical(f"Error creating employers table: {e}")
            raise e
    

    def add_job(self, jobid, title, company, location, remote_status, linkedin_url):
        try:
            with sqlite3.connect(os.getenv('DATABASE_PATH')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT INTO jobs (jobid, title, company, location, remote_status, linkedin_url)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (jobid, title, company, location, remote_status, linkedin_url))
                conn.commit()

            self.logger.info(f'Job Added To DB: {company} - {title} - {location}')
        except sqlite3.Error as e:
            self.logger.critical(f'add_job() error when adding new job to db: {e}')
            raise e
        
    
    def add_employer(self, company, state):
        try:
            with sqlite3.connect(os.getenv('DATABASE_PATH')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT INTO employers (company, state)
                VALUES (?, ?)
            ''', (company, state))
                conn.commit()

            self.logger.info(f'Employer Added To DB: {company} - {state}')
        except sqlite3.Error as e:
            self.logger.critical(f'add_employer() error when adding new employer to db: {e}')
            raise e


    def search_jobs(self, search_term):
        try:
            with sqlite3.connect(os.getenv('DATABASE_PATH')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM jobs
                    WHERE title LIKE ? OR company LIKE ? OR location LIKE ? OR remote_status LIKE ?
                ''', ('%' + search_term + '%', '%' + search_term + '%', '%' + search_term + '%', '%' + search_term + '%'))
                jobs = cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.critical(f'search_jobs() error when searching jobs in db: {e}')
            raise e
           
        if not jobs:
            self.logger.info("No matching jobs found")
        else:
            for job in jobs:
                self.logger.info(job)


    def is_a_new_job(self, jobid):
        try:
            with sqlite3.connect(os.getenv('DATABASE_PATH')) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT jobid FROM jobs WHERE jobid = ?', (jobid,))
                job = cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.critical(f"Error verifying if it's a new job in DB: {e}")
            raise e

        return not job
    

    def is_a_new_employer(self, company):
        try:
            with sqlite3.connect(os.getenv('DATABASE_PATH')) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT company FROM employers WHERE company = ?', (company,))
                company = cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.critical(f"Error verifying if it's a new employer in DB: {e}")
            raise e
        
        return not company
    

class Scraper:
    def __init__(self):
        self.logger = self.setup_logging(os.getenv('LOGGING_PATH'))
        self.browser_manager = BrowserManager(self.logger)
        self.database_manager = DatabaseManager(self.logger)
        self.page_handler = None
        self.terms_block_list = os.getenv('TERMS_BLOCKLIST').split(',')

    
    async def run(self):
        # Makes sure the db is always created before running
        self.database_manager.create_database()
        self.page = await self.browser_manager.start_chrome_with_cdp()
        self.page_handler = PageHandler(self.page, self.logger)

        self.logger.info('Scraper Initiated & Running')

        try:
            pagination_page = 1
            
            await self.page_handler.go_to_url(f"{os.getenv('JOB_SEARCH_BASE_URL')}", 3, 5)
            await self.page_handler.fill_element(
                LOCATORS['job_keyword_search'], os.getenv('JOB_SEARCH_KEYWORDS'), "Keyword Input", 2, 4)
            
            location_inputs = await self.page_handler.get_elements(LOCATORS['job_location_search'])
            await self.page_handler.fill_element(
                location_inputs[0], os.getenv('JOB_SEARCH_LOCATION'), "Location Input", 2, 4)

            await self.page_handler.click_and_wait(LOCATORS['search_button'], "Search Button")
            
            self.logger.debug('Start Iterating Jobs')

            while True:
                await self.page_handler.scroll_element_into_view(LOCATORS['pagination_list'], 'Pagination List')

                job_cards = await self.page_handler.get_elements(LOCATORS['job_cards'])

                for i in range(len(job_cards)):
                    card = job_cards[i]
                    card_name = f"Card: {i + 1}"

                    self.logger.debug(f"Inspecting Job {card_name}")

                    jobid = await self.page_handler.get_element_property(card, 'data-job-id')
                    is_new_job = self.database_manager.is_a_new_job(jobid)

                    if not is_new_job:
                        self.logger.info('Repeat Job Found, Skip')
                        continue

                    element_handle = await card.element_handle()
                    await self.page_handler.scroll_element_into_view(element_handle, card_name)
                    await self.page_handler.click_and_wait(card, card_name, 2, 4)
                    
                    company_locator = card.locator(LOCATORS['company'])
                    company = await self.page_handler.get_element_text(company_locator)
                    self.logger.debug(f'Got Company Name: {company}')

                    is_new_company = self.database_manager.is_a_new_employer(company)
                    if is_new_company:
                        self.database_manager.add_employer(company, os.getenv('STATE'))

                    title_locator = card.locator(LOCATORS['job_title'])
                    job_title = await self.page_handler.get_element_text(title_locator)
                    self.logger.debug(f'Got Job Title: {job_title}')

                    if self.contains_blocked_term(job_title):
                        self.logger.debug('Blocked Term Found, Skip')
                        continue
                    
                    has_remote_status = False
                    job_location_locator = card.locator(LOCATORS['job_location'])
                    job_location_string = await self.page_handler.get_element_text(job_location_locator)
                    job_location = ''
                    job_remote_status = ''

                    if ' (' in job_location_string:
                        job_location_string = job_location_string.split(' (')
                        has_remote_status = True

                    if has_remote_status:
                        job_location = job_location_string[0]
                        job_remote_status = job_location_string[1].replace(')', '')
                    else:
                        job_location = job_location_string

                    self.logger.debug(f'Got Job Location: {job_location}')

                    linkedin_url = f"{os.getenv('JOBS_PAGE_BASE_URL')}{jobid}"
                    self.logger.debug(f'Got LinkedIn URL: {linkedin_url}')

                    self.database_manager.add_job(jobid, job_title, company, job_location, job_remote_status, linkedin_url)

                pagination_page += 1
                self.logger.debug(f'Looking for pagination btn {pagination_page}')

                try:
                    next_pagination_btn_locator = self.page.locator(LOCATORS['pagination_button'](pagination_page), timeout=6000)
                    if next_pagination_btn_locator:
                        await self.page_handler.click_and_wait(next_pagination_btn_locator, f"Pagination Btn {pagination_page}")
                except Exception as e:
                    self.logger.info(f"Couln't fine next pagination btn, need to click for more")
                    selector = LOCATORS['more_pagination_buttons'](pagination_page)
                    self.logger.debug(selector)

                    more_pagination_btn_locator = self.page.locator(selector)
                    await self.page_handler.click_and_wait(more_pagination_btn_locator, 'Show More Pagination Btn')
                
                if pagination_page % 5 == 0:
                    os.system('clear')
                # await self.browser_manager.cleanup_context()
        except Exception as e:
            self.logger.critical('Error occurred {e}')
        finally:
            await self.browser_manager.close_browser()
            await self.browser_manager.playwright.stop()

        
    def setup_logging(self, log_file):
        """Sets up logging to both console and file"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)

        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)

        # Create console formatter and add it to handler
        formatter_c = logging.Formatter('%(levelname)s - %(message)s')
        console_handler.setFormatter(formatter_c)
        logger.addHandler(console_handler)

        try:
            # Create file handler
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
        except Exception as e:
            logger.warning(f'Error creating logger file handler: {e}')
            return logger

        # Create file formatter and add it to handler
        formatter_f = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s\n')
        file_handler.setFormatter(formatter_f)        
        logger.addHandler(file_handler)
        
        return logger


    def contains_blocked_term(self, job_title):
        """Sets up list of terms for jobs I want to ignore"""
        return any(sub in job_title for sub in self.terms_block_list)



scraper = Scraper()
asyncio.run(scraper.run())



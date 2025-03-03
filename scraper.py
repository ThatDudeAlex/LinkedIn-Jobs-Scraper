import sqlite3
from playwright.async_api import async_playwright, Playwright
from locators import LOCATORS
from dotenv import load_dotenv
import math
import asyncio
import os
import random
# import logging

load_dotenv()


class BrowserManager:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None

    async def connect_to_existing_chrome(self, cdp_url):
        # To open chrome with remote port, run this command on the terminal:
        # /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
        # https://stackoverflow.com/questions/71362982/is-there-a-way-to-connect-to-my-existing-browser-session-using-playwright
        # with async_playwright() as p:
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.connect_over_cdp(cdp_url)
        self.context = self.browser.contexts[0]
        
        if len(self.context.pages) > 0:
            self.page = self.context.pages[0]  # Reuse existing page
        else:
            self.page = await self.context.new_page()

        print("\nBrowser Connected!")
        return self.page
    
    async def cleanup_context(self):
        if len(await self.context.pages()) > 5:  # If more than 5 pages are open
            print("Closing extra pages to free up memory...")
        for page in (await self.context.pages())[1:]:  # Keep only the first page open
            await page.close()  # Close all other pages


    async def close_browser(self):
        if self.browser is not None:
            await self.browser.close()
            print('Succesfully Terminated!')
  

class PageHandler:
    def __init__(self, page):
        self.page = page

    async def go_to_url(self, url, wait_min=3, wait_max=7):
        print(f"Goto URL: {url}")
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
            print(f"Error finding element with selector {target}: {error}")
            return None
    

    async def get_element_property(self, target, attribute):
        if isinstance(target, str):
            locator = self.page.locator(target)
            return await locator.get_attribute(attribute)
        
        return await target.get_attribute(attribute)


    async def click_and_wait(self, target, name="n/a", wait_min=2, wait_max=4):
        if isinstance(target, str):
            await self.page.locator(target).click()
        else:
            await target.click()
        
        print(f"Clicked Button: {name}")
        await self.random_wait(wait_min, wait_max)

    async def fill_element(self, target, value, name="n/a", wait_min=2, wait_max=4):
        """Fills target with text value"""
        if isinstance(target, str):
            locator = self.page.locator(target)
            await locator.fill(value)
        else:
            await target.fill(value)
        
        print(f"Filled Element: {name}")
        await self.random_wait(wait_min, wait_max)

    async def get_elements(self, selector):
        return await self.page.locator(selector).all()
    
    # async def scroll_element_into_view(self, target, name="n/a", wait_min=3, wait_max=6):
    #     """Scrolls the target element into view"""
    #     await self.page.evaluate("""
    #     async (target) => {
    #         let element = document.querySelector(target);
    #         if (element) {
    #             element.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    #             await new Promise(resolve => setTimeout(resolve, 1500));
    #         }

    #     }
    # """, arg=target)
    #     print(f"Scrolled Into View: {name}")
    #     await self.random_wait(wait_min, wait_max)
    async def scroll_element_into_view(self, target, name="n/a", wait_min=2, wait_max=4):
        """Scrolls the target element into view"""
        
        # Convert Playwright Locator to an ElementHandle if necessary
        if isinstance(target, str):  # If it's a selector (string)
            element_handle = await self.page.locator(target).element_handle()
        elif hasattr(target, "element_handle"):  # If it's a Playwright Locator
            element_handle = await target.element_handle()
        else:  # If it's already an ElementHandle, use it directly
            element_handle = target  

        if element_handle:
            await self.page.evaluate("""
            async (element) => {
                element.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
                await new Promise(resolve => setTimeout(resolve, 1500));
            }
            """, element_handle)
            print(f"Scrolled Into View: {name}")
        else:
            print(f"Failed to scroll {name}: Element not found.")

        await self.random_wait(wait_min, wait_max)


class DatabaseManager:
    def create_database(self):
        conn = sqlite3.connect(os.getenv('DATABASE_PATH'))
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
        
        # Table that holds employers for a career within a state
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS employers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT,
                state TEXT
            )
        ''')

        conn.commit()
        conn.close()
    

    def add_job(self, jobid, title, company, location, remote_status, linkedin_url):
        conn = sqlite3.connect(os.getenv('DATABASE_PATH'))
        cursor = conn.cursor()

        cursor.execute('''
        INSERT INTO jobs (jobid, title, company, location, remote_status, linkedin_url)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (jobid, title, company, location, remote_status, linkedin_url))

        conn.commit()
        conn.close()
        print('  - Job Added To DB\n\n')
    
    
    def add_employer(self, company, state):
        conn = sqlite3.connect(os.getenv('DATABASE_PATH'))
        cursor = conn.cursor()

        cursor.execute('''
        INSERT INTO employers (company, state)
        VALUES (?, ?)
    ''', (company, state))

        conn.commit()
        conn.close()
        print('  - Employer Added To DB')


    def search_jobs(self, search_term):
        conn = sqlite3.connect(os.getenv('DATABASE_PATH'))
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM jobs
            WHERE title LIKE ? OR company LIKE ? OR location LIKE ? OR remote_status LIKE ?
        ''', ('%' + search_term + '%', '%' + search_term + '%', '%' + search_term + '%', '%' + search_term + '%'))

        jobs = cursor.fetchall()

        if not jobs:
            print("No matching jobs found")
        else:
            for job in jobs:
                print(job)

        conn.close()

    def is_a_new_job(self, jobid):
        conn = sqlite3.connect(os.getenv('DATABASE_PATH'))
        cursor = conn.cursor()

        cursor.execute('SELECT jobid FROM jobs WHERE jobid = ?', (jobid,))

        job = cursor.fetchall()

        if not job:
            return True
        return False
    
    def is_a_new_employer(self, company):
        conn = sqlite3.connect(os.getenv('DATABASE_PATH'))
        cursor = conn.cursor()

        cursor.execute('SELECT company FROM employers WHERE company = ?', (company,))

        company = cursor.fetchall()

        if not company:
            return True
        return False

class Scraper:
    def __init__(self):
        self.browser_manager = BrowserManager()
        self.database_manager = DatabaseManager()
        self.page_handler = None
        self.terms_block_list = os.getenv('TERMS_BLOCKLIST').split(',')

    
    async def run(self):
        # Makes sure the db is always created before running
        self.database_manager.create_database()
        self.page = await self.browser_manager.connect_to_existing_chrome(os.getenv('CDP_URL'))
        self.page_handler = PageHandler(self.page)

        print('\nScraper Initiated & Running\n')

        try:


            await self.page_handler.go_to_url(f"{os.getenv('JOB_SEARCH_BASE_URL')}", 3, 5)
            print()

            await self.page_handler.fill_element(
                LOCATORS['job_keyword_search'], os.getenv('JOB_SEARCH_KEYWORDS'), "Keyword Input", 2, 4)
            print()
            
            location_inputs = await self.page_handler.get_elements(LOCATORS['job_location_search'])

            await self.page_handler.fill_element(
                location_inputs[0], os.getenv('JOB_SEARCH_LOCATION'), "Location Input", 2, 4)
            print()

            await self.page_handler.click_and_wait(LOCATORS['search_button'], "Search Button")
            pagination_page = 1
            print('\n---------- Start Iterating ----------n')

            while True:
                await self.page_handler.scroll_element_into_view(LOCATORS['pagination_list'], 'Pagination List')

                job_cards = await self.page_handler.get_elements(LOCATORS['job_cards'])

                for i in range(len(job_cards)):
                    card = job_cards[i]
                    card_name = f"Card: {i + 1}"

                    print(f"Inspecting Job {card_name}")

                    jobid = await self.page_handler.get_element_property(card, 'data-job-id')

                    is_new_job = self.database_manager.is_a_new_job(jobid)

                    if not is_new_job:
                        print('  * Repeat Job Found, Skip!\n\n')
                        continue

                    element_handle = await card.element_handle()
                    await self.page_handler.scroll_element_into_view(element_handle, card_name)
                    await self.page_handler.click_and_wait(card, card_name, 2, 4)
                    
                    company_locator = card.locator(LOCATORS['company'])
                    company = await self.page_handler.get_element_text(company_locator)
                    print(f'  - Got Company Name: {company}')

                    is_new_company = self.database_manager.is_a_new_employer(company)
                    if is_new_company:
                        self.database_manager.add_employer(company, os.getenv('STATE'))

                    title_locator = card.locator(LOCATORS['job_title'])
                    job_title = await self.page_handler.get_element_text(title_locator)
                    print(f'  - Got Job Title: {job_title}')

                    if self.contains_blocked_term(job_title):
                        print('  * Blocked Term Found, Skip!\n\n')
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

                    print(f'  - Got Job Location: {job_location}')

                    linkedin_url = f"{os.getenv('JOBS_PAGE_BASE_URL')}{jobid}"
                    print(f'  - Got LinkedIn URL: {linkedin_url}')

                    self.database_manager.add_job(jobid, job_title, company, job_location, job_remote_status, linkedin_url)

                pagination_page += 1
                print(f'Looking for pagination btn {pagination_page}')

                try:
                    next_pagination_btn_locator = self.page.locator(LOCATORS['pagination_button'](pagination_page))
                    await self.page_handler.click_and_wait(next_pagination_btn_locator, f"Pagination Btn {pagination_page}")
                except Exception as error:
                    print('Timeout Error looking for pagination btn, checking for More')
                    
                    more_pagination_btn_locator = self.page.locator(LOCATORS['more_pagination_buttons'](pagination_page))
                    if more_pagination_btn_locator:
                        await self.page_handler.click_and_wait(more_pagination_btn_locator, 'Show More Pagination Btn')
                    else:
                        break

            await self.browser_manager.cleanup_context()
        finally:
            await self.browser_manager.close_browser()
            await self.browser_manager.playwright.stop()
            

    def contains_blocked_term(self, job_title):
        # Checks if any substring is in the job_title
        return any(sub in job_title for sub in self.terms_block_list)




scraper = Scraper()
asyncio.run(scraper.run())



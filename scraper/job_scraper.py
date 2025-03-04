import os
import logging
import argparse
from typing import List
from .browser_manager import BrowserManager
from .database_manager import DatabaseManager
from .page_handler import PageHandler
from locators import LOCATORS 


class JobScraper:
    browser_manager: BrowserManager
    database_manager: DatabaseManager
    page_handler: PageHandler
    logger: logging.Logger
    job_search: str
    location: str
    terms_block_list: List[str]

    def __init__(self, args: argparse.Namespace, logger: logging.Logger):
        self.browser_manager = BrowserManager(logger)
        self.database_manager = DatabaseManager(logger)
        self.page_handler = None
        self.logger = logger
        self.job_search = args.job_search
        self.location = args.location
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

            await self.page_handler.fill_element(LOCATORS['job_keyword_search'], self.job_search, "Keyword Input", 2, 4)
            
            location_inputs = await self.page_handler.get_elements(LOCATORS['job_location_search'])
            await self.page_handler.fill_element(location_inputs[0], self.location, "Location Input", 2, 4)

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
                await self.page_handler.scroll_element_into_view(LOCATORS['pagination_list'], 'Pagination List')
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

        
    def contains_blocked_term(self, job_title: str) -> bool:
        """Sets up list of terms for jobs I want to ignore"""
        return any(sub in job_title for sub in self.terms_block_list)

import logging
import math
import random
import asyncio
from typing import Union, List
from playwright.async_api import Page, Locator

class PageHandler:
    page: Page
    logger: logging.Logger

    def __init__(self, page: Page, logger: logging.Logger):
        self.page = page
        self.logger = logger


    async def go_to_url(self, url: str, wait_min: int = 3, wait_max: int = 7) -> None:
        self.logger.info(f"Goto URL: {url}")
        await self.page.goto(url, wait_until="domcontentloaded")
        await self.random_wait(wait_min, wait_max)


    async def random_wait(self, wait_min: int = 5, wait_max: int = 12) -> None:
        wait_time = math.floor(random.random() * (wait_max - wait_min + 1)) + wait_min
        await asyncio.sleep(wait_time)

    
    async def get_element_text(self, target: Union[str, Locator]) -> Union[str, None]:
        try:
            text_content = ''

            if isinstance(target, str):
                text_content = await self.page.locator(target).text_content()
            
            text_content = await target.text_content()
            return text_content.strip()
        except Exception as error:
            self.logger.warning(f"Error finding element with selector {target}: {error}")
            return None
    

    async def get_element_property(self, target: Union[str, Locator],
                                   property: str) -> Union[str, None]:
        try:
            if isinstance(target, str):
                locator = self.page.locator(target)
                return await locator.get_attribute(property)
            
            return await target.get_attribute(property)
        except Exception as e:
            self.logger.warning(f"get_element_property() Error occurred while getting element property: {e}")
            return None


    async def click_and_wait(self, target: Union[str, Locator], name: str,
                             wait_min: int = 2, wait_max: int = 4) -> None:
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


    async def fill_element(self, target: Union[str, Locator], value, name,
                           wait_min: int = 2, wait_max: int = 4) -> None:
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


    async def get_elements(self, selector: str) -> Union[List[Locator], None]:
        try:
            return await self.page.locator(selector).all()
        except Exception as e:
            self.logger.warning(f'get_elements() Error getting elements: {e}')
            return None
    
    
    async def scroll_element_into_view(self, target: Union[str, Locator], name,
                                       wait_min: int = 2, wait_max: int = 4) -> None:
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

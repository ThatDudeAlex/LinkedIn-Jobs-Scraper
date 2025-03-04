import logging
import socket
import sys
import os
import subprocess
import time
from playwright.async_api import async_playwright, Page, Browser, BrowserContext, Playwright


class BrowserManager:
    """Handles browser connections and closing"""

    logger: logging.Logger
    browser: Browser
    context: BrowserContext
    page: Page
    chrome_process: subprocess.Popen
    playwright: Playwright

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.browser = None
        self.context = None
        self.page = None
        self.chrome_process = None
        self.playwright = None

    
    def get_chrome_profile_path(self) -> str:
        if sys.platform == "darwin":  # macOS
            default_path = os.path.expanduser("~/Library/Application Support/Google/Chrome")
        elif sys.platform == "win32":  # Windows
            default_path = os.path.join(os.getenv("LOCALAPPDATA"), "Google", "Chrome", "User Data")
        elif sys.platform == "linux":  # Linux (Chromium or Chrome)
            default_path = os.path.expanduser("~/.config/google-chrome")
        else:
            raise RuntimeError("Unsupported operating system")

        return os.getenv("CHROME_PROFILE_PATH", default_path)
    

    def get_chrome_executable_path(self) -> str:
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


    async def connect_to_existing_chrome(self, cdp_url: str) -> Page:
        """
        Connects to an existing Chrome session via CDP
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


    async def start_chrome_with_cdp(self) -> Page:
        """
        Starts a new Chrome process with a specific user profile and connects Playwright to it
        """
        cdp_url = os.getenv('CDP_URL', 'http://127.0.0.1:9222')
        host, port = cdp_url.replace("http://", "").split(":")
        port = int(port)
        self.logger.debug(f"CDP URL: {cdp_url}")
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


    def is_chrome_running(self) -> bool:
        """
        Checks if Chrome is already running with CDP enabled
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
        

    def kill_chrome_process(self) -> None:
        """
        Kills any existing Chrome processes before launching a new one
        """
        subprocess.run(["pkill", "-f", "Google Chrome"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


    async def cleanup_context(self) -> None:
        """
        Closes extra Playwright pages to free up memory
        """
        if len(await self.context.pages()) > 5:
            self.logger.info("🧹 Closing extra pages to free up memory...")
            for page in (await self.context.pages())[1:]:
                await page.close()


    async def close_browser(self) -> None:
        """
        Closes the Playwright browser session and kills Chrome if needed
        """
        if self.browser:
            await self.browser.close()
            self.logger.info("✅ Successfully closed the browser")

        if self.chrome_process:
            self.logger.info("🛑 Stopping Chrome process...")
            self.chrome_process.terminate()

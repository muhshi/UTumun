import asyncio
import os
from playwright.async_api import async_playwright

SESSION_FILE = ".auth/session.json"
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

async def download_rambu():
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=CHROME_PATH, headless=True)
        context = await browser.new_context(storage_state=SESSION_FILE, accept_downloads=True)
        page = await context.new_page()

        print("Triggering download for Rambu Penilaian Diskusi 2...")
        try:
            async with page.expect_download() as download_info:
                # Trigger goto
                await page.goto("https://elearning.ut.ac.id/mod/resource/view.php?id=47303005")
            download = await download_info.value
            filename = download.suggested_filename
            print(f"Suggested filename: {filename}")
            save_path = os.path.join("data", filename)
            await download.save_as(save_path)
            print(f"Saved download to {save_path}")
        except Exception as e:
            print(f"Error during download: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(download_rambu())

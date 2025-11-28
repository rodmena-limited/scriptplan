#!/usr/bin/env python3
"""Screenshot tool using Selenium with Chrome - supports complex URLs"""

import argparse
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def take_screenshot(
    url: str,
    delay: int = 2,
    output_dir: str = "screenshots",
    click_selector: str | None = None,
    scroll_y: int | None = None,
    debug: bool = False,
    type_text: str | None = None,
    execute_js: str | None = None,
) -> str:
    """Take screenshot of URL with delay and save with epoch timestamp

    Args:
        url: URL to screenshot (can include fragments, query params, etc.)
        delay: Seconds to wait before taking screenshot
        output_dir: Directory to save screenshots
        click_selector: Optional CSS selector to click before screenshot
        scroll_y: Optional Y position to scroll to before screenshot
        debug: If True, dump DOM analysis to stderr
        type_text: Optional "selector:text" to type into an element
        execute_js: Optional JavaScript code to execute before taking screenshot

    Returns:
        Path to saved screenshot file
    """
    # Create output directory if it doesn't exist
    screenshots_path = Path(output_dir)
    screenshots_path.mkdir(exist_ok=True)

    # Generate filename with unix epoch timestamp
    epoch_timestamp = int(time.time())
    output_file = screenshots_path / f"{epoch_timestamp}.png"

    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1440,900")
    chrome_options.add_argument("--disable-gpu")

    # Enable console logging
    chrome_options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

    # Initialize driver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        print(f"Loading URL: {url}", file=sys.stderr)
        driver.get(url)

        print(f"Waiting {delay} seconds...", file=sys.stderr)
        time.sleep(delay)

        # Click element if selector provided
        if click_selector:
            try:
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support import expected_conditions as EC
                from selenium.webdriver.support.ui import WebDriverWait

                print(f"Clicking element: {click_selector}", file=sys.stderr)
                element = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, click_selector)),
                )
                element.click()
                time.sleep(1)  # Wait for modal animation
            except Exception as e:
                print(f"Failed to click element: {e}", file=sys.stderr)

        # Type text if provided
        if type_text:
            try:
                from selenium.webdriver.common.by import By
                from selenium.webdriver.common.keys import Keys
                from selenium.webdriver.support import expected_conditions as EC
                from selenium.webdriver.support.ui import WebDriverWait

                # Parse "selector:text" format
                if ":" not in type_text:
                    print(
                        f"Invalid type_text format (expected 'selector:text'): {type_text}",
                        file=sys.stderr,
                    )
                else:
                    selector, text = type_text.split(":", 1)
                    print(f"Typing '{text}' into element: {selector}", file=sys.stderr)
                    element = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector)),
                    )
                    element.clear()
                    element.send_keys(text)
                    # Press Enter to submit
                    element.send_keys(Keys.RETURN)
                    time.sleep(1)  # Wait for action to complete
            except Exception as e:
                print(f"Failed to type text: {e}", file=sys.stderr)

        # Execute JavaScript if provided
        if execute_js:
            try:
                print(f"Executing JavaScript: {execute_js[:50]}...", file=sys.stderr)
                driver.execute_script(execute_js)
                time.sleep(1)  # Wait for JS to take effect
            except Exception as e:
                print(f"Failed to execute JavaScript: {e}", file=sys.stderr)

        # Scroll if Y position provided
        if scroll_y is not None:
            try:
                print(f"Scrolling to Y position: {scroll_y}", file=sys.stderr)
                # Try scrolling the analytics content container first (for modals)
                driver.execute_script(
                    f"""
                    const analyticsContent = document.querySelector('.analytics-content');
                    if (analyticsContent) {{
                        analyticsContent.scrollTop = {scroll_y};
                    }} else {{
                        window.scrollTo(0, {scroll_y});
                    }}
                """,
                )
                time.sleep(0.5)  # Wait for scroll to complete
            except Exception as e:
                print(f"Failed to scroll: {e}", file=sys.stderr)

        # Debug DOM if requested
        if debug:
            print("\n=== DOM Analysis ===", file=sys.stderr)
            try:
                dom_info = driver.execute_script(
                    """
                    const detailsContent = document.getElementById("details-content");
                    if (!detailsContent) return {error: "details-content not found"};
                    const html = detailsContent.innerHTML;
                    return {
                        hasQuickActions: html.includes('QUICK ACTIONS'),
                        hasExport: html.includes('EXPORT & DOWNLOAD'),
                        hasExecution: html.includes('EXECUTION'),
                        hasLifecycle: html.includes('LIFECYCLE'),
                        hasInputsOutputs: html.includes('INPUTS / OUTPUTS'),
                        hasIdentity: html.includes('IDENTITY'),
                        hasSignals: html.includes('SIGNALS'),
                        htmlLength: html.length,
                        firstChars: html.substring(0, 200),
                        lastChars: html.substring(html.length - 200)
                    };
                """,
                )
                print(f"DOM Info: {dom_info}", file=sys.stderr)
            except Exception as e:
                print(f"Failed to analyze DOM: {e}", file=sys.stderr)
            print("=== End DOM Analysis ===\n", file=sys.stderr)

        print(f"Taking screenshot: {output_file}", file=sys.stderr)
        driver.save_screenshot(str(output_file))

        # Capture console logs
        print("\n=== Browser Console Logs ===", file=sys.stderr)
        for entry in driver.get_log("browser"):  # type: ignore[no-untyped-call]
            print(f"[{entry['level']}] {entry['message']}", file=sys.stderr)
        print("=== End Console Logs ===\n", file=sys.stderr)

        # Only output the path to stdout for easy piping
        print(str(output_file))
        return str(output_file)

    finally:
        driver.quit()


def main() -> None:
    """Command-line interface"""
    parser = argparse.ArgumentParser(description="Take screenshots of URLs using headless Chrome")
    parser.add_argument("url", help="URL to screenshot (supports fragments, query params, etc.)")
    parser.add_argument(
        "-d",
        "--delay",
        type=int,
        default=2,
        help="Delay in seconds before taking screenshot (default: 2)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default="screenshots",
        help="Output directory for screenshots (default: screenshots/)",
    )
    parser.add_argument(
        "-c",
        "--click",
        dest="click_selector",
        help="CSS selector to click before taking screenshot",
    )
    parser.add_argument(
        "-t",
        "--type",
        dest="type_text",
        help='Text to type into element (format: "selector:text")',
    )
    parser.add_argument(
        "-s",
        "--scroll",
        dest="scroll_y",
        type=int,
        help="Y position to scroll to before taking screenshot",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Dump DOM analysis to stderr",
    )
    parser.add_argument(
        "-j",
        "--js",
        dest="execute_js",
        help="JavaScript code to execute before taking screenshot",
    )

    args = parser.parse_args()
    take_screenshot(
        args.url,
        args.delay,
        args.output_dir,
        args.click_selector,
        args.scroll_y,
        args.debug,
        args.type_text,
        args.execute_js,
    )


if __name__ == "__main__":
    main()

import argparse
import time
from pathlib import Path
from pprint import pprint
from urllib.parse import urlencode

import pandas as pd
import yaml
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

DEFAULT_CONFIG_PATH = Path(__file__).parent / "104_config.yaml"


def load_config(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_search_url(page: int, search_config: dict) -> str:
    params = {
        "keyword": search_config.get("keyword", ""),
        "page": page,
    }

    optional_fields = ["area", "jobcat", "jobexp", "edu", "isnew", "order", "ro"]

    for field in optional_fields:
        value = search_config.get(field)
        if value not in (None, "", []):
            params[field] = value

    return "https://www.104.com.tw/jobs/search/?" + urlencode(params)


def create_driver(config: dict) -> webdriver.Firefox:
    options = Options()
    if config.get("headless", True):
        options.add_argument("-headless")

    options.binary_location = config["firefox_binary"]

    service = Service(
        executable_path=config["geckodriver_path"],
        log_output="geckodriver.log",
    )

    driver = webdriver.Firefox(service=service, options=options)
    driver.set_window_size(
        config.get("window_width", 1400),
        config.get("window_height", 2200),
    )
    return driver


def crawl_104_links(config: dict) -> list[dict]:
    driver = create_driver(config)
    wait = WebDriverWait(driver, config.get("wait_timeout", 20))

    jobs = []

    try:
        for page in range(1, config.get("max_pages", 1) + 1):
            url = build_search_url(page=page, search_config=config["search"])
            print(f"抓取第 {page} 頁: {url}")

            driver.get(url)

            wait.until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, 'a[href*="/job/"]')
                )
            )

            time.sleep(config.get("sleep_sec", 2))

            links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/job/"]')
            print(f"第 {page} 頁找到 {len(links)} 個候選連結")

            seen_in_page = set()

            for a in links:
                try:
                    title = a.text.strip()
                    href = (a.get_attribute("href") or "").strip()

                    if not title:
                        continue
                    if "/job/" not in href:
                        continue
                    if href in seen_in_page:
                        continue

                    seen_in_page.add(href)

                    jobs.append(
                        {
                            "title": title,
                            "link": href,
                            "page": page,
                            "keyword": config["search"].get("keyword", ""),
                            "area": config["search"].get("area", ""),
                        }
                    )
                except Exception:
                    continue

    finally:
        driver.quit()

    dedup = {}
    for job in jobs:
        dedup[job["link"]] = job

    return list(dedup.values())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", default=DEFAULT_CONFIG_PATH, help="Path to YAML config file"
    )
    args = parser.parse_args()

    config = load_config(args.config)

    jobs = crawl_104_links(config)
    df = pd.DataFrame(jobs)
    pprint(df)
    df.to_csv(config["output_csv"], index=False, encoding="utf-8-sig")

    print(df.head())
    print(f"總共 {len(df)} 筆，已輸出到 {config['output_csv']}")


if __name__ == "__main__":
    main()

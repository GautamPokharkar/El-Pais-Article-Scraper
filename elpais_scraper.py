import os
import re
import time
import argparse
import json
import unicodedata
from collections import Counter
from urllib.parse import urlparse

import requests
from concurrent.futures import ThreadPoolExecutor

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options

from deep_translator import GoogleTranslator

# Configuration
BASE_URL = "https://elpais.com"
OPINION_URL = f"{BASE_URL}/opinion/"
OUTPUT_DIR = "output"
IMAGES_DIR = f"{OUTPUT_DIR}/images"
ARTICLES_FILE = f"{OUTPUT_DIR}/articles.json"
MAX_ARTICLES = 5
DEBUG = False  

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)


class ElPaisScraper:
    def __init__(self, remote=False, browser_config=None):
        self.remote = remote
        self.browser_config = browser_config or {}
        self.driver = None
        self.translator = GoogleTranslator(source='es', target='en')

    # ---------------- DRIVER SETUP ----------------
    def setup_driver(self):
        if self.remote:
            username = os.environ.get('BROWSERSTACK_USERNAME')
            access_key = os.environ.get('BROWSERSTACK_ACCESS_KEY')

            if not username or not access_key:
                raise ValueError("BrowserStack credentials not found")

            if self.browser_config.get("device"):
                desired_capabilities = {
                    'device': self.browser_config.get('device'),
                    'real_mobile': self.browser_config.get('real_mobile', 'true'),
                    'os_version': self.browser_config.get('os_version'),
                    'project': 'El Pais Scraper',
                    'build': 'Build 1.0',
                    'name': f"{self.browser_config.get('device')}"
                }
            else:
                desired_capabilities = {
                    'browserName': self.browser_config.get('browser', 'Chrome'),
                    'browser_version': self.browser_config.get('browser_version', 'latest'),
                    'os': self.browser_config.get('os', 'Windows'),
                    'os_version': self.browser_config.get('os_version', '10'),
                    'resolution': self.browser_config.get('resolution', '1920x1080'),
                    'project': 'El Pais Scraper',
                    'build': 'Build 1.0',
                    'name': f"{self.browser_config.get('browser')} - {self.browser_config.get('os')}"
                }

            url = f"https://{username}:{access_key}@hub-cloud.browserstack.com/wd/hub"
            options = webdriver.ChromeOptions()

            for key, value in desired_capabilities.items():
                options.set_capability(key, value)

            self.driver = webdriver.Remote(
                command_executor=url,
                options=options
            )

        else:
            chrome_options = Options()
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920,1080")

            self.driver = webdriver.Chrome(options=chrome_options)

        try:
            if not self.browser_config.get("device") and self.browser_config.get("browser") != "Safari":
                self.driver.maximize_window()
        except Exception:
            pass

    # ---------------- COOKIE HANDLING ----------------
    def handle_cookie_consent(self):
        try:
            accept_button = WebDriverWait(self.driver, 8).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Aceptar')]"))
            )
            accept_button.click()

            # Wait for page reload / DOM stabilization
            WebDriverWait(self.driver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            if DEBUG:
                print("🍪 Cookie accepted and page stabilized")

        except TimeoutException:
            pass

    # ---------------- LANGUAGE CHECK ----------------
    def verify_spanish_language(self):
        try:
            html_lang = self.driver.find_element(By.TAG_NAME, "html").get_attribute("lang")
            if html_lang and html_lang.lower().startswith("es"):
                return True
            return False
        except Exception:
            return False

    # ---------------- NAVIGATION ----------------
    def navigate_to_opinion(self):
        try:
            self.driver.get(OPINION_URL)

            # Handle cookie again (important for mobile Safari)
            self.handle_cookie_consent()

            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "article, main"))
            )
            return True
        except TimeoutException:
            return False

    # ---------------- SCRAPING ----------------
    def scrape_articles(self):
        articles = []
        visited_urls = set()

        try:
            article_elements = self.driver.find_elements(By.CSS_SELECTOR, "article")

            candidate_links = []

            for article_elem in article_elements:
                try:
                    links = article_elem.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        href = link.get_attribute("href")
                        if href and "/opinion/" in href and href not in visited_urls:
                            candidate_links.append(href)
                            visited_urls.add(href)
                            break
                except Exception:
                    pass

            for url in candidate_links:
                if len(articles) >= MAX_ARTICLES:
                    break

                try:
                    self.driver.get(url)

                    WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "h1, article, main"))
                    )

                    spanish_title = None

                    try:
                        headline_elem = self.driver.find_element(
                            By.CSS_SELECTOR,
                            "h1[data-dtm-region='articulo_titulo']"
                        )
                        spanish_title = headline_elem.text.strip()
                    except NoSuchElementException:
                        try:
                            headline_elem = self.driver.find_element(
                                By.CSS_SELECTOR,
                                "article h1"
                            )
                            spanish_title = headline_elem.text.strip()
                        except NoSuchElementException:
                            continue

                    if not spanish_title:
                        continue

                    if spanish_title.lower() == "opinión":
                        continue

                    content = ""
                    try:
                        content_selectors = [
                            "div.articulo-cuerpo",
                            "article .article_body",
                            "div[data-dtm-region='articulo_cuerpo']",
                            "article div.article-body"
                        ]

                        for selector in content_selectors:
                            try:
                                content_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                                content = content_elem.text.strip()
                                if content:
                                    break
                            except NoSuchElementException:
                                continue

                        if not content:
                            paragraphs = self.driver.find_elements(By.CSS_SELECTOR, "article p, main p")
                            content = "\n\n".join(p.text.strip() for p in paragraphs if p.text.strip())
                    except Exception:
                        content = "Content could not be extracted"

                    image_url = None
                    try:
                        image_selectors = [
                            ".articulo-multimedia img",
                            "article figure img",
                            "main img",
                            "img[data-dtm-region='articulo_imagen']",
                            "figure.article-image img"
                        ]

                        for selector in image_selectors:
                            try:
                                image_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                                image_url = image_elem.get_attribute("src")
                                if image_url and image_url.startswith("http"):
                                    break
                            except NoSuchElementException:
                                continue
                    except Exception:
                        pass

                    image_path = None
                    if image_url:
                        image_path = self.download_image(image_url, len(articles) + 1)

                    print(f"{len(articles)+1}. {spanish_title}")
                    print(content[:500])
                    print()

                    articles.append({
                        "title": spanish_title,
                        "content": content,
                        "url": url,
                        "image_url": image_url,
                        "image_path": image_path
                    })

                except Exception:
                    continue

            if articles:
                with open(ARTICLES_FILE, 'w', encoding='utf-8') as f:
                    json.dump(articles, f, ensure_ascii=False, indent=2)

            return articles

        except Exception:
            return []

    # ---------------- IMAGE DOWNLOAD ----------------
    def download_image(self, image_url, article_index):
        try:
            parsed_url = urlparse(image_url)
            filename = os.path.basename(parsed_url.path) or f"article_{article_index}.jpg"
            filename = re.sub(r'[^\w\-_\.]', '_', filename)
            image_path = os.path.join(IMAGES_DIR, filename)

            response = requests.get(image_url, stream=True, timeout=10)
            response.raise_for_status()

            with open(image_path, 'wb') as f:
                for chunk in response.iter_content(8192):
                    f.write(chunk)

            if DEBUG:
                print(f"📷 Image saved: {image_path}")

            return image_path
        except Exception:
            return None

    # ---------------- TRANSLATION ----------------
    def translate_titles(self, articles):
        translated_titles = []

        for i, article in enumerate(articles, 1):
            try:
                spanish_title = article["title"]

                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        translated = self.translator.translate(spanish_title)
                        break
                    except Exception:
                        if attempt < max_retries - 1:
                            time.sleep(2)
                        else:
                            raise

                article["translated_title"] = translated
                translated_titles.append(translated)

                print(f"   → {translated}")

                time.sleep(1)

            except Exception:
                article["translated_title"] = article["title"]
                translated_titles.append(article["title"])

        with open(ARTICLES_FILE, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)

        return translated_titles

    # ---------------- HEADER ANALYSIS ----------------
    def analyze_headers(self, translated_titles):
        all_words = []

        for title in translated_titles:
            if title:
                normalized = unicodedata.normalize("NFKD", title.lower())
                normalized = "".join(c for c in normalized if not unicodedata.combining(c))
                words = re.findall(r"\b[a-z]+\b", normalized)
                all_words.extend(words)

        counts = Counter(all_words)

        repeated = {
            word: count
            for word, count in counts.items()
            if count > 2
        }

        return repeated

    # ---------------- PIPELINE RUN ----------------
    def run(self):
        try:
            self.setup_driver()
            self.driver.get(BASE_URL)

            self.handle_cookie_consent()

            if not self.verify_spanish_language():
                print("Page is not in Spanish. Exiting.")
                return False

            if not self.navigate_to_opinion():
                return False

            articles = self.scrape_articles()
            if not articles:
                return False

            translated_titles = self.translate_titles(articles)

            repeated = self.analyze_headers(translated_titles)

            if repeated:
                print("Repeated words (>2):")
                for word, count in sorted(repeated.items(), key=lambda x: x[1], reverse=True):
                    print(f"  • {word}: {count}")
            else:
                print("No words repeated more than twice.")

            return True

        except Exception:
            return False

        finally:
            if self.driver:
                self.driver.quit()


# ---------------- BROWSERSTACK RUNNER ----------------
def run_on_browserstack(config):
    scraper = ElPaisScraper(remote=True, browser_config=config)
    result = scraper.run()
    return {"config": config, "success": result}


# ---------------- MAIN ----------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--local', action='store_true', help='Run locally instead of BrowserStack')
    args = parser.parse_args()

    if args.local:
        print("Running locally...")
        global DEBUG
        DEBUG = True
        ElPaisScraper().run()
    else:
        print("Running on BrowserStack with 5 parallel threads...")
        configs = [
            {"browser": "Chrome", "os": "Windows", "os_version": "10"},
            {"browser": "Firefox", "os": "Windows", "os_version": "10"},
            {"browser": "Safari", "os": "OS X", "os_version": "Big Sur"},
            {"device": "iPhone 13", "real_mobile": "true", "os_version": "15"},
            {"device": "Samsung Galaxy S22", "real_mobile": "true", "os_version": "12"}
        ]

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(run_on_browserstack, configs))

        print("\n" + "="*60)
        print("BROWSERSTACK RESULTS")
        print("="*60)
        for result in results:
            config = result["config"]
            status = "✅ SUCCESS" if result["success"] else "❌ FAILED"

            if config.get("device"):
                print(f"{config['device']}: {status}")
            else:
                print(f"{config['browser']} on {config['os']}: {status}")
        print("="*60)


if __name__ == "__main__":
    main()

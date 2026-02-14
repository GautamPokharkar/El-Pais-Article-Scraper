# El País Article Scraper — Selenium + API + Text Analysis

## 📌 Overview

This project demonstrates **web scraping, API integration, text processing, and cross-browser automation** using the **Selenium framework**.

The script:

- Visits the Spanish news website **El País**
- Ensures the page content is in **Spanish**
- Scrapes the **Opinion** section
- Extracts the **first five articles**
- Prints **titles and content in Spanish**
- Downloads **cover images** (if available)
- Translates article titles to **English** using a translation API
- Performs **word frequency analysis** on translated titles
- Runs **locally** and on **BrowserStack** across desktop and mobile browsers

---

## 🧰 Tech Stack

- **Python**
- **Selenium**
- **Requests** (image download)
- **deep_translator** (Google Translate API wrapper)
- **BrowserStack Automate**
- **ThreadPoolExecutor** (parallel cross-browser runs)

---

## 📂 Project Structure
elpais_scraper.py
output/
├── articles.json
└── images/


---

## ⚙️ Features Implemented

### 1. Visit El País
- Navigates to: https://elpais.com
- Verifies that the page content is displayed in **Spanish**

---

### 2. Scrape Opinion Articles
- Opens the **Opinion** section
- Fetches the **first five articles**
- Extracts:
  - 📰 Title (Spanish)
  - 📄 Article content (Spanish)
  - 🖼 Cover image (if available)
- Saves images locally to `/output/images`

---

### 3. Translate Article Headers
- Uses **Google Translate API (via deep_translator)**  
- Translates Spanish titles → **English**
- Prints translated titles in console
- Stores translations in `articles.json`

---

### 4. Text Processing & Analysis
- Tokenizes all translated titles
- Counts **all words (no stop-word removal)** as required
- Identifies words repeated **more than twice**
- Prints each repeated word with its frequency

Example output:

---

## ⚙️ Features Implemented

### 1. Visit El País
- Navigates to: https://elpais.com
- Verifies that the page content is displayed in **Spanish**

---

### 2. Scrape Opinion Articles
- Opens the **Opinion** section
- Fetches the **first five articles**
- Extracts:
  - 📰 Title (Spanish)
  - 📄 Article content (Spanish)
  - 🖼 Cover image (if available)
- Saves images locally to `/output/images`

---

### 3. Translate Article Headers
- Uses **Google Translate API (via deep_translator)**  
- Translates Spanish titles → **English**
- Prints translated titles in console
- Stores translations in `articles.json`

---

### 4. Text Processing & Analysis
- Tokenizes all translated titles
- Counts **all words (no stop-word removal)** as required
- Identifies words repeated **more than twice**
- Prints each repeated word with its frequency

Example output:
Repeated words (>2):
• the: 4
• of: 3


---

### 5. Image Download
- Detects article cover images
- Downloads using `requests`
- Saves with sanitized filenames

---

### 6. Cross-Browser Testing (BrowserStack)

The framework supports **parallel execution across 5 configurations**:

| Platform | Browser / Device |
|----------|------------------|
| Windows 10 | Chrome |
| Windows 10 | Firefox |
| macOS Big Sur | Safari |
| iPhone 13 | Real Mobile |
| Samsung Galaxy S22 | Real Mobile |

Parallel execution is handled using:

``python
ThreadPoolExecutor(max_workers=5)
🖥️ Local Execution

Run locally to validate full functionality:

python elpais_scraper.py --local
This will:

Scrape 5 articles

Download images

Translate titles

Perform word frequency analysis

Save results to output/articles.json

This will:

Scrape 5 articles

Download images

Translate titles

Perform word frequency analysis

Save results to output/articles.json
☁️ BrowserStack Execution

Set your credentials:

export BROWSERSTACK_USERNAME=your_username
export BROWSERSTACK_ACCESS_KEY=your_access_key


Run:

python elpais_scraper.py


This executes the scraper across 5 parallel desktop and mobile environments.


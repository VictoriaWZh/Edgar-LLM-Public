import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import schedule
import time

BASE_URL = "https://www.eastsideprep.org/"  # Replace with correct domain if needed
visited = set()
DATA_FOLDER = "data"
OUTPUT_FILE = os.path.join(DATA_FOLDER, "eps_website_data.txt")

def clean_text(text):
    return ' '.join(text.split())

def crawl(url, depth=0):
    if url in visited or depth > 100:
        return ""
    visited.add(url)
    
    try:
        response = requests.get(url, timeout=5)
        if not response.ok:
            return ""
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string.strip() if soup.title else "No Title"
        text = soup.get_text()
        cleaned = clean_text(text)
        
        # Header for organization
        section = f"\n\n=== {title} ===\nURL: {url}\n{cleaned}\n"
        
        # Find and follow internal links
        for link in soup.find_all("a", href=True):
            href = link["href"]
            full_url = urljoin(url, href)
            if urlparse(full_url).netloc == urlparse(BASE_URL).netloc:
                section += crawl(full_url, depth + 1)
                
        return section
    except Exception as e:
        return f"\n[Error accessing {url}: {e}]\n"

def save_organized_data():
    print("Crawling EPS website...")
    visited.clear()
    raw_data = crawl(BASE_URL)
    
    os.makedirs(DATA_FOLDER, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(raw_data)
    
    print(f"[✓] Data saved to {OUTPUT_FILE}")

# Schedule to run monthly
schedule.every(30).days.do(save_organized_data)

if __name__ == "__main__":
    save_organized_data()  # Run once initially
    while True:
        schedule.run_pending()
        time.sleep(3600)  # Check every hour

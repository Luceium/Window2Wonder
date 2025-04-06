import json
import os
import time
from collections import deque
from typing import List, Dict, Any, Set, Deque

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def initialize_driver():
    """Initialize and configure the Chrome WebDriver for Fedora with Flatpak"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # For Flatpak Chrome/Chromium
    flatpak_chrome_path = "/var/lib/flatpak/app/org.chromium.Chromium/current/active/files/bin/chromium"
    if os.path.exists(flatpak_chrome_path):
        chrome_options.binary_location = flatpak_chrome_path
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def get_page_content(driver, url: str, timeout: int = 20):
    """Load a page using Selenium and wait for key elements to render"""
    try:
        driver.get(url)
        # Wait for either the title element or video carousel to be present
        # This indicates the page has loaded enough for our needs
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span#cam-group-title, div#video-carousel"))
            )
        except TimeoutException:
            print(f"Page load timeout for {url}, but continuing with partial content")
        
        return True
    except Exception as e:
        print(f"Error loading page {url}: {e}")
        return False

def extract_youtube_url(driver):
    """Extract YouTube URL from iframe using Selenium"""
    try:
        iframe = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.video-player-wrap iframe"))
        )
        src = iframe.get_attribute('src')
        if src and 'youtube.com/embed' in src:
            video_id = src.split('/embed/')[1].split('?')[0]
            return f"https://www.youtube.com/watch?v={video_id}"
    except (TimeoutException, NoSuchElementException):
        pass
    
    # Fallback: Try to get from meta tags
    try:
        meta_video = driver.find_element(By.CSS_SELECTOR, 'meta[property="og:video"]')
        src = meta_video.get_attribute('content')
        if src and 'youtube.com/embed' in src:
            video_id = src.split('/embed/')[1].split('?')[0]
            return f"https://www.youtube.com/watch?v={video_id}"
    except NoSuchElementException:
        pass
    
    return ""

def process_stream_page(driver, url: str) -> Dict[str, Any]:
    """Process an individual stream page using Selenium"""
    print(f"Processing stream page: {url}")
    
    # Load the page with Selenium
    success = get_page_content(driver, url)
    if not success:
        return {"stream": None, "related_links": []}
    
    # Extract title
    title = "Unknown Camera"
    try:
        title_element = driver.find_element(By.CSS_SELECTOR, 'span#cam-group-title')
        title = title_element.text.strip()
    except NoSuchElementException:
        # Fallback to meta title
        try:
            meta_title = driver.find_element(By.CSS_SELECTOR, 'meta[property="og:title"]')
            title = meta_title.get_attribute('content').split('|')[0].strip()
        except NoSuchElementException:
            pass
    
    # Extract description
    description = ""
    try:
        desc_element = driver.find_element(By.CSS_SELECTOR, 'div.widget.panel.cam > div > div > p')
        description = desc_element.text.strip()
    except NoSuchElementException:
        # Fallback to meta description
        try:
            meta_desc = driver.find_element(By.CSS_SELECTOR, 'meta[property="og:description"]')
            description = meta_desc.get_attribute('content').strip()
        except NoSuchElementException:
            pass
    
    # Extract YouTube URL
    youtube_url = extract_youtube_url(driver)
    
    # Find related videos for the queue
    related_links = []
    try:
        carousel_items = driver.find_elements(By.CSS_SELECTOR, 'div#video-carousel > div > a')
        for item in carousel_items:
            href = item.get_attribute('href')
            if href and '/livecams/' in href:
                related_links.append(href)
    except NoSuchElementException:
        # Try alternative selector if video-carousel isn't found
        try:
            link_elements = driver.find_elements(By.CSS_SELECTOR, 'a[href^="/livecams/"]')
            for link in link_elements:
                href = link.get_attribute('href')
                if href and '/livecams/' in href and 'category' not in href and 'search' not in href:
                    related_links.append(href)
        except NoSuchElementException:
            pass
    
    print(f"Found stream: {title}")
    print(f"Description: {description[:50]}...")
    print(f"YouTube URL: {youtube_url}")
    print(f"Found {len(related_links)} related links")
    
    return {
        "stream": {
            "name": title,
            "description": description,
            "url": youtube_url,
            "source_url": url,
            "embedding": 0
        } if youtube_url else None,
        "related_links": related_links
    }

def load_state():
    """Load queue and visited set from disk"""
    queue = deque()
    visited = set()
    
    # Load queue
    if os.path.exists('queue.json'):
        try:
            with open('queue.json', 'r') as f:
                queue_list = json.load(f)
                queue = deque(queue_list)
        except Exception as e:
            print(f"Error loading queue: {e}")
    
    # Load visited set
    if os.path.exists('visited.json'):
        try:
            with open('visited.json', 'r') as f:
                visited_list = json.load(f)
                visited = set(visited_list)
        except Exception as e:
            print(f"Error loading visited set: {e}")
    
    return queue, visited

def save_state(queue: Deque[str], visited: Set[str]):
    """Save queue and visited set to disk"""
    # Save queue
    with open('queue.json', 'w') as f:
        json.dump(list(queue), f)
    
    # Save visited set
    with open('visited.json', 'w') as f:
        json.dump(list(visited), f)

def save_stream(stream: Dict[str, Any], filename: str = "streams.local.json"):
    """Save a single stream to the JSON file"""
    if not stream:
        return
        
    # Load existing streams
    existing_streams = []
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            try:
                existing_streams = json.load(f)
            except json.JSONDecodeError:
                print(f"Error reading existing file {filename}, creating new one")
    
    # Check if URL already exists
    existing_urls = {s.get('url', '') for s in existing_streams}
    
    if stream['url'] and stream['url'] not in existing_urls:
        existing_streams.append(stream)
        
        # Write back to file
        with open(filename, 'w') as f:
            json.dump(existing_streams, f, indent=2)
        
        print(f"Added new stream: {stream['name']}")
    else:
        print(f"Stream already exists or has no URL: {stream['name']}")

def crawl_main_page(driver, queue, visited):
    """Process the main livecams page to find starting links"""
    url = "https://explore.org/livecams"
    print(f"Visiting main page: {url}")
    
    success = get_page_content(driver, url)
    if not success:
        return

    # Try to find livecam card links
    try:
        livecam_links = driver.find_elements(By.CSS_SELECTOR, 'a.livecam-card__link')
        for link in livecam_links:
            href = link.get_attribute('href')
            if href and '/livecams/' in href:
                if href not in visited and href not in queue:
                    queue.append(href)
                    print(f"Added to queue: {href}")
    except NoSuchElementException:
        # Alternate approach: find all links to livecams
        try:
            links = driver.find_elements(By.CSS_SELECTOR, 'a[href^="/livecams/"]')
            for link in links:
                href = link.get_attribute('href')
                if href and '/category/' not in href and '/search/' not in href:
                    if href not in visited and href not in queue:
                        queue.append(href)
                        print(f"Added to queue: {href}")
        except NoSuchElementException:
            print("Could not find any livecam links on the main page")

def crawler():
    """Main crawler function using BFS approach with Selenium"""
    # Initialize WebDriver
    driver = initialize_driver()
    
    try:
        # Load state
        queue, visited = load_state()
        
        # If queue is empty, start with the main page
        if not queue:
            crawl_main_page(driver, queue, visited)
        
        # Process queue
        while queue:
            # Get next URL to process
            current_url = queue.popleft()
            
            # Skip if already visited
            if current_url in visited:
                continue
            
            print(f"\nVisiting: {current_url}")
            visited.add(current_url)
            
            # Process the current page
            try:
                result = process_stream_page(driver, current_url)
                
                # Save stream data if available
                if result["stream"]:
                    save_stream(result["stream"])
                
                # Add related links to queue
                for link in result["related_links"]:
                    if link not in visited and link not in queue:
                        queue.append(link)
            
            except Exception as e:
                print(f"Error processing {current_url}: {e}")
            
            # Save state after each page
            save_state(queue, visited)
            
            # Rate limiting to be gentle on the server
            time.sleep(2)
            
            # Status update
            print(f"Queue size: {len(queue)}, Visited: {len(visited)}")
    
    except KeyboardInterrupt:
        print("\nScraping paused. Progress saved.")
    except Exception as e:
        print(f"Error during crawling: {e}")
    finally:
        # Final state save
        save_state(queue, visited)
        # Clean up Selenium resources
        driver.quit()
        print("Crawler state saved and browser closed.")

if __name__ == "__main__":
    crawler()
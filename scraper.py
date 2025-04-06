import requests
from bs4 import BeautifulSoup
import json
import os
import re
import time
from collections import deque
from typing import List, Dict, Any, Set, Deque

def get_page_content(url: str) -> str:
    """Fetch the HTML content of the explore.org livecams page"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    if response.status_code != 200:
        raise Exception(f"Failed to fetch page content: {response.status_code}")
    if not response.text:
        raise Exception("Failed to receive HTML")
    print(response.text)
    return response.text

def extract_youtube_url(html_content: str) -> str:
    """Extract YouTube URL from iframe"""
    soup = BeautifulSoup(html_content, 'html.parser')
    iframe = soup.select_one('div.video-player-wrap iframe')
    
    if iframe and 'src' in iframe.attrs:
        src = iframe['src']
        if 'youtube.com/embed' in src:
            video_id = src.split('/embed/')[1].split('?')[0]
            return f"https://www.youtube.com/watch?v={video_id}"
    
    return ""

def process_stream_page(url: str) -> Dict[str, Any]:
    """Process an individual stream page"""
    print(f"Processing stream page: {url}")
    html_content = get_page_content(url)
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract title
    title_element = soup.select_one('span#cam-group-title')
    title = title_element.text.strip() if title_element else "Unknown Camera"
    
    # Extract description
    desc_element = soup.select_one('div.widget.panel.cam > div > div > p')
    description = desc_element.text.strip() if desc_element else ""
    
    # Extract YouTube URL
    youtube_url = extract_youtube_url(html_content)
    
    # Find related videos for the queue
    related_links = []
    carousel_items = soup.select('div#video-carousel > div > a')
    for item in carousel_items:
        if 'href' in item.attrs and item['href'].startswith('/livecams/'):
            related_links.append("https://explore.org" + item['href'])
    
    return {
        "stream": {
            "name": title,
            "description": description,
            "url": youtube_url,
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
    
    if stream['url'] not in existing_urls:
        existing_streams.append(stream)
        
        # Write back to file
        with open(filename, 'w') as f:
            json.dump(existing_streams, f, indent=2)
        
        print(f"Added new stream: {stream['name']}")
    else:
        print(f"Stream already exists: {stream['name']}")

def crawler():
    """Main crawler function using BFS approach"""
    # Initial state
    queue, visited = load_state()
    
    # If queue is empty, start with the main page
    if not queue:
        queue.append("https://explore.org/livecams")
    
    try:
        while queue:
            # Get next URL to process
            current_url = queue.popleft()
            
            # Skip if already visited
            if current_url in visited:
                continue
            
            print(f"Visiting: {current_url}")
            visited.add(current_url)
            
            # Process differently based on URL
            if current_url == "https://explore.org/livecams":
                # Main livecams page - find all livecam links
                html_content = get_page_content(current_url)
                soup = BeautifulSoup(html_content, 'html.parser')
                
                livecam_links = soup.select('a.livecam-card__link')
                for link in livecam_links:
                    if 'href' in link.attrs and link['href'].startswith('/livecams/'):
                        next_url = "https://explore.org" + link['href']
                        if next_url not in visited:
                            queue.append(next_url)
            else:
                # Individual stream page
                try:
                    result = process_stream_page(current_url)
                    
                    # Save stream data if available
                    if result["stream"]:
                        save_stream(result["stream"])
                    
                    # Add related links to queue
                    for link in result["related_links"]:
                        if link not in visited:
                            queue.append(link)
                
                except Exception as e:
                    print(f"Error processing {current_url}: {e}")
            
            # Save state after each page
            save_state(queue, visited)
            
            # Rate limiting
            time.sleep(1)
            
            # Status update
            print(f"Queue size: {len(queue)}, Visited: {len(visited)}")
    
    except KeyboardInterrupt:
        print("\nScraping paused. Progress saved.")
    except Exception as e:
        print(f"Error during crawling: {e}")
    finally:
        # Final state save
        save_state(queue, visited)
        print("Crawler state saved.")

if __name__ == "__main__":
    crawler()
from pymongo.cursor import CommandCursor
import os
import concurrent.futures
import json
import subprocess
from typing import List, Dict, Any, Optional

def display_res(res: CommandCursor):    
    # Find the first live stream
    live_url = find_first_live_stream([item["url"] for item in res if 'url' in item])
    
    if live_url:
        print(f"Found active stream: {live_url}")
        return os.system() # display and center crop stream
    else:
        print("No active streams found")
        return None

def is_stream_live(url: str) -> bool:
    """Check if a YouTube stream is currently live"""
    try:
        # Using yt-dlp to check if stream is live
        cmd = [
            "yt-dlp", 
            "--skip-download", 
            "--print", "is_live", 
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        # If "True" is in the output, the stream is live
        return "True" in result.stdout
    except Exception as e:
        print(f"Error checking stream {url}: {e}")
        return False

def find_first_live_stream(urls: List[Dict[str, Any]]) -> Optional[str]:
    """Check all streams in parallel and return the first live one"""
    
    print(f"Checking {len(urls)} streams for availability...")
    
    # Check streams in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(is_stream_live, url): url for url in urls}
        
        # As each check completes, return the first live URL
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                is_live = future.result()
                if is_live:
                    # Cancel all remaining futures
                    for f in future_to_url:
                        if not f.done():
                            f.cancel()
                    return url
            except Exception as e:
                print(f"Error processing result for {url}: {e}")
    
    # If no live streams found
    return None

# For testing
if __name__ == "__main__":
    print("Testing display.py")
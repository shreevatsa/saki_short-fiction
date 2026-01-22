#!/usr/bin/env python3
"""Download text from Wikisource URLs and save to files."""

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse
import time

try:
    import requests
except ImportError:
    print("Installing requests library...")
    os.system("pip install requests -q")
    import requests

from bs4 import BeautifulSoup

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Installing beautifulsoup4 library...")
    os.system("pip install beautifulsoup4 -q")
    from bs4 import BeautifulSoup


def load_urls(json_file):
    """Load URLs from JSON file."""
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def extract_text_from_wikisource(url):
    """Extract text content from a Wikisource page."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to find prose div first (most reliable for chapter pages)
        prose_div = soup.find('div', {'class': 'prose'})
        if prose_div:
            text = prose_div.get_text(separator='\n', strip=True)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return '\n'.join(lines) if lines else None
        
        # Fall back to mw-parser-output for full collection pages
        content_div = soup.find('div', {'class': 'mw-parser-output'})
        if content_div:
            # Remove unwanted elements (scripts, styles, etc.) but keep prose
            for tag in content_div.find_all(['script', 'style']):
                tag.decompose()
            
            # Get text
            text = content_div.get_text(separator='\n', strip=True)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return '\n'.join(lines) if lines else None
        
        # Try mw-content-text as last resort
        mw_content = soup.find('div', {'id': 'mw-content-text'})
        if mw_content:
            for tag in mw_content.find_all(['script', 'style']):
                tag.decompose()
            text = mw_content.get_text(separator='\n', strip=True)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return '\n'.join(lines) if lines else None
        
        return None
            
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def save_text(text, output_file):
    """Save text to a file."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(text)


def main():
    json_file = '/workspaces/saki_short-fiction/wikisource/wikisource_urls.json'
    output_dir = '/workspaces/saki_short-fiction/wikisource/texts'
    
    data = load_urls(json_file)
    
    # Filter entries that have valid wikisource URLs
    entries_with_urls = [item for item in data if item.get('wikisource_url')]
    
    print(f"Found {len(entries_with_urls)} entries with Wikisource URLs")
    print(f"Downloading texts to {output_dir}\n")
    
    downloaded = 0
    failed = 0
    
    for i, item in enumerate(entries_with_urls, 1):
        title = item['title']
        url = item['wikisource_url']
        
        # Create output filename from href
        href = item['href']
        filename = os.path.basename(href).replace('.xhtml', '.txt')
        output_file = os.path.join(output_dir, filename)
        
        print(f"[{i}/{len(entries_with_urls)}] Downloading: {title}")
        print(f"    URL: {url}")
        
        text = extract_text_from_wikisource(url)
        
        if text:
            save_text(text, output_file)
            print(f"    ✓ Saved to {filename}")
            downloaded += 1
        else:
            print(f"    ✗ Failed to extract text")
            failed += 1
        
        # Be respectful to Wikisource servers
        time.sleep(0.5)
    
    print(f"\n{'='*60}")
    print(f"Download complete!")
    print(f"Successfully downloaded: {downloaded}")
    print(f"Failed: {failed}")
    print(f"Output directory: {output_dir}")


if __name__ == '__main__':
    main()

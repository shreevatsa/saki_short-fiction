#!/usr/bin/env python3
"""Compare repo XHTML text with Wikisource plain text."""

import re
import sys
from pathlib import Path
from html.parser import HTMLParser
from html import unescape

class TextExtractor(HTMLParser):
    """Extract text from HTML while preserving text content."""
    
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.in_style_or_script = False
        
    def handle_starttag(self, tag, attrs):
        if tag in ['style', 'script']:
            self.in_style_or_script = True
    
    def handle_endtag(self, tag):
        if tag in ['style', 'script']:
            self.in_style_or_script = False
        # Add space after block elements
        if tag in ['p', 'div', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.text_parts.append('\n')
    
    def handle_data(self, data):
        if not self.in_style_or_script:
            self.text_parts.append(data)
    
    def get_text(self):
        return ''.join(self.text_parts)


def extract_text_from_xhtml(xhtml_path):
    """Extract clean text from XHTML file."""
    with open(xhtml_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    parser = TextExtractor()
    parser.feed(content)
    text = parser.get_text()
    
    # Unescape HTML entities
    text = unescape(text)
    
    # Extract only the story body (skip title and metadata)
    # Find the main story content after <article> tags
    match = re.search(r'<article[^>]*>.*?<h2[^>]*>([^<]*)</h2>\s*(.*?)</article>', content, re.DOTALL)
    if match:
        story_title = match.group(1).strip()
        story_body = match.group(2)
        # Parse just the body
        parser = TextExtractor()
        parser.feed(story_body)
        text = parser.get_text()
        text = unescape(text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


def normalize_text(text, is_wikisource=False):
    """Normalize text for comparison."""
    
    if is_wikisource:
        # For Wikisource: skip metadata and find where actual story starts
        # Look for the chapter marker line (single uppercase letter on its own)
        # The pattern is: "Layout 2" followed by zero-width space, then title, then "I" or chapter number, then story
        
        # Find and skip metadata section (everything up to and including first chapter marker)
        match = re.search(r'Layout \d+[\s\S]*?\n[A-Z]\n', text)
        if match:
            text = text[match.end():]
    
    # Normalize whitespace and zero-width spaces
    text = text.replace('​', '')  # zero-width space
    text = re.sub(r'\s+', ' ', text)
    
    # Normalize all types of dashes FIRST (before quote normalization)
    text = text.replace('⁠—', '--')  # em dash with zero-width space
    text = text.replace('—', '--')  # em dash
    text = text.replace('–', '-')   # en dash
    
    # Normalize all types of quotation marks to straight quotes
    # Using Unicode escape sequences to ensure correct characters
    text = text.replace('\u201C', '"')   # U+201C left double quotation mark → "
    text = text.replace('\u201D', '"')   # U+201D right double quotation mark → "
    text = text.replace('\u2018', "'")   # U+2018 left single quotation mark → '
    text = text.replace('\u2019', "'")   # U+2019 right single quotation mark/apostrophe → '
    
    # Normalize punctuation spacing
    # Remove spaces before punctuation, normalize spacing after
    text = re.sub(r'\s+([,;:!?])', r'\1', text)  # Remove spaces before punctuation
    text = re.sub(r'([,;:!?])\s+', r'\1 ', text)  # Normalize to single space after
    
    # Remove commas and semicolons before comparing (stylistic differences)
    text = re.sub(r'[,;]', '', text)  # Remove commas and semicolons
    
    # Normalize em-dashes (both -- and —) to a standard form
    text = text.replace('--', '—')  # Normalize -- to em-dash
    text = text.replace('⁠—', '—')  # Remove zero-width space before em-dash
    
    # Normalize spacing around em-dashes
    text = re.sub(r'\s*—\s*', ' — ', text)  # Normalize spacing around em-dashes
    
    # Standardize hyphenation (remove soft hyphens and standardize compounds)
    text = text.replace('‐', '-')  # soft hyphen to regular
    
    # Standardize some British/American spelling variants
    replacements = [
        (r'\bcivilisation\b', 'civilization'),
        (r'\bcolour\b', 'color'),
        (r'\bhonour\b', 'honor'),
        (r'\brealised\b', 'realized'),
        (r'\brecognised\b', 'recognized'),
    ]
    
    for old, new in replacements:
        text = re.sub(old, new, text, flags=re.IGNORECASE)
    
    text = text.strip()
    return text


def compare_texts(xhtml_path, txt_path):
    """Compare texts and show differences."""
    
    print(f"Repo file:      {xhtml_path}")
    print(f"Wikisource file: {txt_path}\n")
    
    # Extract text from repo
    xhtml_text = extract_text_from_xhtml(xhtml_path)
    print(f"Extracted text length from XHTML: {len(xhtml_text)} chars")
    print(f"First 200 chars: {xhtml_text[:200]}\n")
    
    # Read Wikisource text
    with open(txt_path, 'r', encoding='utf-8') as f:
        wikisource_text = f.read()
    print(f"Wikisource text length: {len(wikisource_text)} chars")
    print(f"First 200 chars: {wikisource_text[:200]}\n")
    
    # Normalize both
    xhtml_norm = normalize_text(xhtml_text, is_wikisource=False)
    ws_norm = normalize_text(wikisource_text, is_wikisource=True)
    
    print(f"Normalized XHTML length: {len(xhtml_norm)} chars")
    print(f"Normalized Wikisource length: {len(ws_norm)} chars\n")
    
    # Check if they're the same
    if xhtml_norm == ws_norm:
        print("✓ TEXTS MATCH (after normalization)")
    else:
        print("✗ TEXTS DIFFER\n")
        
        # Handle alignment issue: WS text might be missing leading "I" chapter marker
        # If XHTML starts with "It was" and WS starts with "T was", skip the "I"
        if xhtml_norm.startswith("It ") and ws_norm.startswith("T "):
            xhtml_aligned = xhtml_norm[1:]  # Skip the "I"
            ws_aligned = ws_norm
            print("(Aligned texts by skipping missing chapter marker)\n")
        else:
            xhtml_aligned = xhtml_norm
            ws_aligned = ws_norm
        
        # Use difflib to find all differences
        from difflib import SequenceMatcher
        sm = SequenceMatcher(None, xhtml_aligned, ws_aligned)
        
        # Show all differences with context
        print("\nDifferences:")
        diff_count = 0
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag != 'equal':
                diff_count += 1
                repo_text = xhtml_aligned[i1:i2]
                ws_text = ws_aligned[j1:j2]
                
                # Skip trivial whitespace differences
                if repo_text.strip() == ws_text.strip() and len(repo_text) < 5 and len(ws_text) < 5:
                    continue
                
                # Get context around the difference
                context_start = max(0, i1 - 30)
                context_end = min(len(xhtml_aligned), i2 + 30)
                repo_context = xhtml_aligned[context_start:context_end]
                ws_context = ws_aligned[max(0, j1 - 30):min(len(ws_aligned), j2 + 30)]
                
                print(f"\n  [{diff_count}] {tag.upper()} at position {i1}")
                print(f"    Repo:      {repo_context!r}")
                print(f"    Wikisource: {ws_context!r}")
                if repo_text != ws_text and len(repo_text) < 50 and len(ws_text) < 50:
                    print(f"    Change: {repo_text!r} → {ws_text!r}")
        
        print(f"\n\nTotal: {diff_count} difference(s)")


if __name__ == '__main__':
    xhtml_file = '/workspaces/saki_short-fiction/src/epub/text/tobermory.xhtml'
    txt_file = '/workspaces/saki_short-fiction/wikisource/texts/tobermory.txt'
    
    compare_texts(xhtml_file, txt_file)

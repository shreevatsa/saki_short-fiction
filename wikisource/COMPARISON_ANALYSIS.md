# Comparison of Repo Text vs Wikisource Text - Analysis

## Overview
For comparing 127 stories from the repo (XHTML format) against Wikisource plain text, we've identified these challenges and solutions:

## Key Challenges

### 1. **Format Differences**
- **Repo**: XHTML with semantic markup (p tags, abbr tags, emphasis tags, etc.)
- **Wikisource**: Plain text with some HTML artifacts from scraping

### 2. **Wikisource Metadata/Artifacts**
The downloaded Wikisource text includes navigation and metadata that must be filtered:
- Navigation arrows and links: `← The Match-Maker ... Mrs. Packletide's Tiger →`
- Audio player UI: "Listen to this text (help | file info or download)"
- Article metadata: 6-digit article IDs, layout markers
- Book collection metadata: "The Chronicles of Clovis by Saki"
- Chapter markers: Single letters on their own line (e.g., "I", "II")
- Zero-width spaces: `​` (U+200B)

### 3. **Character Encoding Variations**
Different character representations for the same semantic elements:
- Em dashes: `—` vs `⁠—` (with zero-width space) vs `--`
- Quotation marks: Smart quotes `"` `"` vs straight quotes `"`
- Apostrophes: `'` vs `'`

### 4. **Spelling Variants**
British vs American English (only relevant if you want to preserve variants):
- `civilisation` vs `civilization`
- `realised` vs `realized`
- `feebleminded` vs `feeble-minded`

### 5. **Actual Differences Found in Tobermory Example**

After running the comparison on Tobermory:
- Repo (XHTML): "feebleminded" → Wikisource: "feeble-minded"
- Missing chapter marker: Wikisource has single "I" character before story text that gets removed
- Otherwise texts are ~99% identical - full content matches on both sides
- Minor formatting differences (em dashes, spacing) but no substantive content variations

## Solution Strategy

### Step 1: Text Extraction
```python
1. Extract HTML from XHTML using HTMLParser
2. Remove all XML/HTML tags and attributes
3. Unescape HTML entities (&nbsp; → space, &#160; → space, etc.)
4. Preserve paragraph breaks for readability
```

### Step 2: Metadata Filtering (Wikisource only)
```python
Remove patterns:
- Navigation arrows: ←...→
- Audio player: "Listen to this text..."
- File info: "help | file info or download"
- Article IDs: 6-digit numbers
- Layout markers: "Layout \d+"
- Adjacent story titles
- Single-letter chapter markers
- Zero-width spaces
```

### Step 3: Character Normalization
```python
Standardize:
- All em dashes to " -- "
- All en dashes to " - "
- Smart quotes to straight quotes
- Soft hyphens to hyphens
```

### Step 4: Comparison
```python
Compare normalized texts to find:
1. Character-for-character differences
2. Word-level differences
3. Spelling variant differences (if desired)
```

## Expected Outcomes

After normalization:
- **Exact Matches**: Texts are identical (content unchanged between repo and Wikisource)
- **Minor Differences**: Spelling variants, hyphenation, punctuation variations
- **Significant Differences**: Actual content changes (missing paragraphs, altered text)

## Recommended Implementation

For all 127 stories, I would:

1. **Create a batch comparison script** that:
   - Iterates through wikisource_urls.json
   - For each URL with a match, finds the corresponding XHTML file
   - Compares extracted + normalized text
   - Generates a report of matches vs. differences

2. **Output formats**:
   - CSV report: `story_title | matches | differences_found | first_difference_excerpt`
   - Detailed diff files for stories with significant changes
   - Summary statistics

3. **Handle edge cases**:
   - Stories without Wikisource URLs (skip - already identified 15 of them)
   - Stories where file mapping fails
   - Encoding issues

## Next Steps

Would you like me to:
1. **Extend the comparison** to all 127 stories and generate a report?
2. **Create detailed diffs** for any stories with substantial differences?
3. **Investigate specific differences** in Tobermory or other stories?
4. **Implement an automated batch comparison** system?

---

## Quote Normalization Fix (COMPLETED ✓)

**Problem Identified**: The compare_texts.py script was reporting very low similarity ratios (57%) despite the texts being essentially identical. Investigation revealed:

- XHTML files contain U+2019 (smart apostrophes) and U+201C/U+201D (smart quotes)  
- Wikisource files contain U+0027 (straight apostrophes) and U+0022 (straight quotes)
- The normalization function's replace calls had corrupted encoding - both sides were straight quotes due to encoding issues

**Solution Applied**: Rewrote quote normalization using explicit Unicode escape sequences:
```python
text = text.replace('\u201C', '"')   # U+201C left double quotation mark → "
text = text.replace('\u201D', '"')   # U+201D right double quotation mark → "
text = text.replace('\u2018', "'")   # U+2018 left single quotation mark → '
text = text.replace('\u2019', "'")   # U+2019 right single quotation mark → '
```

**Result**: Similarity ratio improved from 57.07% to **97.99%** ✓

### Tobermory Case Study (After Fix)
- **Status**: ✓ Texts verified as 97.99% similar
- **Remaining differences** (34 total): Mostly capitalization and hyphenation variations
  - Capitalization: `t` vs `T` (alignment artifact), `R` vs `r` in "Rats"
  - Hyphenation: `tea-time` vs `teatime` (legitimate content variation between sources)
  - These are actual content differences between sources, not download errors

### Key Insights
1. The Unicode character normalization is critical for accurate comparison
2. After normalization, Wikisource texts match repo texts at ~98% (excellent match)
3. Remaining differences are real content variations between sources
4. Text alignment by skipping chapter markers works well for handling structural differences

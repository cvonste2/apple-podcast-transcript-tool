# Apple Podcast Transcript Tool

A simple Python tool to extract and process transcripts from your local Apple Podcasts cache on macOS.

## What Does It Do?

Apple Podcasts automatically downloads transcript files (TTML format) when you download episodes. This tool:
- Finds all transcript files in your Apple Podcasts cache
- Converts them from TTML (XML) format to clean text files
- Optionally includes timestamps
- Saves them to an organized folder for easy processing
- **Search across all your transcripts** with context

## Requirements

- macOS (tested on recent versions)
- Python 3.7 or higher (comes with macOS)
- Apple Podcasts app with downloaded episodes

## Installation

1. **Clone or download this repository:**
   ```bash
   git clone https://github.com/cvonste2/apple-podcast-transcript-tool.git
   cd apple-podcast-transcript-tool
   ```

2. **That's it!** No additional dependencies needed - uses only Python standard library.

## Usage

### Extract All Transcripts

Simplest usage - extracts all transcripts from your Apple Podcasts cache:

```bash
python3 extract_transcripts.py
```

This creates a `transcripts/` folder with all your podcast transcripts as `.txt` files.

### Include Timestamps

Add timestamps to see when each paragraph was spoken:

```bash
python3 extract_transcripts.py --timestamps
```

Output will include timestamps like:
```
[00:01:23] Welcome to the show!

[00:01:30] Today we're discussing...
```

### Custom Output Directory

Save transcripts to a different folder:

```bash
python3 extract_transcripts.py --output my_transcripts
```

### Extract Single File

Process a specific TTML file:

```bash
python3 extract_transcripts.py --file /path/to/file.ttml
```

## 🔍 Search Transcripts

Once you've extracted transcripts, you can search across all of them:

### Basic Search

```bash
python3 search_transcripts.py "artificial intelligence"
```

This will show you:
- All files containing the search term
- Line numbers where matches occur
- Context (2 lines before and after by default)
- Up to 50 matches (by default)

### Search Options

**More context lines:**
```bash
python3 search_transcripts.py "machine learning" --context 5
```

**Limit number of results:**
```bash
python3 search_transcripts.py "python" --limit 10
```

**Search in a different directory:**
```bash
python3 search_transcripts.py "blockchain" --dir my_transcripts
```

**Unlimited results:**
```bash
python3 search_transcripts.py "startup" --limit 0
```

### Search Examples

```bash
# Find all discussions about Python programming
python3 search_transcripts.py "python programming"

# Find mentions of specific people
python3 search_transcripts.py "Elon Musk"

# Search for technical terms with more context
python3 search_transcripts.py "transformer architecture" --context 4

# Get first 20 mentions of a topic
python3 search_transcripts.py "climate change" --limit 20
```

## Where Are Transcripts Stored?

Apple Podcasts stores transcripts at:
```
~/Library/Group Containers/243LU875E5.groups.com.apple.podcasts/Library/Cache/Assets/TTML
```

**Important Notes:**
- Transcripts are only downloaded for episodes you've downloaded in the Podcasts app
- Not all podcasts provide transcripts
- You may need to play an episode briefly for transcripts to be cached

## Troubleshooting

### "No TTML files found"

**Solutions:**
1. Download some podcast episodes in the Apple Podcasts app
2. Make sure the episodes have transcripts (look for the transcript icon in the app)
3. Try playing the episode briefly to trigger transcript download
4. Check if the TTML directory exists:
   ```bash
   ls ~/Library/Group\ Containers/243LU875E5.groups.com.apple.podcasts/Library/Cache/Assets/TTML
   ```

### Empty or Corrupted Transcripts

If extracted files are empty or garbled, the TTML file might be corrupted. Try:
1. Re-downloading the episode in Apple Podcasts
2. Deleting the episode and downloading again

### "No matches found" when searching

1. Make sure you've extracted transcripts first: `python3 extract_transcripts.py`
2. Check the transcript directory exists and has `.txt` files: `ls transcripts/`
3. Try a broader or different search term
4. Search is case-insensitive, so "AI" will match "ai", "AI", and "Ai"

## Architecture for Vibe Coders

This tool is intentionally simple and modular:

### extract_transcripts.py
```
TranscriptExtractor
├── find_ttml_files()      # Locates all transcript files
├── parse_ttml()           # Converts TTML XML to text
├── format_timestamp()     # Formats time strings
├── extract_single_file()  # Processes one transcript
└── extract_all()          # Batch processes all transcripts
```

### search_transcripts.py
```
Search Functions
├── load_file()            # Read transcript files
├── find_matches_in_lines() # Find query with context
├── search_transcripts()   # Search all files
└── print_results()        # Format and display results
```

**Key Design Decisions:**
- Zero external dependencies (pure Python stdlib)
- Class-based extractor for easy extension
- Functional search for simplicity
- Handles duplicate filenames automatically
- Robust namespace handling for XML parsing
- Case-insensitive search by default
- Clear error messages for common issues

## Extending the Tool

Here are some ideas for expansion:

1. **AI Summarization:** Pipe search results to an LLM for synthesis
2. **Export Search Results:** Add JSON, CSV, or Markdown export options
3. **Regex Search:** Support advanced regex patterns
4. **Metadata Extraction:** Read the SQLite database to link transcripts to podcast names
5. **Web Interface:** Build a Flask app for browser-based search
6. **Multi-term Search:** Search for multiple terms at once (AND/OR logic)
7. **Highlighting:** Add color highlighting in terminal output
8. **Date Filtering:** Search transcripts from specific time periods

## Security & Privacy

- Reads only from your local Apple Podcasts cache
- No network calls or external API access
- No dependencies that could introduce vulnerabilities
- All processing happens locally on your machine
- Source code is simple enough to audit yourself (~350 lines total)

## Contributing

Contributions welcome! This is a simple tool meant to be easily understood and modified.

## License

MIT License - feel free to use, modify, and distribute.

## Credits

Inspired by the need for simple, local podcast transcript processing without unnecessary complexity.

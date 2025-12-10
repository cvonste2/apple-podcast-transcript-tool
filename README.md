# Apple Podcast Transcript Tool

A simple Python tool to extract and process transcripts from your local Apple Podcasts cache on macOS.

## What Does It Do?

Apple Podcasts automatically downloads transcript files (TTML format) when you download episodes. This tool:
- Finds all transcript files in your Apple Podcasts cache
- Converts them from TTML (XML) format to clean text files
- Optionally includes timestamps
- Saves them to an organized folder for easy processing

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
python extract_transcripts.py
```

This creates a `transcripts/` folder with all your podcast transcripts as `.txt` files.

### Include Timestamps

Add timestamps to see when each paragraph was spoken:

```bash
python extract_transcripts.py --timestamps
```

Output will include timestamps like:
```
[00:01:23] Welcome to the show!

[00:01:30] Today we're discussing...
```

### Custom Output Directory

Save transcripts to a different folder:

```bash
python extract_transcripts.py --output my_transcripts
```

### Extract Single File

Process a specific TTML file:

```bash
python extract_transcripts.py --file /path/to/file.ttml
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

## Architecture for Vibe Coders

This tool is intentionally simple and modular:

```
TranscriptExtractor
├── find_ttml_files()      # Locates all transcript files
├── parse_ttml()           # Converts TTML XML to text
├── format_timestamp()     # Formats time strings
├── extract_single_file()  # Processes one transcript
└── extract_all()          # Batch processes all transcripts
```

**Key Design Decisions:**
- Zero external dependencies (pure Python stdlib)
- Class-based for easy extension
- Handles duplicate filenames automatically
- Robust namespace handling for XML parsing
- Clear error messages for common issues

## Extending the Tool

Here are some ideas for expansion:

1. **Search Transcripts:** Add full-text search across all transcripts
2. **Export Formats:** Support JSON, Markdown, or CSV output
3. **Metadata Extraction:** Read the SQLite database to link transcripts to podcast names
4. **AI Processing:** Pipe transcripts to LLMs for summarization or Q&A
5. **GUI:** Add a simple Tkinter interface for non-technical users

## Security & Privacy

- Reads only from your local Apple Podcasts cache
- No network calls or external API access
- No dependencies that could introduce vulnerabilities
- All processing happens locally on your machine
- Source code is simple enough to audit yourself (~200 lines)

## Contributing

Contributions welcome! This is a simple tool meant to be easily understood and modified.

## License

MIT License - feel free to use, modify, and distribute.

## Credits

Inspired by the need for simple, local podcast transcript processing without unnecessary complexity.

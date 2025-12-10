#!/usr/bin/env python3
"""
Apple Podcast Transcript Extractor

Extracts transcripts from Apple Podcasts local cache and saves them as text files.
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path
import argparse
import sys


class TranscriptExtractor:
    """Handles extraction of TTML transcripts from Apple Podcasts cache."""
    
    def __init__(self, output_dir="transcripts", include_timestamps=False):
        """Initialize the transcript extractor.
        
        Args:
            output_dir: Directory to save extracted transcripts
            include_timestamps: Whether to include timestamps in output
        """
        self.output_dir = Path(output_dir)
        self.include_timestamps = include_timestamps
        self.output_dir.mkdir(exist_ok=True)
        
        # Apple Podcasts TTML cache location
        home = Path.home()
        self.ttml_dir = home / "Library" / "Group Containers" / "243LU875E5.groups.com.apple.podcasts" / "Library" / "Cache" / "Assets" / "TTML"
    
    def format_timestamp(self, seconds):
        """Convert seconds to HH:MM:SS format.
        
        Args:
            seconds: Time in seconds (float or string)
            
        Returns:
            Formatted timestamp string
        """
        try:
            total_seconds = float(seconds.rstrip('s')) if isinstance(seconds, str) else float(seconds)
        except (ValueError, AttributeError):
            return "00:00:00"
        
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        secs = int(total_seconds % 60)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def parse_ttml(self, ttml_path):
        """Parse a TTML file and extract text content.
        
        Args:
            ttml_path: Path to TTML file
            
        Returns:
            List of tuples (timestamp, text) or list of text strings
        """
        try:
            tree = ET.parse(ttml_path)
            root = tree.getroot()
            
            # Handle XML namespaces
            namespaces = {'tt': 'http://www.w3.org/ns/ttml'}
            
            # Try with namespace first
            paragraphs = root.findall('.//tt:p', namespaces)
            
            # If no results, try without namespace
            if not paragraphs:
                paragraphs = root.findall('.//{http://www.w3.org/ns/ttml}p')
            
            # Last resort: search for any 'p' tags
            if not paragraphs:
                paragraphs = root.findall('.//p')
            
            transcript_parts = []
            
            for para in paragraphs:
                # Extract all text from paragraph and its children
                # Join with spaces to preserve word boundaries
                text_parts = [t.strip() for t in para.itertext() if t.strip()]
                text = ' '.join(text_parts)
                
                if text:
                    if self.include_timestamps:
                        # Get timestamp from 'begin' attribute
                        timestamp = para.get('begin', '0')
                        formatted_time = self.format_timestamp(timestamp)
                        transcript_parts.append((formatted_time, text))
                    else:
                        transcript_parts.append(text)
            
            return transcript_parts
        
        except Exception as e:
            print(f"Error parsing {ttml_path.name}: {e}")
            return []
    
    def find_ttml_files(self):
        """Find all TTML files in Apple Podcasts cache.
        
        Returns:
            List of Path objects for TTML files
        """
        if not self.ttml_dir.exists():
            print(f"Error: TTML directory not found at {self.ttml_dir}")
            print("\nMake sure you have:")
            print("1. Downloaded podcast episodes in Apple Podcasts app")
            print("2. Episodes have transcripts available")
            print("3. Opened/played episodes to trigger transcript download")
            return []
        
        ttml_files = list(self.ttml_dir.rglob('*.ttml'))
        return ttml_files
    
    def extract_single_file(self, ttml_path, output_path=None):
        """Extract transcript from a single TTML file.
        
        Args:
            ttml_path: Path to TTML file
            output_path: Optional custom output path
        """
        transcript_parts = self.parse_ttml(ttml_path)
        
        if not transcript_parts:
            print(f"No content extracted from {ttml_path.name}")
            return
        
        # Generate output filename
        if output_path is None:
            # Extract podcast episode ID from path
            episode_id = ttml_path.stem
            output_path = self.output_dir / f"{episode_id}.txt"
        
        # Format output
        if self.include_timestamps:
            output_text = '\n\n'.join([f"[{ts}] {text}" for ts, text in transcript_parts])
        else:
            output_text = '\n\n'.join(transcript_parts)
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_text)
        
        print(f"✓ Saved: {output_path.name}")
    
    def extract_all(self):
        """Extract all transcripts from Apple Podcasts cache."""
        ttml_files = self.find_ttml_files()
        
        if not ttml_files:
            print("No TTML files found.")
            return
        
        print(f"Found {len(ttml_files)} transcript file(s)\n")
        
        # Track filenames to handle duplicates
        filename_counts = {}
        
        for ttml_path in ttml_files:
            # Generate unique filename
            base_name = ttml_path.stem
            count = filename_counts.get(base_name, 0)
            
            if count > 0:
                output_filename = f"{base_name}-{count}.txt"
            else:
                output_filename = f"{base_name}.txt"
            
            filename_counts[base_name] = count + 1
            
            output_path = self.output_dir / output_filename
            self.extract_single_file(ttml_path, output_path)
        
        print(f"\n✓ Extraction complete! Files saved to: {self.output_dir.absolute()}")


def main():
    parser = argparse.ArgumentParser(
        description='Extract transcripts from Apple Podcasts local cache',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  Extract all transcripts:
    python extract_transcripts.py
  
  Include timestamps:
    python extract_transcripts.py --timestamps
  
  Custom output directory:
    python extract_transcripts.py --output my_transcripts
        """
    )
    
    parser.add_argument(
        '--timestamps',
        action='store_true',
        help='Include timestamps in output'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='transcripts',
        help='Output directory for transcripts (default: transcripts)'
    )
    
    parser.add_argument(
        '--file', '-f',
        help='Extract a specific TTML file instead of all files'
    )
    
    args = parser.parse_args()
    
    # Create extractor
    extractor = TranscriptExtractor(
        output_dir=args.output,
        include_timestamps=args.timestamps
    )
    
    # Extract transcripts
    if args.file:
        # Single file mode
        ttml_path = Path(args.file)
        if not ttml_path.exists():
            print(f"Error: File not found: {ttml_path}")
            sys.exit(1)
        
        extractor.extract_single_file(ttml_path)
    else:
        # Batch mode
        extractor.extract_all()


if __name__ == '__main__':
    main()

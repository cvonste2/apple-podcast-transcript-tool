#!/usr/bin/env python3
"""
Apple Podcast Transcript Extractor with Metadata

Extracts transcripts with proper filenames using podcast metadata from Apple Podcasts database.
"""

import os
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
import argparse
import sys
import re
from datetime import datetime


class MetadataExtractor:
    """Handles extraction of TTML transcripts with metadata from Apple Podcasts."""
    
    def __init__(self, output_dir="transcripts_with_metadata", include_timestamps=False):
        """Initialize the extractor.
        
        Args:
            output_dir: Directory to save extracted transcripts
            include_timestamps: Whether to include timestamps in output
        """
        self.output_dir = Path(output_dir)
        self.include_timestamps = include_timestamps
        self.output_dir.mkdir(exist_ok=True)
        
        # Apple Podcasts paths
        home = Path.home()
        self.ttml_dir = home / "Library" / "Group Containers" / "243LU875E5.groups.com.apple.podcasts" / "Library" / "Cache" / "Assets" / "TTML"
        self.db_path = home / "Library" / "Group Containers" / "243LU875E5.groups.com.apple.podcasts" / "Documents" / "MTLibrary.sqlite"
        
        # Cache for metadata
        self.metadata_cache = {}
        self._load_metadata()
    
    def _load_metadata(self):
        """Load metadata from Apple Podcasts SQLite database."""
        if not self.db_path.exists():
            print(f"Warning: Database not found at {self.db_path}")
            print("Will use generic filenames instead.")
            return
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Query to get episode metadata
            # The database has tables: ZMTEPISODE, ZMTPODCAST
            query = """
                SELECT 
                    e.ZGUID as guid,
                    e.ZTITLE as episode_title,
                    e.ZPUBDATE as pub_date,
                    p.ZTITLE as podcast_title,
                    p.ZAUTHOR as author
                FROM ZMTEPISODE e
                LEFT JOIN ZMTPODCAST p ON e.ZPODCAST = p.Z_PK
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            for row in rows:
                guid, episode_title, pub_date, podcast_title, author = row
                if guid:
                    self.metadata_cache[guid] = {
                        'episode_title': episode_title or 'Unknown Episode',
                        'pub_date': pub_date,
                        'podcast_title': podcast_title or 'Unknown Podcast',
                        'author': author
                    }
            
            conn.close()
            print(f"Loaded metadata for {len(self.metadata_cache)} episodes\n")
            
        except Exception as e:
            print(f"Warning: Could not load metadata from database: {e}")
            print("Will use generic filenames instead.\n")
    
    def _sanitize_filename(self, text):
        """Make text safe for use in filenames.
        
        Args:
            text: Text to sanitize
            
        Returns:
            Sanitized text safe for filenames
        """
        # Remove or replace invalid characters
        text = re.sub(r'[<>:"/\\|?*]', '', text)
        # Replace spaces and other whitespace with underscores
        text = re.sub(r'\s+', '_', text)
        # Limit length
        if len(text) > 100:
            text = text[:100]
        return text
    
    def _format_date(self, timestamp):
        """Format timestamp to readable date.
        
        Args:
            timestamp: Unix timestamp or Core Data timestamp
            
        Returns:
            Formatted date string (YYYY-MM-DD)
        """
        if not timestamp:
            return "UnknownDate"
        
        try:
            # Apple Core Data uses reference date of 2001-01-01
            reference_date = datetime(2001, 1, 1)
            date = reference_date + timedelta(seconds=timestamp)
            return date.strftime("%Y-%m-%d")
        except:
            return "UnknownDate"
    
    def _get_metadata_from_ttml(self, ttml_path):
        """Try to extract metadata from TTML filename or content.
        
        Args:
            ttml_path: Path to TTML file
            
        Returns:
            Dictionary with metadata or None
        """
        # The TTML filename often contains a GUID or ID
        # Try to match it with database metadata
        filename = ttml_path.stem
        
        # Check if we have metadata for this file
        for guid, metadata in self.metadata_cache.items():
            if guid and guid in str(ttml_path):
                return metadata
        
        return None
    
    def format_timestamp(self, seconds):
        """Convert seconds to HH:MM:SS format."""
        try:
            total_seconds = float(seconds.rstrip('s')) if isinstance(seconds, str) else float(seconds)
        except (ValueError, AttributeError):
            return "00:00:00"
        
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        secs = int(total_seconds % 60)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def parse_ttml(self, ttml_path):
        """Parse a TTML file and extract text content."""
        try:
            tree = ET.parse(ttml_path)
            root = tree.getroot()
            
            namespaces = {'tt': 'http://www.w3.org/ns/ttml'}
            paragraphs = root.findall('.//tt:p', namespaces)
            
            if not paragraphs:
                paragraphs = root.findall('.//{http://www.w3.org/ns/ttml}p')
            
            if not paragraphs:
                paragraphs = root.findall('.//p')
            
            transcript_parts = []
            
            for para in paragraphs:
                text_parts = [t.strip() for t in para.itertext() if t.strip()]
                text = ' '.join(text_parts)
                
                if text:
                    if self.include_timestamps:
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
        """Find all TTML files in Apple Podcasts cache."""
        if not self.ttml_dir.exists():
            print(f"Error: TTML directory not found at {self.ttml_dir}")
            return []
        
        ttml_files = list(self.ttml_dir.rglob('*.ttml'))
        return ttml_files
    
    def extract_single_file(self, ttml_path):
        """Extract transcript from a single TTML file with metadata.
        
        Args:
            ttml_path: Path to TTML file
        """
        transcript_parts = self.parse_ttml(ttml_path)
        
        if not transcript_parts:
            print(f"No content extracted from {ttml_path.name}")
            return None
        
        # Get metadata
        metadata = self._get_metadata_from_ttml(ttml_path)
        
        # Generate filename with metadata
        if metadata:
            podcast_name = self._sanitize_filename(metadata['podcast_title'])
            episode_title = self._sanitize_filename(metadata['episode_title'])
            
            # Try to format date
            from datetime import timedelta
            date_str = self._format_date(metadata['pub_date'])
            
            # Create descriptive filename
            filename = f"{podcast_name}_{date_str}_{episode_title}.txt"
        else:
            # Fallback to original filename
            filename = f"{ttml_path.stem}.txt"
        
        output_path = self.output_dir / filename
        
        # Handle duplicate filenames
        if output_path.exists():
            counter = 1
            base = output_path.stem
            while output_path.exists():
                output_path = self.output_dir / f"{base}_{counter}.txt"
                counter += 1
        
        # Format output
        if self.include_timestamps:
            output_text = '\n\n'.join([f"[{ts}] {text}" for ts, text in transcript_parts])
        else:
            output_text = '\n\n'.join(transcript_parts)
        
        # Add metadata header
        if metadata:
            header = f"""Podcast: {metadata['podcast_title']}
Episode: {metadata['episode_title']}
Date: {date_str}
{'='*70}\n\n"""
            output_text = header + output_text
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_text)
        
        print(f"✓ Saved: {output_path.name}")
        return output_path
    
    def extract_all(self):
        """Extract all transcripts with metadata."""
        ttml_files = self.find_ttml_files()
        
        if not ttml_files:
            print("No TTML files found.")
            return
        
        print(f"Found {len(ttml_files)} transcript file(s)\n")
        
        extracted = 0
        for ttml_path in ttml_files:
            result = self.extract_single_file(ttml_path)
            if result:
                extracted += 1
        
        print(f"\n✓ Extraction complete! {extracted} files saved to: {self.output_dir.absolute()}")


def main():
    parser = argparse.ArgumentParser(
        description='Extract transcripts with metadata (podcast names, dates, etc.)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  Extract all transcripts with metadata:
    python3 extract_with_metadata.py
  
  Include timestamps:
    python3 extract_with_metadata.py --timestamps
  
  Custom output directory:
    python3 extract_with_metadata.py --output my_transcripts
        """
    )
    
    parser.add_argument(
        '--timestamps',
        action='store_true',
        help='Include timestamps in output'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='transcripts_with_metadata',
        help='Output directory for transcripts (default: transcripts_with_metadata)'
    )
    
    args = parser.parse_args()
    
    # Create extractor
    extractor = MetadataExtractor(
        output_dir=args.output,
        include_timestamps=args.timestamps
    )
    
    # Extract transcripts
    extractor.extract_all()


if __name__ == '__main__':
    main()

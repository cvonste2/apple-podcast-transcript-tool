#!/usr/bin/env python3
"""
Apple Podcast Transcript Extractor with Metadata

Extracts transcripts with proper filenames using podcast metadata from Apple Podcasts database.
Based on insights from Podsidian (https://github.com/pedramamini/Podsidian)
"""

import os
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
import argparse
import sys
import re
import csv
from datetime import datetime, timedelta
from collections import defaultdict


class MetadataExtractor:
    """Handles extraction of TTML transcripts with metadata from Apple Podcasts."""
    
    def __init__(self, output_dir="transcripts_with_metadata", include_timestamps=False, debug=False):
        """Initialize the extractor.
        
        Args:
            output_dir: Directory to save extracted transcripts
            include_timestamps: Whether to include timestamps in output
            debug: Whether to print debug information
        """
        self.output_dir = Path(output_dir)
        self.include_timestamps = include_timestamps
        self.debug = debug
        self.output_dir.mkdir(exist_ok=True)
        
        # Apple Podcasts paths
        home = Path.home()
        self.ttml_dir = home / "Library" / "Group Containers" / "243LU875E5.groups.com.apple.podcasts" / "Library" / "Cache" / "Assets" / "TTML"
        self.db_path = home / "Library" / "Group Containers" / "243LU875E5.groups.com.apple.podcasts" / "Documents" / "MTLibrary.sqlite"
        
        # Cache for metadata - keyed by podcast Z_PK
        self.podcast_cache = {}
        self.episode_cache = {}
        
        # Tracking for unmatched items
        self.transcript_files = []  # List of all transcript files found
        self.matched_transcripts = set()  # Set of matched transcript file stems
        self.failed_parsing = []  # List of files that failed trackid parsing
        self.db_trackids = set()  # Set of all trackids/GUIDs from database
        self.unmatched_transcript_count = 0  # Count of unmatched transcripts
        self.unmatched_db_count = 0  # Count of unmatched database entries
        
        # Log files
        self.unmatched_transcript_log = self.output_dir / "unmatched_transcripts.log"
        self.unmatched_db_log = self.output_dir / "unmatched_db_entries.log"
        self.mapping_csv = self.output_dir / "transcript_mappings.csv"
        self.failed_parsing_log = self.output_dir / "failed_parsing.log"
        
        self._load_metadata()
    
    def _load_metadata(self):
        """Load metadata from Apple Podcasts SQLite database."""
        if not self.db_path.exists():
            print(f"Warning: Database not found at {self.db_path}")
            print("Will use generic filenames instead.\n")
            return
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # First, let's check what tables exist if in debug mode
            if self.debug:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                print(f"[DEBUG] Database tables found: {[t[0] for t in tables]}")
            
            # Load all podcasts
            try:
                cursor.execute("""
                    SELECT 
                        Z_PK,
                        ZTITLE,
                        ZAUTHOR
                    FROM ZMTPODCAST
                """)
                
                for row in cursor.fetchall():
                    pk, title, author = row
                    self.podcast_cache[pk] = {
                        'title': title or 'Unknown Podcast',
                        'author': author or 'Unknown Author'
                    }
                    if self.debug and len(self.podcast_cache) <= 3:
                        print(f"[DEBUG] Loaded podcast {pk}: {title}")
                
            except sqlite3.OperationalError as e:
                print(f"Warning: Could not query ZMTPODCAST table: {e}")
                if self.debug:
                    # Try to get column names
                    cursor.execute("PRAGMA table_info(ZMTPODCAST)")
                    columns = cursor.fetchall()
                    print(f"[DEBUG] ZMTPODCAST columns: {[c[1] for c in columns]}")
            
            # Load all episodes
            try:
                cursor.execute("""
                    SELECT 
                        ZPODCAST,
                        ZTITLE,
                        ZPUBDATE,
                        ZGUID
                    FROM ZMTEPISODE
                """)
                
                for row in cursor.fetchall():
                    podcast_pk, title, pub_date, guid = row
                    if podcast_pk not in self.episode_cache:
                        self.episode_cache[podcast_pk] = []
                    
                    self.episode_cache[podcast_pk].append({
                        'title': title or 'Unknown Episode',
                        'pub_date': pub_date,
                        'guid': guid
                    })
                    
                    # Track all database trackids for later comparison
                    if guid:
                        self.db_trackids.add(guid)
                    
                    if self.debug and sum(len(eps) for eps in self.episode_cache.values()) <= 3:
                        print(f"[DEBUG] Loaded episode for podcast {podcast_pk}: {title}")
                
            except sqlite3.OperationalError as e:
                print(f"Warning: Could not query ZMTEPISODE table: {e}")
                if self.debug:
                    # Try to get column names
                    cursor.execute("PRAGMA table_info(ZMTEPISODE)")
                    columns = cursor.fetchall()
                    print(f"[DEBUG] ZMTEPISODE columns: {[c[1] for c in columns]}")
            
            conn.close()
            
            print(f"Loaded metadata for {len(self.podcast_cache)} podcasts")
            total_episodes = sum(len(eps) for eps in self.episode_cache.values())
            print(f"Loaded metadata for {total_episodes} episodes\n")
            
        except Exception as e:
            print(f"Warning: Could not load metadata from database: {e}")
            print("Will use generic filenames instead.\n")
            if self.debug:
                import traceback
                traceback.print_exc()
    
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
        # Remove leading/trailing underscores and dots
        text = text.strip('_.')
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
    
    def _get_podcast_id_from_path(self, ttml_path):
        """Extract podcast ID from the PodcastContent### folder structure.
        
        Args:
            ttml_path: Path to TTML file
            
        Returns:
            Podcast ID (int) or None
        """
        # Look for PodcastContent### in the path
        match = re.search(r'PodcastContent(\d+)', str(ttml_path))
        if match:
            podcast_id = int(match.group(1))
            if self.debug:
                print(f"  [DEBUG] Found podcast ID {podcast_id} in path: {ttml_path}")
            return podcast_id
        if self.debug:
            print(f"  [DEBUG] No podcast ID found in path: {ttml_path}")
        return None
    
    def _extract_trackid_from_filename(self, ttml_path):
        """Extract trackid from TTML filename with robust parsing.
        
        Handles various filename patterns including:
        - Standard GUIDs
        - transcript_ABC.ttml patterns
        - Numeric IDs
        - URL-encoded filenames
        
        Args:
            ttml_path: Path to TTML file
            
        Returns:
            Tuple of (trackid, success_flag) where trackid is a string or None
        """
        filename = ttml_path.stem
        
        # Pattern 1: Standard filename (just use as-is)
        if filename:
            # Check for common problematic patterns
            if filename.startswith('transcript_'):
                # Extract part after 'transcript_'
                prefix_len = len('transcript_')
                trackid = filename[prefix_len:]
                if trackid:
                    if self.debug:
                        print(f"  [DEBUG] Extracted trackid '{trackid}' from pattern 'transcript_*'")
                    return trackid, True
                else:
                    if self.debug:
                        print(f"  [DEBUG] Failed to extract trackid from 'transcript_*' pattern: {filename}")
                    return None, False
            
            # Pattern 2: Looks like a valid GUID or identifier (at least 8 chars)
            if len(filename) >= 8:
                return filename, True
            
            # Pattern 3: Short filename, might be problematic but try it
            if self.debug:
                print(f"  [DEBUG] Short filename detected: '{filename}' (len={len(filename)})")
            return filename, True
        
        # No valid trackid found
        if self.debug:
            print(f"  [DEBUG] Could not extract trackid from: {ttml_path}")
        return None, False
    
    def _get_episode_guid_from_path(self, ttml_path):
        """Extract episode GUID from TTML filename.
        
        Args:
            ttml_path: Path to TTML file
            
        Returns:
            Episode GUID (string) or None
        """
        # Use the robust trackid extraction method
        trackid, success = self._extract_trackid_from_filename(ttml_path)
        
        # Log failures for later reporting
        if not success:
            self.failed_parsing.append(str(ttml_path))
        
        return trackid
    
    def _get_metadata_from_path(self, ttml_path):
        """Get metadata for a TTML file based on its path.
        
        Args:
            ttml_path: Path to TTML file
            
        Returns:
            Dictionary with metadata or None
        """
        podcast_id = self._get_podcast_id_from_path(ttml_path)
        episode_guid = self._get_episode_guid_from_path(ttml_path)
        
        if self.debug:
            print(f"  [DEBUG] Episode GUID from filename: {episode_guid}")
        
        if podcast_id is None:
            if self.debug:
                print(f"  [DEBUG] Cannot extract metadata - no podcast ID")
            return None
        
        # Get podcast metadata
        podcast_info = self.podcast_cache.get(podcast_id)
        if not podcast_info:
            if self.debug:
                print(f"  [DEBUG] No podcast info found for ID {podcast_id}")
                print(f"  [DEBUG] Available podcast IDs: {list(self.podcast_cache.keys())[:10]}")
            return None
        
        # Get episodes for this podcast
        episodes = self.episode_cache.get(podcast_id, [])
        
        if self.debug:
            print(f"  [DEBUG] Found {len(episodes)} episodes for podcast ID {podcast_id}")
        
        if not episodes:
            # Return podcast info without episode details
            if self.debug:
                print(f"  [DEBUG] No episodes found, using default metadata")
            return {
                'podcast_title': podcast_info['title'],
                'episode_title': 'Unknown Episode',
                'pub_date': None,
                'author': podcast_info['author']
            }
        
        # First, try to match by GUID (most accurate)
        episode = None
        if episode_guid:
            for ep in episodes:
                if ep['guid']:
                    # Try exact match first
                    if ep['guid'] == episode_guid:
                        episode = ep
                        if self.debug:
                            print(f"  [DEBUG] Matched episode by exact GUID: {episode['title']}")
                        break
                    # Try if GUID contains the episode_guid or vice versa (for URL-based GUIDs)
                    # Only if one is substantially contained in the other
                    elif (episode_guid in ep['guid'] and len(episode_guid) > 10) or \
                         (ep['guid'] in episode_guid and len(ep['guid']) > 10):
                        episode = ep
                        if self.debug:
                            print(f"  [DEBUG] Matched episode by GUID substring: {episode['title']}")
                        break
        
        # If no GUID match, fall back to using the most recent episode
        if not episode:
            if self.debug:
                print(f"  [DEBUG] No GUID match, falling back to most recent episode")
            
            # Sort by pub_date descending
            episodes_sorted = sorted(
                [e for e in episodes if e['pub_date'] is not None],
                key=lambda x: x['pub_date'],
                reverse=True
            )
            
            if self.debug:
                print(f"  [DEBUG] Sorted {len(episodes_sorted)} episodes by date")
            
            if episodes_sorted:
                episode = episodes_sorted[0]
                if self.debug:
                    print(f"  [DEBUG] Using most recent episode: {episode['title']}")
            else:
                episode = episodes[0] if episodes else None
                if self.debug and episode:
                    print(f"  [DEBUG] Using first episode (no dates): {episode['title']}")
        
        if episode:
            return {
                'podcast_title': podcast_info['title'],
                'episode_title': episode['title'],
                'pub_date': episode['pub_date'],
                'author': podcast_info['author']
            }
        
        return {
            'podcast_title': podcast_info['title'],
            'episode_title': 'Unknown Episode',
            'pub_date': None,
            'author': podcast_info['author']
        }
    
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
            
        Returns:
            Dictionary with mapping info or None if failed
        """
        if self.debug:
            print(f"\n[DEBUG] Processing: {ttml_path}")
        
        transcript_parts = self.parse_ttml(ttml_path)
        
        if not transcript_parts:
            print(f"No content extracted from {ttml_path.name}")
            return None
        
        # Extract trackid once for reuse
        trackid, success = self._extract_trackid_from_filename(ttml_path)
        
        # Get metadata
        metadata = self._get_metadata_from_path(ttml_path)
        
        # Track matched transcripts (those with metadata found)
        if metadata and trackid:
            self.matched_transcripts.add(trackid)
        
        if self.debug:
            if metadata:
                print(f"  [DEBUG] Metadata found:")
                print(f"    Podcast: {metadata['podcast_title']}")
                print(f"    Episode: {metadata['episode_title']}")
                print(f"    Date: {self._format_date(metadata['pub_date'])}")
                print(f"    Author: {metadata['author']}")
            else:
                print(f"  [DEBUG] No metadata found for this file")
        
        # Generate filename with metadata
        if metadata:
            podcast_name = self._sanitize_filename(metadata['podcast_title'])
            episode_title = self._sanitize_filename(metadata['episode_title'])
            date_str = self._format_date(metadata['pub_date'])
            
            # Create descriptive filename
            filename = f"{podcast_name}_{date_str}_{episode_title}.txt"
            if self.debug:
                print(f"  [DEBUG] Generated filename: {filename}")
        else:
            # Fallback to path-based naming
            podcast_id = self._get_podcast_id_from_path(ttml_path)
            if podcast_id:
                filename = f"Podcast_{podcast_id}_{ttml_path.stem}.txt"
            else:
                filename = f"{ttml_path.stem}.txt"
            if self.debug:
                print(f"  [DEBUG] Using fallback filename: {filename}")
        
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
Date: {self._format_date(metadata['pub_date'])}
Author: {metadata['author']}
{'='*70}

"""
            output_text = header + output_text
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_text)
        
        print(f"✓ Saved: {output_path.name}")
        
        # Return mapping info for CSV output
        # trackid was already extracted at the start of this method
        mapping_info = {
            'transcript_file': ttml_path.name,
            'trackid': trackid if trackid else ttml_path.stem,
            'output_file': output_path.name,
            'matched': metadata is not None
        }
        
        if metadata:
            mapping_info.update({
                'podcast_title': metadata['podcast_title'],
                'episode_title': metadata['episode_title'],
                'pub_date': self._format_date(metadata['pub_date']),
                'author': metadata['author']
            })
        else:
            mapping_info.update({
                'podcast_title': '',
                'episode_title': '',
                'pub_date': '',
                'author': ''
            })
        
        return mapping_info
    
    def extract_all(self):
        """Extract all transcripts with metadata and generate logs."""
        ttml_files = self.find_ttml_files()
        
        if not ttml_files:
            print("No TTML files found.")
            return
        
        # Store all transcript file information
        self.transcript_files = ttml_files
        
        print(f"Found {len(ttml_files)} transcript file(s)\n")
        
        # Process all files and collect mapping information
        mapping_results = []
        extracted = 0
        
        for ttml_path in ttml_files:
            result = self.extract_single_file(ttml_path)
            if result:
                extracted += 1
                mapping_results.append(result)
        
        print(f"\n✓ Extraction complete! {extracted} files saved to: {self.output_dir.absolute()}")
        
        # Generate CSV with successfully mapped entries
        self._write_mapping_csv(mapping_results)
        
        # Generate unmatched logs
        self._write_unmatched_logs()
        
        # Write failed parsing log
        self._write_failed_parsing_log()
        
        # Print summary
        self._print_summary(mapping_results)
    
    def _write_mapping_csv(self, mapping_results):
        """Write CSV file with all transcript-to-episode mappings.
        
        Args:
            mapping_results: List of mapping info dictionaries
        """
        if not mapping_results:
            return
        
        try:
            with open(self.mapping_csv, 'w', newline='', encoding='utf-8') as f:
                fieldnames = [
                    'transcript_file', 'trackid', 'output_file', 'matched',
                    'podcast_title', 'episode_title', 'pub_date', 'author'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                writer.writeheader()
                for result in mapping_results:
                    writer.writerow(result)
            
            print(f"✓ Mapping CSV saved to: {self.mapping_csv.name}")
        except Exception as e:
            print(f"Warning: Could not write mapping CSV: {e}")
    
    def _write_unmatched_logs(self):
        """Write log files for unmatched transcript files and database entries."""
        # Find unmatched transcript files (those without metadata match)
        # Store both matched and unmatched for later use
        unmatched_transcripts = []
        transcript_trackids = set()
        
        for ttml_path in self.transcript_files:
            trackid, success = self._extract_trackid_from_filename(ttml_path)
            if trackid:
                transcript_trackids.add(trackid)
                if trackid not in self.matched_transcripts:
                    unmatched_transcripts.append({
                        'file': ttml_path.name,
                        'trackid': trackid,
                        'path': str(ttml_path)
                    })
        
        # Store counts for later use in summary
        self.unmatched_transcript_count = len(unmatched_transcripts)
        
        # Write unmatched transcript files log
        if unmatched_transcripts:
            try:
                with open(self.unmatched_transcript_log, 'w', encoding='utf-8') as f:
                    f.write("Transcript Files Without Database Matches\n")
                    f.write("=" * 70 + "\n\n")
                    f.write(f"Total unmatched: {len(unmatched_transcripts)}\n\n")
                    
                    for item in unmatched_transcripts:
                        f.write(f"File: {item['file']}\n")
                        f.write(f"Trackid: {item['trackid']}\n")
                        f.write(f"Path: {item['path']}\n")
                        f.write("-" * 70 + "\n")
                
                print(f"✓ Unmatched transcripts log: {self.unmatched_transcript_log.name} ({len(unmatched_transcripts)} entries)")
            except Exception as e:
                print(f"Warning: Could not write unmatched transcripts log: {e}")
        
        # Find database trackids without transcript files (using pre-calculated set)
        unmatched_db_entries = self.db_trackids - transcript_trackids
        self.unmatched_db_count = len(unmatched_db_entries)
        
        # Write unmatched database entries log
        if unmatched_db_entries:
            try:
                with open(self.unmatched_db_log, 'w', encoding='utf-8') as f:
                    f.write("Database Entries Without Transcript Files\n")
                    f.write("=" * 70 + "\n\n")
                    f.write(f"Total unmatched: {len(unmatched_db_entries)}\n\n")
                    f.write("These episode GUIDs are in the database but no corresponding transcript file was found.\n")
                    f.write("This may be normal if:\n")
                    f.write("  - The episode doesn't have a transcript available\n")
                    f.write("  - The episode hasn't been downloaded yet\n")
                    f.write("  - The transcript hasn't been cached yet\n\n")
                    
                    for guid in sorted(unmatched_db_entries):
                        f.write(f"{guid}\n")
                
                print(f"✓ Unmatched DB entries log: {self.unmatched_db_log.name} ({len(unmatched_db_entries)} entries)")
            except Exception as e:
                print(f"Warning: Could not write unmatched DB entries log: {e}")
    
    def _write_failed_parsing_log(self):
        """Write log file for transcript files that failed trackid parsing."""
        if not self.failed_parsing:
            return
        
        try:
            with open(self.failed_parsing_log, 'w', encoding='utf-8') as f:
                f.write("Transcript Files That Failed Trackid Parsing\n")
                f.write("=" * 70 + "\n\n")
                f.write(f"Total failed: {len(self.failed_parsing)}\n\n")
                f.write("These files could not be parsed to extract a trackid.\n")
                f.write("Check the filename patterns and update the parsing logic if needed.\n\n")
                
                for filepath in self.failed_parsing:
                    f.write(f"{filepath}\n")
            
            print(f"✓ Failed parsing log: {self.failed_parsing_log.name} ({len(self.failed_parsing)} entries)")
        except Exception as e:
            print(f"Warning: Could not write failed parsing log: {e}")
    
    def _print_summary(self, mapping_results):
        """Print summary of the extraction and mapping process.
        
        Args:
            mapping_results: List of mapping info dictionaries
        """
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        
        total_files = len(self.transcript_files)
        matched = sum(1 for r in mapping_results if r['matched'])
        unmatched = len(mapping_results) - matched
        
        print(f"Total transcript files found: {total_files}")
        print(f"Successfully mapped to episodes: {matched}")
        print(f"Could not map to episodes: {unmatched}")
        print(f"Failed trackid parsing: {len(self.failed_parsing)}")
        
        # Calculate database entries without transcripts
        # Use matched_transcripts which only includes successfully matched trackids
        unmatched_db_count = len(self.db_trackids - self.matched_transcripts)
        print(f"Database entries without transcripts: {unmatched_db_count}")
        
        print("\nOutput files:")
        print(f"  - Transcripts: {self.output_dir.absolute()}")
        print(f"  - Mapping CSV: {self.mapping_csv.name}")
        if self.failed_parsing:
            print(f"  - Failed parsing log: {self.failed_parsing_log.name}")
        
        # Use pre-calculated counts from _write_unmatched_logs
        if hasattr(self, 'unmatched_transcript_count') and self.unmatched_transcript_count > 0:
            print(f"  - Unmatched transcripts log: {self.unmatched_transcript_log.name}")
        
        # Only mention the DB log if it was actually created (i.e., there are unmatched entries)
        if hasattr(self, 'unmatched_db_count') and self.unmatched_db_count > 0:
            print(f"  - Unmatched DB entries log: {self.unmatched_db_log.name}")
        
        print("\n" + "=" * 70)


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
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output to trace metadata extraction'
    )
    
    args = parser.parse_args()
    
    # Create extractor
    extractor = MetadataExtractor(
        output_dir=args.output,
        include_timestamps=args.timestamps,
        debug=args.debug
    )
    
    # Extract transcripts
    extractor.extract_all()


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Search across podcast transcript files."""

import argparse
import os
import sys
from typing import List, Tuple

DEFAULT_TRANSCRIPT_DIR = "transcripts"


def load_file(path: str) -> List[str]:
    """Load a text file and return its lines."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.readlines()
    except UnicodeDecodeError:
        # Fallback if encoding is unusual
        with open(path, "r", errors="replace") as f:
            return f.readlines()


def find_matches_in_lines(
    lines: List[str],
    query: str,
    context: int,
    filename: str,
) -> List[Tuple[str, int, List[str]]]:
    """Find all matches in lines and return with context.
    
    Returns:
        List of (filename, line_number, context_block_lines)
    """
    results = []
    q_lower = query.lower()

    for i, line in enumerate(lines):
        if q_lower in line.lower():
            start = max(0, i - context)
            end = min(len(lines), i + context + 1)
            block = lines[start:end]
            results.append((filename, i + 1, block))
    return results


def search_transcripts(
    base_dir: str,
    query: str,
    context: int,
    limit: int,
) -> List[Tuple[str, int, List[str]]]:
    """Search for query across all transcript files.
    
    Args:
        base_dir: Directory containing transcript .txt files
        query: Search string (case-insensitive)
        context: Number of lines before/after to include
        limit: Maximum number of results (0 for unlimited)
    
    Returns:
        List of (filename, line_number, context_lines) tuples
    """
    all_results: List[Tuple[str, int, List[str]]] = []

    if not os.path.isdir(base_dir):
        print(f"Error: transcripts directory not found at: {base_dir}")
        print("Run extract_transcripts.py first, or adjust --dir.")
        sys.exit(1)

    for root, _, files in os.walk(base_dir):
        for name in files:
            if not name.lower().endswith(".txt"):
                continue
            path = os.path.join(root, name)
            lines = load_file(path)
            matches = find_matches_in_lines(lines, query, context, path)
            all_results.extend(matches)
            if limit and len(all_results) >= limit:
                return all_results[:limit]

    return all_results[:limit] if limit else all_results


def print_results(results: List[Tuple[str, int, List[str]]], query: str, context: int):
    """Print search results in a readable format."""
    if not results:
        print(f'No matches found for: "{query}"')
        return

    print(f'Found {len(results)} match(es) for: "{query}"\n')

    separator = "-" * 80
    for idx, (filename, line_num, block) in enumerate(results, 1):
        rel_path = os.path.relpath(filename)
        print(separator)
        print(f"[{idx}] File: {rel_path}")
        print(f"    Line: {line_num}")
        print(f"    Context (±{context} lines):")
        print()

        for line in block:
            # Trim trailing newline for nicer printing
            print("    " + line.rstrip("\n"))

        print()  # blank line after block

    print(separator)


def main():
    parser = argparse.ArgumentParser(
        description="Search text across podcast transcripts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  Basic search:
    python3 search_transcripts.py "artificial intelligence"
  
  With more context:
    python3 search_transcripts.py "machine learning" --context 5
  
  Limit results:
    python3 search_transcripts.py "python" --limit 10
  
  Search in different directory:
    python3 search_transcripts.py "blockchain" --dir my_transcripts
        """
    )
    parser.add_argument(
        "query",
        type=str,
        help="Search query (case-insensitive substring match)",
    )
    parser.add_argument(
        "--dir",
        type=str,
        default=DEFAULT_TRANSCRIPT_DIR,
        help=f"Directory containing .txt transcripts (default: {DEFAULT_TRANSCRIPT_DIR})",
    )
    parser.add_argument(
        "--context",
        type=int,
        default=2,
        help="Number of context lines before/after each match (default: 2)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of matches to show (0 = no limit, default: 50)",
    )

    args = parser.parse_args()

    results = search_transcripts(
        base_dir=args.dir,
        query=args.query,
        context=args.context,
        limit=args.limit,
    )
    print_results(results, args.query, args.context)


if __name__ == "__main__":
    main()

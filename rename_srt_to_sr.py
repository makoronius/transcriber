#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rename SRT files without language code to Serbian (.sr.srt)

This script finds all .srt files that don't have a language code
(e.g., video.srt) and renames them to include 'sr' language code
(e.g., video.sr.srt)

Usage:
    python rename_srt_to_sr.py [directory]

    If no directory is specified, uses the DOWNLOADED_FILES_DIR from config.yaml
"""

import os
import sys
import re
from pathlib import Path
import yaml

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def load_config():
    """Load configuration from config.yaml"""
    config_path = Path(__file__).parent / 'config.yaml'
    if not config_path.exists():
        print(f"Error: config.yaml not found at {config_path}")
        return None

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    return config


def is_language_coded_srt(filename):
    """
    Check if an SRT file already has a language code.
    Returns True if it has a language code like .en.srt, .sr.srt, etc.
    Returns False if it's just .srt
    """
    # Pattern: filename ends with .XX.srt where XX is 2-3 letter language code
    pattern = r'\.[a-z]{2,3}\.srt$'
    return bool(re.search(pattern, filename.lower()))


def rename_srt_files(directory, dry_run=False):
    """
    Rename all .srt files without language code to .sr.srt

    Args:
        directory: Directory to search for SRT files
        dry_run: If True, only print what would be renamed without actually renaming

    Returns:
        Tuple of (renamed_count, error_count)
    """
    directory = Path(directory)

    if not directory.exists():
        print(f"Error: Directory not found: {directory}")
        return 0, 0

    renamed_count = 0
    error_count = 0

    # Find all .srt files recursively
    srt_files = list(directory.rglob('*.srt'))

    print(f"Found {len(srt_files)} SRT files in {directory}")
    print()

    for srt_file in srt_files:
        # Skip if already has language code
        if is_language_coded_srt(srt_file.name):
            continue

        # Generate new filename with .sr.srt
        old_name = srt_file.name
        new_name = old_name[:-4] + '.sr.srt'  # Remove .srt and add .sr.srt
        new_path = srt_file.parent / new_name

        # Check if target file already exists
        if new_path.exists():
            print(f"SKIP: {old_name}")
            print(f"    Target already exists: {new_name}")
            print()
            error_count += 1
            continue

        if dry_run:
            print(f"WOULD RENAME:")
            print(f"    From: {old_name}")
            print(f"    To:   {new_name}")
            print(f"    Path: {srt_file.parent}")
            print()
            renamed_count += 1
        else:
            try:
                srt_file.rename(new_path)
                print(f"RENAMED:")
                print(f"    From: {old_name}")
                print(f"    To:   {new_name}")
                print(f"    Path: {srt_file.parent}")
                print()
                renamed_count += 1
            except Exception as e:
                print(f"ERROR renaming {old_name}:")
                print(f"    {str(e)}")
                print()
                error_count += 1

    return renamed_count, error_count


def main():
    print("=" * 70)
    print("SRT Language Code Renamer - Add 'sr' to files without language code")
    print("=" * 70)
    print()

    # Get directory from command line or config
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        config = load_config()
        if not config:
            print("Please specify a directory as argument:")
            print("    python rename_srt_to_sr.py <directory>")
            return

        directory = config.get('downloaded_files_dir', './downloads')

    print(f"Scanning directory: {directory}")
    print()

    # First do a dry run to show what would be renamed
    print("=" * 70)
    print("DRY RUN - Showing what will be renamed")
    print("=" * 70)
    print()

    renamed_count, error_count = rename_srt_files(directory, dry_run=True)

    if renamed_count == 0 and error_count == 0:
        print("OK: No SRT files need renaming (all already have language codes)")
        return

    print("=" * 70)
    print(f"Summary: {renamed_count} files would be renamed")
    if error_count > 0:
        print(f"         {error_count} files would be skipped (errors)")
    print("=" * 70)
    print()

    # Ask for confirmation
    response = input("Proceed with renaming? (yes/no): ").strip().lower()

    if response not in ['yes', 'y']:
        print("CANCELLED - no files were renamed")
        return

    print()
    print("=" * 70)
    print("RENAMING FILES")
    print("=" * 70)
    print()

    # Actually rename the files
    renamed_count, error_count = rename_srt_files(directory, dry_run=False)

    print("=" * 70)
    print("COMPLETED")
    print("=" * 70)
    print(f"Successfully renamed: {renamed_count} files")
    if error_count > 0:
        print(f"Errors/Skipped: {error_count} files")
    print()


if __name__ == '__main__':
    main()

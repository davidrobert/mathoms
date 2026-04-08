#!/usr/bin/env python3
"""
File routing script for Financas Familia pipeline.
Routes files from inbox/ to their correct destinations.
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

# Define base paths
BASE_DIR = Path("/sessions/sharp-cool-shannon/mnt/Financas Familia/financas-familia")
INBOX_DIR = BASE_DIR / "inbox"
INBOX_PROCESSED_DIR = BASE_DIR / "inbox_processed" / "20260408"
DATA_DIR = BASE_DIR / "data"
MEMBERS_DIR = BASE_DIR / "members"

# Ensure directories exist
INBOX_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Routing categories
MEMBERS_FILES = [
    "david_curriculo",
    "mariana_curriculo",
    "mariana_holerite"
]

# Special exceptions
REAL_ESTATE_FILES = ["dados_imoveis"]
INCOME_TAX_BR_FILES = ["receitafederal_irpf"]

def get_destination(filename):
    """
    Determine the destination directory for a file based on routing rules.
    Returns (destination_path, category_name)
    """
    # Check if it's a members file
    for member_pattern in MEMBERS_FILES:
        if filename.startswith(member_pattern):
            return MEMBERS_DIR, "members"

    # Check for real estate exception
    if filename.startswith("dados_imoveis"):
        return DATA_DIR / "real_estate", "real_estate"

    # Check for income tax BR exception
    if filename.startswith("receitafederal_irpf"):
        return DATA_DIR / "income_tax_br", "income_tax_br"

    # Default to financial statements
    return DATA_DIR / "financial_statements", "financial_statements"

def copy_file(source, destination):
    """
    Copy file to destination, creating parent directories if needed.
    Returns True if successful, False otherwise.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(source, destination)
        return True
    except Exception as e:
        print(f"  Error copying to destination: {e}")
        return False

def move_file(source, destination):
    """
    Move file using shutil.move with fallback to copy + delete.
    Returns True if successful, False otherwise.
    """
    try:
        shutil.move(str(source), str(destination))
        return True
    except Exception as e:
        print(f"  Move failed, attempting copy+delete: {e}")
        try:
            if copy_file(source, destination):
                source.unlink()
                return True
        except Exception as e2:
            print(f"  Copy+delete also failed: {e2}")
        return False

def main():
    """Main routing logic."""
    print("Starting file routing process...")
    print(f"Inbox: {INBOX_DIR}")
    print(f"Processed dir: {INBOX_PROCESSED_DIR}")
    print()

    # Get all files in inbox
    files = sorted([f for f in INBOX_DIR.iterdir() if f.is_file()])

    if not files:
        print("No files found in inbox.")
        return

    print(f"Found {len(files)} files to process\n")

    # Track statistics
    stats = {
        "members": 0,
        "real_estate": 0,
        "income_tax_br": 0,
        "financial_statements": 0,
        "failed": 0
    }

    failed_files = []

    # Process each file
    for source_file in files:
        filename = source_file.name
        dest_dir, category = get_destination(filename)

        try:
            # Step 1: Copy to inbox_processed
            processed_dest = INBOX_PROCESSED_DIR / filename
            if not copy_file(source_file, processed_dest):
                print(f"✗ {filename} - Failed to copy to inbox_processed")
                stats["failed"] += 1
                failed_files.append(filename)
                continue

            # Step 2: Move to final destination
            final_dest = dest_dir / filename
            if not move_file(source_file, final_dest):
                print(f"✗ {filename} - Failed to move to {category}")
                stats["failed"] += 1
                failed_files.append(filename)
                continue

            stats[category] += 1
            print(f"✓ {filename} → {category}")

        except Exception as e:
            print(f"✗ {filename} - Unexpected error: {e}")
            stats["failed"] += 1
            failed_files.append(filename)

    # Print summary
    print("\n" + "="*70)
    print("ROUTING SUMMARY")
    print("="*70)
    print(f"Members:              {stats['members']:3d} files")
    print(f"Real Estate:          {stats['real_estate']:3d} files")
    print(f"Income Tax (BR):      {stats['income_tax_br']:3d} files")
    print(f"Financial Statements: {stats['financial_statements']:3d} files")
    print(f"Failed:               {stats['failed']:3d} files")
    print("-"*70)
    total_successful = sum(stats.values()) - stats["failed"]
    print(f"Total Processed:      {total_successful:3d} files")
    print(f"Total in Inbox:       {len(files):3d} files")
    print("="*70)

    if failed_files:
        print("\nFailed files:")
        for f in failed_files:
            print(f"  - {f}")

    return total_successful == len(files)

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

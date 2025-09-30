#!/usr/bin/env python3
"""
Bulk Knowledge Base Upload Script

Usage:
    python scripts/upload_knowledge.py --tenant demo --api-key YOUR_API_KEY --file docs.txt
    python scripts/upload_knowledge.py --tenant demo --api-key YOUR_API_KEY --dir ./knowledge_docs/

Supports:
    - Single file upload (.txt, .md, .json)
    - Directory bulk upload
    - JSON files with structured documents
    - Progress tracking
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Dict
import requests


def print_success(text):
    """Print success message."""
    print(f"✓ {text}")


def print_error(text):
    """Print error message."""
    print(f"✗ {text}")


def print_info(text):
    """Print info message."""
    print(f"ℹ {text}")


def upload_document(api_url: str, tenant: str, api_key: str, title: str, content: str, metadata: Dict = None) -> bool:
    """
    Upload a single document to the knowledge base.

    Args:
        api_url: API base URL
        tenant: Tenant slug
        api_key: API key for authentication
        title: Document title
        content: Document content
        metadata: Optional metadata dictionary

    Returns:
        True if upload successful, False otherwise
    """
    url = f"{api_url}/{tenant}/knowledge"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key
    }

    payload = {
        "title": title,
        "content": content,
        "metadata": metadata or {}
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)

        if response.status_code == 200:
            data = response.json()
            print_success(f"Uploaded: {title} (ID: {data['id']})")
            return True
        else:
            print_error(f"Failed to upload {title}: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print_error(f"Error uploading {title}: {e}")
        return False


def read_file_content(file_path: Path) -> str:
    """Read file content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print_error(f"Error reading file {file_path}: {e}")
        return None


def upload_single_file(api_url: str, tenant: str, api_key: str, file_path: Path, metadata: Dict = None) -> bool:
    """
    Upload a single file to the knowledge base.

    Args:
        api_url: API base URL
        tenant: Tenant slug
        api_key: API key for authentication
        file_path: Path to file
        metadata: Optional metadata dictionary

    Returns:
        True if upload successful, False otherwise
    """
    content = read_file_content(file_path)
    if content is None:
        return False

    # Use filename (without extension) as title
    title = file_path.stem

    # Add file type to metadata
    if metadata is None:
        metadata = {}
    metadata["source_file"] = file_path.name
    metadata["file_type"] = file_path.suffix.lstrip('.')

    return upload_document(api_url, tenant, api_key, title, content, metadata)


def upload_json_file(api_url: str, tenant: str, api_key: str, file_path: Path) -> tuple:
    """
    Upload documents from a JSON file.

    Expected JSON format:
    [
        {
            "title": "Document Title",
            "content": "Document content...",
            "metadata": {"category": "faq", "tags": ["support"]}
        },
        ...
    ]

    Args:
        api_url: API base URL
        tenant: Tenant slug
        api_key: API key for authentication
        file_path: Path to JSON file

    Returns:
        Tuple of (successful_count, failed_count)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            documents = json.load(f)

        if not isinstance(documents, list):
            print_error(f"JSON file must contain an array of documents")
            return (0, 1)

        successful = 0
        failed = 0

        for i, doc in enumerate(documents):
            if not isinstance(doc, dict):
                print_error(f"Document {i+1} is not a valid object")
                failed += 1
                continue

            title = doc.get('title', f'Document {i+1}')
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})

            if not content:
                print_error(f"Document '{title}' has no content")
                failed += 1
                continue

            if upload_document(api_url, tenant, api_key, title, content, metadata):
                successful += 1
            else:
                failed += 1

        return (successful, failed)

    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON in file {file_path}: {e}")
        return (0, 1)
    except Exception as e:
        print_error(f"Error processing JSON file {file_path}: {e}")
        return (0, 1)


def upload_directory(api_url: str, tenant: str, api_key: str, dir_path: Path, metadata: Dict = None) -> tuple:
    """
    Upload all supported files from a directory.

    Args:
        api_url: API base URL
        tenant: Tenant slug
        api_key: API key for authentication
        dir_path: Path to directory
        metadata: Optional metadata dictionary to apply to all files

    Returns:
        Tuple of (successful_count, failed_count)
    """
    supported_extensions = {'.txt', '.md', '.json'}
    files = [f for f in dir_path.iterdir() if f.is_file() and f.suffix in supported_extensions]

    if not files:
        print_error(f"No supported files found in {dir_path}")
        print_info(f"Supported file types: {', '.join(supported_extensions)}")
        return (0, 0)

    print_info(f"Found {len(files)} file(s) to upload...")

    successful = 0
    failed = 0

    for file_path in files:
        if file_path.suffix == '.json':
            s, f = upload_json_file(api_url, tenant, api_key, file_path)
            successful += s
            failed += f
        else:
            if upload_single_file(api_url, tenant, api_key, file_path, metadata):
                successful += 1
            else:
                failed += 1

    return (successful, failed)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Bulk upload documents to AgentEva knowledge base",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload a single text file
  python scripts/upload_knowledge.py --tenant demo --api-key YOUR_KEY --file docs/faq.txt

  # Upload all files from a directory
  python scripts/upload_knowledge.py --tenant demo --api-key YOUR_KEY --dir ./knowledge_docs/

  # Upload with custom metadata
  python scripts/upload_knowledge.py --tenant demo --api-key YOUR_KEY --file policy.md --category policies

  # Upload JSON file with multiple documents
  python scripts/upload_knowledge.py --tenant demo --api-key YOUR_KEY --file docs.json
        """
    )

    parser.add_argument('--tenant', required=True, help='Tenant slug')
    parser.add_argument('--api-key', required=True, help='API key for authentication')
    parser.add_argument('--api-url', default='http://127.0.0.1:8000/api', help='API base URL')
    parser.add_argument('--file', type=Path, help='Path to single file to upload')
    parser.add_argument('--dir', type=Path, help='Path to directory with files to upload')
    parser.add_argument('--category', help='Category for metadata')
    parser.add_argument('--tags', help='Comma-separated tags for metadata')

    args = parser.parse_args()

    # Validate arguments
    if not args.file and not args.dir:
        print_error("Must specify either --file or --dir")
        parser.print_help()
        sys.exit(1)

    if args.file and args.dir:
        print_error("Cannot specify both --file and --dir")
        sys.exit(1)

    # Build metadata
    metadata = {}
    if args.category:
        metadata['category'] = args.category
    if args.tags:
        metadata['tags'] = [tag.strip() for tag in args.tags.split(',')]

    print_info(f"Uploading to tenant: {args.tenant}")
    print_info(f"API URL: {args.api_url}")
    print()

    # Upload
    if args.file:
        file_path = args.file
        if not file_path.exists():
            print_error(f"File not found: {file_path}")
            sys.exit(1)

        if file_path.suffix == '.json':
            successful, failed = upload_json_file(args.api_url, args.tenant, args.api_key, file_path)
        else:
            successful = 1 if upload_single_file(args.api_url, args.tenant, args.api_key, file_path, metadata) else 0
            failed = 0 if successful else 1
    else:
        dir_path = args.dir
        if not dir_path.exists() or not dir_path.is_dir():
            print_error(f"Directory not found: {dir_path}")
            sys.exit(1)

        successful, failed = upload_directory(args.api_url, args.tenant, args.api_key, dir_path, metadata)

    # Summary
    print()
    print("=" * 60)
    print(f"Upload Summary:")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
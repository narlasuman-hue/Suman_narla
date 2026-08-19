"""Command-line interface for the file search utility."""

import argparse
import sys
from pathlib import Path
from file_search import search_and_save


def main():
    """Command-line entry point for file search."""
    parser = argparse.ArgumentParser(
        description="Search for files and content, write results to a file"
    )

    parser.add_argument(
        "query",
        help="What to search for (filename pattern, content, or extension)",
    )

    parser.add_argument(
        "-t",
        "--type",
        choices=["filename", "content", "extension"],
        default="filename",
        help="Type of search (default: filename)",
    )

    parser.add_argument(
        "-o",
        "--output",
        default="search_results.txt",
        help="Output file path (default: search_results.txt)",
    )

    parser.add_argument(
        "-r",
        "--root",
        default=".",
        help="Root directory to search from (default: current directory)",
    )

    parser.add_argument(
        "-p",
        "--pattern",
        help="File pattern filter (used with content search)",
    )

    parser.add_argument(
        "-cs",
        "--case-sensitive",
        action="store_true",
        help="Case-sensitive search (only for content search)",
    )

    args = parser.parse_args()

    # Validate root directory
    if not Path(args.root).exists():
        print(f"Error: Root directory '{args.root}' does not exist", file=sys.stderr)
        sys.exit(1)

    try:
        # Prepare kwargs for specific search types
        kwargs = {}
        if args.type == "content":
            if args.pattern:
                kwargs["file_pattern"] = args.pattern
            kwargs["case_sensitive"] = args.case_sensitive

        # Perform search
        result = search_and_save(
            search_type=args.type,
            search_query=args.query,
            output_file=args.output,
            root_path=args.root,
            **kwargs,
        )

        # Display results
        print(f"✓ Search completed successfully")
        print(f"  Type: {result['search_type']}")
        print(f"  Query: {result['search_query']}")
        print(f"  Matches found: {result['total_matches']}")
        print(f"  Results saved to: {result['output_file']}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

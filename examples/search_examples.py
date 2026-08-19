"""Examples of how to use the file search utility."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from file_search import FileSearcher, SearchResultWriter, search_and_save


def example_1_search_by_filename():
    """Example 1: Search for files by filename pattern."""
    print("\n" + "=" * 60)
    print("Example 1: Search for Python files")
    print("=" * 60)

    searcher = FileSearcher(root_path=".")
    results = searcher.search_by_filename("*.py")

    print(f"Found {len(results)} Python files:")
    for result in results[:10]:  # Show first 10
        print(f"  - {result.file_path}")

    # Save to file
    output = SearchResultWriter.write_results(
        results, "search_results_py_files.txt"
    )
    print(f"\nResults saved to: {output}")


def example_2_search_by_extension():
    """Example 2: Search for files by extension."""
    print("\n" + "=" * 60)
    print("Example 2: Search for JSON files")
    print("=" * 60)

    searcher = FileSearcher(root_path=".")
    results = searcher.search_by_extension("json")

    print(f"Found {len(results)} JSON files:")
    for result in results[:10]:
        print(f"  - {result.file_path}")

    if results:
        output = SearchResultWriter.write_results(
            results, "search_results_json_files.txt"
        )
        print(f"\nResults saved to: {output}")
    else:
        print("  (None found)")


def example_3_search_content():
    """Example 3: Search for content within files."""
    print("\n" + "=" * 60)
    print("Example 3: Search for 'import' in Python files")
    print("=" * 60)

    searcher = FileSearcher(root_path=".")
    results = searcher.search_in_content(
        search_term="^import ", file_pattern="*.py", case_sensitive=False
    )

    print(f"Found {len(results)} import statements:")
    for result in results[:15]:  # Show first 15
        print(f"  {result.file_path}:{result.line_number}")
        print(f"    {result.line_content}")

    if results:
        output = SearchResultWriter.write_results(
            results, "search_results_imports.txt"
        )
        print(f"\nResults saved to: {output}")


def example_4_search_functions():
    """Example 4: Search for function definitions."""
    print("\n" + "=" * 60)
    print("Example 4: Search for function definitions")
    print("=" * 60)

    searcher = FileSearcher(root_path=".")
    results = searcher.search_in_content(
        search_term=r"^\s*def ", file_pattern="*.py", case_sensitive=True
    )

    print(f"Found {len(results)} function definitions:")
    for result in results[:20]:  # Show first 20
        print(f"  {result.file_path}:{result.line_number}")
        print(f"    {result.line_content.strip()}")

    if results:
        output = SearchResultWriter.write_results(
            results, "search_results_functions.txt"
        )
        print(f"\nResults saved to: {output}")


def example_5_convenient_api():
    """Example 5: Using the convenient search_and_save function."""
    print("\n" + "=" * 60)
    print("Example 5: Using search_and_save convenience function")
    print("=" * 60)

    # Search for all test files
    result = search_and_save(
        search_type="filename",
        search_query="test_*.py",
        output_file="search_results_tests.txt",
        root_path=".",
    )

    print(f"Search Results:")
    print(f"  Type: {result['search_type']}")
    print(f"  Query: {result['search_query']}")
    print(f"  Matches: {result['total_matches']}")
    print(f"  Output: {result['output_file']}")


def example_6_case_insensitive_search():
    """Example 6: Case-insensitive content search."""
    print("\n" + "=" * 60)
    print("Example 6: Case-insensitive search for 'TODO'")
    print("=" * 60)

    result = search_and_save(
        search_type="content",
        search_query="TODO",
        output_file="search_results_todos.txt",
        root_path=".",
        file_pattern="*.py",
        case_sensitive=False,
    )

    print(f"Found {result['total_matches']} TODO comments")
    print(f"Results saved to: {result['output_file']}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("FILE SEARCH UTILITY - USAGE EXAMPLES")
    print("=" * 60)

    try:
        example_1_search_by_filename()
        example_2_search_by_extension()
        example_3_search_content()
        example_4_search_functions()
        example_5_convenient_api()
        example_6_case_insensitive_search()

        print("\n" + "=" * 60)
        print("All examples completed!")
        print("Check the generated search_results_*.txt files for details")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\nError running examples: {e}", file=sys.stderr)
        sys.exit(1)

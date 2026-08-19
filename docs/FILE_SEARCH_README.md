# File Search Utility

A comprehensive Python utility for searching files and content within a directory, with results saved to new files.

## Features

- **Filename Search**: Find files by name patterns (wildcard support)
- **Extension Search**: Find files by file extension
- **Content Search**: Search for text patterns within files
- **Regex Support**: Use regular expressions for advanced searches
- **Case Control**: Case-sensitive or case-insensitive searches
- **Smart Filtering**: Automatically excludes common directories (.git, __pycache__, venv, etc.)
- **Result Export**: Save all results to formatted output files
- **CLI Interface**: Command-line tool for easy scripting

## Installation

The utility is included in the `src/` directory. To use it:

```bash
# Install test dependencies (optional)
pip install pytest
```

## Quick Start

### Method 1: Command-Line Interface

```bash
# Search for Python files
python -m src.search_cli "*.py"

# Search for content
python -m src.search_cli "import os" -t content -p "*.py"

# Search by extension
python -m src.search_cli json -t extension

# Specify output file
python -m src.search_cli "*.py" -o my_results.txt
```

### Method 2: Python API

```python
from src.file_search import FileSearcher, SearchResultWriter

# Initialize searcher
searcher = FileSearcher(root_path=".")

# Search by filename
results = searcher.search_by_filename("*.py")

# Save results to file
output = SearchResultWriter.write_results(results, "results.txt")
```

### Method 3: Convenience Function

```python
from src.file_search import search_and_save

result = search_and_save(
    search_type="filename",
    search_query="*.py",
    output_file="results.txt"
)

print(f"Found {result['total_matches']} matches")
print(f"Results saved to: {result['output_file']}")
```

## Usage Examples

### Example 1: Find All Python Files

```bash
python -m src.search_cli "*.py" -o python_files.txt
```

### Example 2: Find Functions in Code

```python
from src.file_search import search_and_save

result = search_and_save(
    search_type="content",
    search_query=r"^\s*def ",
    file_pattern="*.py",
    output_file="all_functions.txt"
)
```

### Example 3: Find All TODO Comments

```bash
python -m src.search_cli "TODO" -t content -p "*.py" -o todos.txt
```

### Example 4: Search Multiple File Types

```python
from src.file_search import FileSearcher

searcher = FileSearcher()

# Find all config files
results = searcher.search_by_filename("*.{json,yaml,yml,toml}")

# Find files with test in name
results = searcher.search_by_filename("*test*")
```

### Example 5: Case-Insensitive Search

```bash
python -m src.search_cli "error" -t content -p "*.py" --case-sensitive
```

## API Reference

### FileSearcher

Main class for performing searches.

#### Methods

- **`search_by_filename(pattern: str) -> List[SearchResult]`**
  - Search for files matching a filename pattern
  - Supports wildcards: `*` (any characters), `?` (single character)
  - Example: `"*.py"`, `"test_*.py"`, `"config.json"`

- **`search_by_extension(extension: str) -> List[SearchResult]`**
  - Search for files with a specific extension
  - Automatically adds dot prefix if not provided
  - Example: `"py"`, `".json"`, `"yml"`

- **`search_in_content(search_term: str, file_pattern: str = "*", case_sensitive: bool = False) -> List[SearchResult]`**
  - Search for content within files
  - `search_term` can be a regex pattern
  - `file_pattern` filters which files to search
  - Example: `"import ", "^class ", r"def \w+\("`

#### Constructor

```python
searcher = FileSearcher(
    root_path=".",                    # Root directory to search
    exclude_dirs=[".git", "__pycache__"]  # Directories to skip
)
```

### SearchResult

Represents a single search result.

```python
@dataclass
class SearchResult:
    file_path: str              # Path to the file
    line_number: Optional[int]  # Line number (content searches)
    line_content: Optional[str] # Content of the line
    match_type: str             # "filename" or "content"
```

### SearchResultWriter

Utility for writing results to files.

#### Methods

- **`write_results(results: List[SearchResult], output_file: str, include_header: bool = True, include_timestamp: bool = True) -> str`**
  - Write search results to a file
  - Returns the absolute path to the created file

### search_and_save() Function

Convenience function combining search and save operations.

```python
result = search_and_save(
    search_type: str,      # "filename", "content", or "extension"
    search_query: str,     # What to search for
    output_file: str = "search_results.txt",  # Output file
    root_path: str = ".",  # Root directory
    **kwargs               # Additional arguments
)

# Returns a dictionary with:
# {
#     'search_type': str,
#     'search_query': str,
#     'total_matches': int,
#     'output_file': str,
#     'results': List[SearchResult]
# }
```

## Output Format

Results are saved to files in the following format:

```
================================================================================
SEARCH RESULTS
Generated: 2026-08-19 10:30:45
Total matches: 15
================================================================================

[FILE] src/module.py
[FILE] tests/test_module.py
[FILE] examples/example.py
[src/config.py:42] import sys
[src/config.py:43] import os
[src/module.py:10] def hello():
...
```

## Advanced Patterns

### Regular Expressions in Content Search

```python
# Find all function definitions
searcher.search_in_content(r"^\s*def \w+\(", "*.py")

# Find all class definitions
searcher.search_in_content(r"^\s*class \w+", "*.py")

# Find lines with TODO or FIXME
searcher.search_in_content(r"(TODO|FIXME)", "*.py")

# Find import statements
searcher.search_in_content(r"^(import|from) ", "*.py")

# Find potential security issues
searcher.search_in_content(r"eval\(|exec\(|pickle\.load", "*.py")
```

### Complex File Patterns

```python
# Find all hidden files
searcher.search_by_filename(".*")

# Find backup files
searcher.search_by_filename("*.bak")

# Find test files
searcher.search_by_filename("test_*.py")

# Find multiple extensions
for ext in ["py", "js", "ts"]:
    results = searcher.search_by_extension(ext)
```

## Running Tests

```bash
# Run all tests
pytest tests/test_file_search.py

# Run specific test
pytest tests/test_file_search.py::TestFileSearcher::test_search_by_filename

# Run with verbose output
pytest tests/test_file_search.py -v

# Run with coverage
pytest tests/test_file_search.py --cov=src
```

## Running Examples

```bash
python examples/search_examples.py
```

This will execute all examples and create several `search_results_*.txt` files.

## Performance Notes

- First run may take a moment as the entire directory tree is traversed
- Excluded directories (`.git`, `__pycache__`, etc.) are automatically skipped
- Large binary files are handled gracefully (with utf-8 errors ignored)
- Permission errors on specific files are caught and skipped

## Customization

### Custom Exclude Directories

```python
searcher = FileSearcher(
    root_path=".",
    exclude_dirs=[".git", ".venv", "node_modules", ".mypy_cache"]
)
```

### Custom Output Formatting

```python
# Create custom formatted output
results = searcher.search_by_filename("*.py")

with open("custom_output.txt", "w") as f:
    for result in results:
        f.write(f"Python file: {result.file_path}\n")
```

## Troubleshooting

### No results found

- Check that the search pattern or query is correct
- Verify the root_path is correct
- Ensure files aren't in excluded directories

### Permission errors

- These are automatically caught and logged
- Consider running with elevated permissions if needed
- Check file/directory permissions

### Memory issues with large repos

- The utility loads files into memory for content searches
- For very large binary files, use file_pattern to be selective
- Consider searching specific subdirectories

## License

Mozilla Public License 2.0 - See LICENSE file for details

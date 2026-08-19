"""File search utility for finding files and content within a repository."""

import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Pattern
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SearchResult:
    """Represents a single search result."""
    file_path: str
    line_number: Optional[int] = None
    line_content: Optional[str] = None
    match_type: str = "filename"  # 'filename' or 'content'

    def to_string(self) -> str:
        """Format result as a readable string."""
        if self.match_type == "filename":
            return f"[FILE] {self.file_path}"
        else:
            return f"[{self.file_path}:{self.line_number}] {self.line_content}"


class FileSearcher:
    """Search for files and content within directories."""

    def __init__(self, root_path: str = ".", exclude_dirs: Optional[List[str]] = None):
        """
        Initialize the FileSearcher.

        Args:
            root_path: Root directory to search from (default: current directory)
            exclude_dirs: List of directory names to skip (e.g., ['.git', '__pycache__'])
        """
        self.root_path = Path(root_path)
        self.exclude_dirs = exclude_dirs or [
            ".git",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".venv",
            "venv",
            ".env",
            "node_modules",
            ".idea",
            ".vscode",
            "dist",
            "build",
            "*.egg-info",
        ]

    def search_by_filename(self, pattern: str) -> List[SearchResult]:
        """
        Search for files matching a filename pattern.

        Args:
            pattern: Filename pattern (can use wildcards like *.py)

        Returns:
            List of SearchResult objects for matching files
        """
        results = []
        regex = self._pattern_to_regex(pattern)

        try:
            for file_path in self.root_path.rglob("*"):
                if file_path.is_file() and self._should_process(file_path):
                    if regex.search(file_path.name):
                        results.append(
                            SearchResult(
                                file_path=str(file_path.relative_to(self.root_path)),
                                match_type="filename",
                            )
                        )
        except PermissionError:
            pass

        return sorted(results, key=lambda r: r.file_path)

    def search_in_content(
        self, search_term: str, file_pattern: str = "*", case_sensitive: bool = False
    ) -> List[SearchResult]:
        """
        Search for a term within file contents.

        Args:
            search_term: Term to search for
            file_pattern: Filter files by pattern (default: all files)
            case_sensitive: Whether search is case-sensitive

        Returns:
            List of SearchResult objects with line numbers and content
        """
        results = []
        file_regex = self._pattern_to_regex(file_pattern)
        flags = 0 if case_sensitive else re.IGNORECASE

        try:
            for file_path in self.root_path.rglob("*"):
                if not file_path.is_file() or not self._should_process(file_path):
                    continue

                if not file_regex.search(file_path.name):
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            if re.search(search_term, line, flags):
                                results.append(
                                    SearchResult(
                                        file_path=str(
                                            file_path.relative_to(self.root_path)
                                        ),
                                        line_number=line_num,
                                        line_content=line.rstrip(),
                                        match_type="content",
                                    )
                                )
                except (UnicodeDecodeError, PermissionError):
                    pass

        except PermissionError:
            pass

        return results

    def search_by_extension(self, extension: str) -> List[SearchResult]:
        """
        Search for files with a specific extension.

        Args:
            extension: File extension (e.g., 'py', 'txt', 'json')

        Returns:
            List of SearchResult objects for matching files
        """
        if not extension.startswith("."):
            extension = f".{extension}"
        return self.search_by_filename(f"*{extension}")

    def _should_process(self, file_path: Path) -> bool:
        """Check if a file should be processed (not in exclude list)."""
        parts = file_path.parts
        for exclude in self.exclude_dirs:
            exclude_clean = exclude.rstrip("/*")
            if exclude_clean in parts:
                return False
        return True

    @staticmethod
    def _pattern_to_regex(pattern: str) -> Pattern:
        """Convert a shell-like pattern to a regex pattern."""
        regex_pattern = pattern.replace(".", r"\.")
        regex_pattern = regex_pattern.replace("*", ".*")
        regex_pattern = regex_pattern.replace("?", ".")
        return re.compile(f"^{regex_pattern}$")


class SearchResultWriter:
    """Write search results to a file."""

    @staticmethod
    def write_results(
        results: List[SearchResult],
        output_file: str,
        include_header: bool = True,
        include_timestamp: bool = True,
    ) -> str:
        """
        Write search results to a file.

        Args:
            results: List of SearchResult objects
            output_file: Path to output file
            include_header: Whether to include a header with search info
            include_timestamp: Whether to include timestamp in header

        Returns:
            Path to the created file
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            if include_header:
                f.write("=" * 80 + "\n")
                f.write("SEARCH RESULTS\n")
                if include_timestamp:
                    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total matches: {len(results)}\n")
                f.write("=" * 80 + "\n\n")

            for result in results:
                f.write(result.to_string() + "\n")

        return str(output_path.absolute())


def search_and_save(
    search_type: str,
    search_query: str,
    output_file: str = "search_results.txt",
    root_path: str = ".",
    **kwargs,
) -> Dict:
    """
    Perform a search and save results to file.

    Args:
        search_type: Type of search ('filename', 'content', 'extension')
        search_query: What to search for
        output_file: Where to save results
        root_path: Root directory to search from
        **kwargs: Additional arguments for specific search types

    Returns:
        Dictionary with search statistics and output file path
    """
    searcher = FileSearcher(root_path=root_path)

    if search_type == "filename":
        results = searcher.search_by_filename(search_query)
    elif search_type == "content":
        case_sensitive = kwargs.get("case_sensitive", False)
        file_pattern = kwargs.get("file_pattern", "*")
        results = searcher.search_in_content(
            search_query, file_pattern=file_pattern, case_sensitive=case_sensitive
        )
    elif search_type == "extension":
        results = searcher.search_by_extension(search_query)
    else:
        raise ValueError(f"Unknown search type: {search_type}")

    output_path = SearchResultWriter.write_results(results, output_file)

    return {
        "search_type": search_type,
        "search_query": search_query,
        "total_matches": len(results),
        "output_file": output_path,
        "results": results,
    }


if __name__ == "__main__":
    # Example usage
    print("File Search Utility - Example Usage\n")

    # Search by filename
    print("1. Searching for all Python files...")
    result1 = search_and_save("filename", "*.py", output_file="search_py_files.txt")
    print(f"   Found {result1['total_matches']} Python files")
    print(f"   Results saved to: {result1['output_file']}\n")

    # Search by extension
    print("2. Searching for all JSON files...")
    result2 = search_and_save("extension", "json", output_file="search_json_files.txt")
    print(f"   Found {result2['total_matches']} JSON files")
    print(f"   Results saved to: {result2['output_file']}\n")

    # Search in content
    print("3. Searching for 'def ' in Python files...")
    result3 = search_and_save(
        "content",
        "def ",
        file_pattern="*.py",
        output_file="search_functions.txt",
    )
    print(f"   Found {result3['total_matches']} function definitions")
    print(f"   Results saved to: {result3['output_file']}\n")

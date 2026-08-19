"""File search utility module."""

from .file_search import FileSearcher, SearchResult, SearchResultWriter, search_and_save

__all__ = [
    "FileSearcher",
    "SearchResult",
    "SearchResultWriter",
    "search_and_save",
]

__version__ = "1.0.0"

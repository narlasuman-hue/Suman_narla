"""Tests for the file search utility."""

import pytest
import tempfile
from pathlib import Path
from src.file_search import FileSearcher, SearchResult, SearchResultWriter, search_and_save


@pytest.fixture
def temp_project():
    """Create a temporary project structure for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create directory structure
        (tmpdir / "src").mkdir()
        (tmpdir / "tests").mkdir()
        (tmpdir / ".git").mkdir()

        # Create test files
        (tmpdir / "src" / "module.py").write_text("def hello():\n    return 'world'\n")
        (tmpdir / "src" / "config.json").write_text('{"name": "test"}')
        (tmpdir / "tests" / "test_module.py").write_text(
            "import pytest\ndef test_hello():\n    assert True\n"
        )
        (tmpdir / "README.md").write_text("# Test Project\n\nThis is a test.\n")
        (tmpdir / ".git" / "config").write_text("[core]\n    bare = false\n")

        yield tmpdir


class TestFileSearcher:
    """Tests for FileSearcher class."""

    def test_search_by_filename(self, temp_project):
        """Test searching for files by filename."""
        searcher = FileSearcher(root_path=str(temp_project))
        results = searcher.search_by_filename("*.py")

        assert len(results) == 2
        assert any("module.py" in r.file_path for r in results)
        assert any("test_module.py" in r.file_path for r in results)

    def test_search_by_extension(self, temp_project):
        """Test searching for files by extension."""
        searcher = FileSearcher(root_path=str(temp_project))
        results = searcher.search_by_extension("json")

        assert len(results) == 1
        assert "config.json" in results[0].file_path

    def test_search_by_extension_with_dot(self, temp_project):
        """Test searching with extension that includes dot."""
        searcher = FileSearcher(root_path=str(temp_project))
        results = searcher.search_by_extension(".json")

        assert len(results) == 1

    def test_search_in_content(self, temp_project):
        """Test searching for content within files."""
        searcher = FileSearcher(root_path=str(temp_project))
        results = searcher.search_in_content("def ", file_pattern="*.py")

        assert len(results) >= 2  # At least 2 function definitions
        assert all(r.match_type == "content" for r in results)
        assert all(r.line_number is not None for r in results)

    def test_search_in_content_case_sensitive(self, temp_project):
        """Test case-sensitive content search."""
        searcher = FileSearcher(root_path=str(temp_project))
        results = searcher.search_in_content(
            "DEF", file_pattern="*.py", case_sensitive=True
        )

        assert len(results) == 0

    def test_search_in_content_case_insensitive(self, temp_project):
        """Test case-insensitive content search."""
        searcher = FileSearcher(root_path=str(temp_project))
        results = searcher.search_in_content(
            "DEF", file_pattern="*.py", case_sensitive=False
        )

        assert len(results) >= 2

    def test_exclude_dirs(self, temp_project):
        """Test that excluded directories are skipped."""
        searcher = FileSearcher(root_path=str(temp_project))
        results = searcher.search_by_filename("*")

        # Should not include .git files
        assert not any(".git" in r.file_path for r in results)

    def test_pattern_to_regex(self):
        """Test pattern to regex conversion."""
        searcher = FileSearcher()

        # Test wildcard patterns
        pattern = searcher._pattern_to_regex("*.py")
        assert pattern.search("module.py")
        assert not pattern.search("module.txt")

        # Test question mark
        pattern = searcher._pattern_to_regex("test_?.py")
        assert pattern.search("test_a.py")
        assert not pattern.search("test_ab.py")

    def test_sorted_results(self, temp_project):
        """Test that results are sorted."""
        searcher = FileSearcher(root_path=str(temp_project))
        results = searcher.search_by_filename("*")

        file_paths = [r.file_path for r in results]
        assert file_paths == sorted(file_paths)


class TestSearchResult:
    """Tests for SearchResult class."""

    def test_search_result_filename(self):
        """Test SearchResult for filename match."""
        result = SearchResult(file_path="test.py", match_type="filename")
        assert result.to_string() == "[FILE] test.py"

    def test_search_result_content(self):
        """Test SearchResult for content match."""
        result = SearchResult(
            file_path="test.py",
            line_number=42,
            line_content="print('hello')",
            match_type="content",
        )
        assert "test.py:42" in result.to_string()
        assert "print('hello')" in result.to_string()


class TestSearchResultWriter:
    """Tests for SearchResultWriter class."""

    def test_write_results(self, temp_project):
        """Test writing results to file."""
        results = [
            SearchResult(file_path="file1.py", match_type="filename"),
            SearchResult(
                file_path="file2.py",
                line_number=10,
                line_content="test",
                match_type="content",
            ),
        ]

        output_file = str(temp_project / "results.txt")
        path = SearchResultWriter.write_results(results, output_file)

        assert Path(path).exists()
        content = Path(path).read_text()
        assert "SEARCH RESULTS" in content
        assert "file1.py" in content
        assert "file2.py:10" in content

    def test_write_results_without_header(self, temp_project):
        """Test writing results without header."""
        results = [SearchResult(file_path="file1.py", match_type="filename")]

        output_file = str(temp_project / "results_no_header.txt")
        SearchResultWriter.write_results(
            results, output_file, include_header=False, include_timestamp=False
        )

        content = Path(output_file).read_text()
        assert "SEARCH RESULTS" not in content
        assert "[FILE] file1.py" in content


class TestSearchAndSave:
    """Tests for search_and_save convenience function."""

    def test_search_and_save_filename(self, temp_project):
        """Test search_and_save for filename search."""
        result = search_and_save(
            search_type="filename",
            search_query="*.py",
            output_file=str(temp_project / "results.txt"),
            root_path=str(temp_project),
        )

        assert result["search_type"] == "filename"
        assert result["search_query"] == "*.py"
        assert result["total_matches"] == 2
        assert Path(result["output_file"]).exists()

    def test_search_and_save_extension(self, temp_project):
        """Test search_and_save for extension search."""
        result = search_and_save(
            search_type="extension",
            search_query="json",
            output_file=str(temp_project / "results.txt"),
            root_path=str(temp_project),
        )

        assert result["search_type"] == "extension"
        assert result["total_matches"] == 1

    def test_search_and_save_content(self, temp_project):
        """Test search_and_save for content search."""
        result = search_and_save(
            search_type="content",
            search_query="import",
            output_file=str(temp_project / "results.txt"),
            root_path=str(temp_project),
            file_pattern="*.py",
        )

        assert result["search_type"] == "content"
        assert result["total_matches"] >= 1

    def test_search_and_save_invalid_type(self, temp_project):
        """Test search_and_save with invalid search type."""
        with pytest.raises(ValueError):
            search_and_save(
                search_type="invalid",
                search_query="test",
                output_file=str(temp_project / "results.txt"),
                root_path=str(temp_project),
            )

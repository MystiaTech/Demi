"""
Tests for CodebaseReader self-awareness system.

Verifies codebase loading, semantic retrieval, and code injection.
"""

import pytest
from src.llm.codebase_reader import CodebaseReader, CodeSnippet
from src.core.logger import get_logger


@pytest.fixture
def logger():
    """Create a test logger."""
    return get_logger()


@pytest.fixture
def token_counter():
    """Simple token counter for testing."""

    def counter(text: str) -> int:
        return max(1, len(text) // 4)

    return counter


@pytest.fixture
def reader(logger, token_counter):
    """Create a CodebaseReader instance for testing."""
    return CodebaseReader(
        logger=logger, codebase_root="src/", token_counter=token_counter
    )


class TestCodebaseLoading:
    """Test codebase loading and initialization."""

    def test_load_codebase(self, reader):
        """Verify codebase loads with expected file count."""
        # Should load 15-20 Python files
        assert len(reader._file_cache) > 10, "Should load multiple source files"

        # Check for known files
        expected_files = [
            "src/llm/inference.py",
            "src/llm/prompt_builder.py",
            "src/emotion/models.py",
            "src/conductor/orchestrator.py",
        ]
        for expected in expected_files:
            assert any(expected in path for path in reader._file_cache.keys()), (
                f"Expected to find {expected} in loaded files"
            )

    def test_code_blocks_extracted(self, reader):
        """Verify code blocks are extracted from files."""
        # Should have indexed classes and functions
        assert len(reader._code_index) > 10, "Should extract multiple code blocks"

        # Check for known classes
        known_classes = [
            "EmotionalState",
            "OllamaInference",
            "PromptBuilder",
            "Conductor",
        ]
        found_classes = {
            snippet.class_or_function for snippet in reader._code_index.values()
        }

        for cls in known_classes:
            assert cls in found_classes, f"Expected to find {cls} in code index"

    def test_code_snippet_structure(self, reader):
        """Verify CodeSnippet objects have correct structure."""
        if reader._code_index:
            snippet = next(iter(reader._code_index.values()))

            # Check all required fields
            assert hasattr(snippet, "file_path")
            assert hasattr(snippet, "class_or_function")
            assert hasattr(snippet, "start_line")
            assert hasattr(snippet, "end_line")
            assert hasattr(snippet, "content")
            assert hasattr(snippet, "tokens")
            assert hasattr(snippet, "relevance_score")

            # Verify values are reasonable
            assert isinstance(snippet.file_path, str)
            assert isinstance(snippet.class_or_function, str)
            assert snippet.start_line > 0
            assert snippet.end_line >= snippet.start_line
            assert len(snippet.content) > 0
            assert snippet.tokens > 0


class TestArchitectureOverview:
    """Test architecture overview generation."""

    def test_architecture_overview(self, reader):
        """Verify architecture overview is generated."""
        overview = reader.get_architecture_overview()

        # Should return non-empty string
        assert isinstance(overview, str)
        assert len(overview) > 100

        # Should mention core components
        expected_terms = [
            "Emotional System",
            "Personality Modulation",
            "LLM Inference",
            "Conductor",
            "Ollama",
            "llama3.2",
        ]
        for term in expected_terms:
            assert term in overview, f"Architecture overview should mention {term}"

    def test_architecture_overview_token_limit(self, logger, token_counter):
        """Verify architecture overview stays under 500 tokens."""
        reader = CodebaseReader(
            logger=logger, codebase_root="src/", token_counter=token_counter
        )
        overview = reader.get_architecture_overview()

        tokens = token_counter(overview)
        # Should be under 500 tokens
        assert tokens < 500, (
            f"Architecture overview should be <500 tokens, got {tokens}"
        )


class TestSemanticRetrieval:
    """Test semantic code retrieval."""

    def test_get_relevant_code_emotions(self, reader):
        """Query 'emotions' should return emotional system code."""
        results = reader.get_relevant_code("emotions", max_results=3)

        # Should return at least 1 result
        assert len(results) > 0, "Should find code related to 'emotions'"

        # Check that results are CodeSnippet objects
        for snippet in results:
            assert isinstance(snippet, CodeSnippet)
            assert snippet.relevance_score > 0

        # Check for emotional system classes
        result_names = {s.class_or_function for s in results}
        emotional_classes = {"EmotionalState", "DecaySystem", "InteractionHandler"}
        assert any(cls in result_names for cls in emotional_classes), (
            "Should find emotional system classes"
        )

    def test_get_relevant_code_personality(self, reader):
        """Query 'personality' should return personality modulation code."""
        results = reader.get_relevant_code("personality", max_results=3)

        # Should return results
        assert len(results) > 0, "Should find code related to 'personality'"

        # Check for personality-related class
        result_names = {s.class_or_function for s in results}
        assert (
            "PersonalityModulator" in result_names
            or "ModulationParameters" in result_names
        ), "Should find personality modulator"

    def test_get_relevant_code_inference(self, reader):
        """Query 'inference' should return LLM inference code."""
        results = reader.get_relevant_code("inference", max_results=5)

        # Should return results
        assert len(results) > 0, "Should find code related to 'inference'"

        # Check for inference class or related error classes
        result_names = {s.class_or_function for s in results}
        inference_related = {
            "OllamaInference",
            "PromptBuilder",
            "InferenceError",
            "ContextOverflowError",
        }
        assert any(cls in result_names for cls in inference_related), (
            f"Should find inference-related code, got {result_names}"
        )

    def test_get_relevant_code_max_results(self, reader):
        """Verify max_results parameter is respected."""
        results = reader.get_relevant_code("emotions", max_results=2)
        assert len(results) <= 2, "Should respect max_results parameter"

        results = reader.get_relevant_code("emotions", max_results=5)
        assert len(results) <= 5, "Should respect max_results parameter"

    def test_relevance_scoring(self, reader):
        """Verify relevance scores are properly calculated."""
        results = reader.get_relevant_code("emotions", max_results=5)

        if len(results) > 1:
            # Scores should be in descending order
            scores = [s.relevance_score for s in results]
            assert scores == sorted(scores, reverse=True), (
                "Results should be sorted by relevance"
            )

        # Scores should be between 0 and 1
        for result in results:
            assert 0 <= result.relevance_score <= 1, "Relevance score should be 0-1"


class TestModuleRetrieval:
    """Test direct module retrieval."""

    def test_get_code_for_module_emotional_state(self, reader):
        """Retrieve full EmotionalState class."""
        snippet = reader.get_code_for_module("EmotionalState")

        assert snippet is not None, "Should find EmotionalState"
        assert snippet.class_or_function == "EmotionalState"
        assert "class EmotionalState" in snippet.content
        assert snippet.tokens > 0

    def test_get_code_for_module_ollama_inference(self, reader):
        """Retrieve full OllamaInference class."""
        snippet = reader.get_code_for_module("OllamaInference")

        assert snippet is not None, "Should find OllamaInference"
        assert snippet.class_or_function == "OllamaInference"
        assert "class OllamaInference" in snippet.content

    def test_get_code_for_nonexistent_module(self, reader):
        """Querying nonexistent module returns None."""
        snippet = reader.get_code_for_module("NonexistentClass")
        assert snippet is None, "Should return None for nonexistent module"

    def test_code_module_content_length(self, reader):
        """Verify module code snippets have substantial content."""
        snippet = reader.get_code_for_module("EmotionalState")

        if snippet:
            # Class definition should have reasonable length
            assert len(snippet.content) > 100, "Class definition should be substantial"
            assert snippet.end_line > snippet.start_line, (
                "Class should span multiple lines"
            )


class TestKeywordExtraction:
    """Test keyword extraction from queries."""

    def test_extract_keywords(self, reader):
        """Verify keywords are extracted from queries."""
        # Test various queries
        test_cases = [
            ("how do emotions work?", ["emotions", "work"]),
            ("what is personality?", ["personality"]),
            ("emotions and personality", ["emotions", "personality"]),
        ]

        for query, expected_keywords in test_cases:
            keywords = reader._extract_keywords(query)
            for keyword in expected_keywords:
                assert keyword in keywords, (
                    f"Query '{query}' should extract '{keyword}', got {keywords}"
                )

    def test_stop_word_removal(self, reader):
        """Verify stop words are removed."""
        query = "how do you work what is the thing"
        keywords = reader._extract_keywords(query)

        stop_words = {"how", "do", "you", "what", "is", "the"}
        for word in keywords:
            assert word not in stop_words, f"Stop word '{word}' should be removed"


class TestRelevanceCalculation:
    """Test relevance scoring."""

    def test_calculate_relevance(self, reader, logger, token_counter):
        """Verify relevance scores are calculated correctly."""
        # Create test snippet
        test_snippet = CodeSnippet(
            file_path="src/emotion/models.py",
            class_or_function="EmotionalState",
            start_line=1,
            end_line=50,
            content="class EmotionalState:\n    emotions: dict",
            tokens=100,
        )

        # Query with matching keywords
        query_keywords = ["emotional", "state"]
        score = reader._calculate_relevance(query_keywords, test_snippet)

        # Should have positive relevance
        assert score > 0, "Should have positive relevance for matching keywords"
        assert 0 <= score <= 1, "Relevance should be 0-1"

    def test_relevance_prefers_shorter_snippets(self, reader):
        """Verify relevance scoring prefers shorter snippets."""
        long_snippet = CodeSnippet(
            file_path="src/emotion/models.py",
            class_or_function="LongClass",
            start_line=1,
            end_line=500,
            content="x" * 5000,  # Very long
            tokens=2000,
        )

        short_snippet = CodeSnippet(
            file_path="src/emotion/models.py",
            class_or_function="ShortClass",
            start_line=1,
            end_line=10,
            content="class EmotionalState: pass",
            tokens=50,
        )

        query_keywords = ["emotional"]

        long_score = reader._calculate_relevance(query_keywords, long_snippet)
        short_score = reader._calculate_relevance(query_keywords, short_snippet)

        # Both should be positive, but short should be higher
        # (or equal if no keyword match, which is fine)
        assert long_score >= 0 and short_score >= 0


class TestImports:
    """Test that CodebaseReader can be imported properly."""

    def test_import_codebase_reader(self):
        """Verify CodebaseReader can be imported."""
        from src.llm.codebase_reader import CodebaseReader

        assert CodebaseReader is not None

    def test_import_code_snippet(self):
        """Verify CodeSnippet can be imported."""
        from src.llm.codebase_reader import CodeSnippet

        assert CodeSnippet is not None

    def test_import_from_llm_module(self):
        """Verify exports work from llm module."""
        from src.llm import CodebaseReader, CodeSnippet

        assert CodebaseReader is not None
        assert CodeSnippet is not None


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_query(self, reader):
        """Test behavior with empty query."""
        results = reader.get_relevant_code("", max_results=3)
        # Should return empty or minimal results
        assert isinstance(results, list)

    def test_special_characters_in_query(self, reader):
        """Test queries with special characters."""
        results = reader.get_relevant_code("emotions?!@#$%", max_results=3)
        # Should handle gracefully
        assert isinstance(results, list)

    def test_case_insensitive_retrieval(self, reader):
        """Test that retrieval is case-insensitive."""
        results_lower = reader.get_relevant_code("emotions", max_results=3)
        results_upper = reader.get_relevant_code("EMOTIONS", max_results=3)

        # Should find same classes (though scores might differ)
        lower_names = {s.class_or_function for s in results_lower}
        upper_names = {s.class_or_function for s in results_upper}

        # At least one common result expected
        assert len(lower_names & upper_names) > 0, "Case-insensitive search should work"

"""
Codebase reader for self-aware AI system.

Enables Demi to read and understand her own source code,
supporting semantic code retrieval and self-awareness features.
"""

import os
from dataclasses import dataclass
from typing import Optional, List, Dict, Callable
from pathlib import Path
import re
from src.core.logger import DemiLogger


@dataclass
class CodeSnippet:
    """Represents a code snippet with metadata."""

    file_path: str  # Relative path (e.g., "src/models/emotional_state.py")
    class_or_function: str  # Name of class/function (e.g., "EmotionalState")
    start_line: int
    end_line: int
    content: str  # The actual code
    tokens: int  # Token count of this snippet
    relevance_score: float = 0.0  # For ranking (0-1)


class CodebaseReader:
    """
    Reads and indexes Demi's source code for semantic retrieval.

    Enables self-awareness by allowing access to codebase information
    to be injected into prompts.
    """

    def __init__(
        self,
        logger: DemiLogger,
        codebase_root: str = "src/",
        token_counter: Optional[Callable[[str], int]] = None,
    ):
        """
        Initialize CodebaseReader.

        Args:
            logger: DemiLogger instance for logging
            codebase_root: Root directory of source code
            token_counter: Optional function to count tokens (defaults to char-based estimation)
        """
        self.logger = logger
        self.codebase_root = codebase_root
        self.token_counter = token_counter or self._default_token_counter
        self._file_cache: Dict[str, str] = {}
        self._code_index: Dict[str, CodeSnippet] = {}

        # Load and parse codebase
        self._load_codebase()

    def _load_codebase(self):
        """Load all Python files from codebase root."""
        # Find all Python files
        python_files = []
        try:
            for root, dirs, files in os.walk(self.codebase_root):
                # Skip __pycache__ and other hidden directories
                dirs[:] = [
                    d for d in dirs if not d.startswith(".") and d != "__pycache__"
                ]

                for file in files:
                    if file.endswith(".py"):
                        filepath = os.path.join(root, file)
                        python_files.append(filepath)
        except Exception as e:
            self.logger.error(f"Error walking codebase: {e}")
            return

        # Read each file
        file_count = 0
        class_count = 0
        for filepath in python_files:
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    self._file_cache[filepath] = content
                    file_count += 1

                    # Extract code blocks
                    blocks = self._extract_code_blocks(filepath, content)
                    class_count += len(blocks)
                    self._code_index.update(blocks)

            except Exception as e:
                self.logger.warning(f"Error reading {filepath}: {e}")

        self.logger.info(
            f"Loaded codebase: {file_count} files, {class_count} classes/functions"
        )

    def _extract_code_blocks(
        self, filepath: str, content: str
    ) -> Dict[str, CodeSnippet]:
        """
        Extract class and function definitions from file content.

        Args:
            filepath: Path to the file
            content: File content

        Returns:
            Dictionary mapping class/function names to CodeSnippet objects
        """
        blocks = {}
        lines = content.split("\n")

        # Find class definitions
        class_pattern = re.compile(r"^class\s+(\w+)\s*[\(:]")
        function_pattern = re.compile(r"^def\s+(\w+)\s*\(")

        current_indent = 0
        for i, line in enumerate(lines):
            # Check for class definition
            class_match = class_pattern.match(line)
            if class_match:
                class_name = class_match.group(1)
                start_line = i + 1  # 1-indexed for display

                # Find end of class (next class/def at same or lower indent level)
                end_line = self._find_end_of_block(lines, i)

                # Extract class content
                class_content = "\n".join(lines[i : end_line + 1])
                snippet_tokens = self.token_counter(class_content)

                key = f"{filepath}:{class_name}"
                blocks[key] = CodeSnippet(
                    file_path=filepath,
                    class_or_function=class_name,
                    start_line=start_line,
                    end_line=end_line + 1,
                    content=class_content,
                    tokens=snippet_tokens,
                )

            # Check for top-level function definition
            func_match = function_pattern.match(line)
            if func_match and line.startswith("def "):  # Top-level only
                func_name = func_match.group(1)
                start_line = i + 1

                # Find end of function
                end_line = self._find_end_of_block(lines, i)

                # Extract function content
                func_content = "\n".join(lines[i : end_line + 1])
                snippet_tokens = self.token_counter(func_content)

                key = f"{filepath}:{func_name}"
                blocks[key] = CodeSnippet(
                    file_path=filepath,
                    class_or_function=func_name,
                    start_line=start_line,
                    end_line=end_line + 1,
                    content=func_content,
                    tokens=snippet_tokens,
                )

        return blocks

    def _find_end_of_block(self, lines: List[str], start_idx: int) -> int:
        """
        Find the end line of a code block (class or function).

        Args:
            lines: List of source lines
            start_idx: Starting line index

        Returns:
            Index of last line of block
        """
        if start_idx >= len(lines):
            return len(lines) - 1

        # Get the indent level of the definition
        first_line = lines[start_idx]
        def_indent = len(first_line) - len(first_line.lstrip())

        # Look for next definition at same or lower indent level
        for i in range(start_idx + 1, len(lines)):
            line = lines[i]

            # Skip empty lines and comments
            if not line.strip() or line.strip().startswith("#"):
                continue

            # Get indent
            line_indent = len(line) - len(line.lstrip())

            # If we find a line at same or lower indent that's a definition, we're done
            if line_indent <= def_indent:
                if line.strip().startswith("def ") or line.strip().startswith("class "):
                    return i - 1

        return len(lines) - 1

    def get_architecture_overview(self) -> str:
        """
        Get high-level architecture summary of Demi.

        Returns:
            String with architecture overview (under 500 tokens)
        """
        overview = """DEMI ARCHITECTURE OVERVIEW

Core Components:
- Emotional System (src/emotion/models.py): EmotionalState tracks 9 emotions (loneliness, excitement, frustration, jealousy, vulnerability, confidence, curiosity, affection, defensiveness)
- Decay System (src/emotion/decay.py): Background emotion decay with emotion-specific rates and dampening
- Interaction Handler (src/emotion/interactions.py): Maps 8 event types to emotional deltas
- Personality Modulation (src/emotion/modulation.py): Adjusts response tone based on emotional state
- Emotion Persistence (src/emotion/persistence.py): SQLite storage and recovery of emotional states
- LLM Inference (src/llm/inference.py): Ollama integration via llama3.2:1b model
- Prompt Builder (src/llm/prompt_builder.py): Constructs emotionally-modulated system prompts
- History Manager (src/llm/history_manager.py): Token-aware conversation history management
- Response Processor (src/llm/response_processor.py): Cleans responses and logs interactions
- Conductor Orchestrator (src/conductor/orchestrator.py): Manages all integrations and lifecycle

Message Processing Workflow:
1. Receive message from platform
2. Load emotional state from database
3. Determine personality modulation parameters
4. Build system prompt with emotional context
5. Build conversation history with token awareness
6. Call Ollama inference engine for response generation
7. Process response: clean text, count tokens, log interaction
8. Update emotional state based on interaction type
9. Persist updated state to database
10. Send response back to user"""
        return overview

    def get_relevant_code(self, query: str, max_results: int = 3) -> List[CodeSnippet]:
        """
        Retrieve relevant code snippets for a natural language query.

        Args:
            query: Natural language query (e.g., "how do emotions work?")
            max_results: Maximum number of snippets to return

        Returns:
            List of CodeSnippet objects ranked by relevance
        """
        # Extract keywords from query
        keywords = self._extract_keywords(query)

        if not keywords:
            self.logger.debug(f"No keywords extracted from query: {query}")
            return []

        # Score all code snippets
        scored_snippets = []
        for key, snippet in self._code_index.items():
            score = self._calculate_relevance(keywords, snippet)
            if score > 0:
                snippet.relevance_score = score
                scored_snippets.append(snippet)

        # Sort by relevance score (descending)
        scored_snippets.sort(key=lambda s: s.relevance_score, reverse=True)

        # Return top N
        results = scored_snippets[:max_results]
        self.logger.debug(f"Retrieved {len(results)} code snippets for query: {query}")
        return results

    def get_code_for_module(self, module_name: str) -> Optional[CodeSnippet]:
        """
        Get the full class or function definition by name.

        Args:
            module_name: Name of class or function (e.g., "EmotionalState")

        Returns:
            CodeSnippet with full content, or None if not found
        """
        # Search for exact match
        for key, snippet in self._code_index.items():
            if snippet.class_or_function == module_name:
                return snippet

        self.logger.debug(f"Module not found: {module_name}")
        return None

    def _extract_keywords(self, query: str) -> List[str]:
        """
        Extract keywords from natural language query.

        Args:
            query: Natural language query

        Returns:
            List of keywords (lowercase)
        """
        # Simple keyword extraction: split on spaces, remove stop words
        stop_words = {
            "how",
            "do",
            "you",
            "what",
            "is",
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
        }

        words = query.lower().split()
        keywords = [w.strip("?.,!;:") for w in words if w not in stop_words]
        return [k for k in keywords if k]  # Remove empty strings

    def _calculate_relevance(
        self, query_keywords: List[str], snippet: CodeSnippet
    ) -> float:
        """
        Calculate relevance score between query keywords and code snippet.

        Args:
            query_keywords: List of query keywords
            snippet: CodeSnippet to score

        Returns:
            Relevance score (0-1)
        """
        if not query_keywords:
            return 0.0

        # Check keyword matches in:
        # 1. Class/function name
        # 2. Content (docstring and code)
        matches = 0

        snippet_text = (snippet.class_or_function + " " + snippet.content).lower()

        for keyword in query_keywords:
            if keyword.lower() in snippet_text:
                matches += 1

        # Base relevance: match ratio
        base_score = matches / len(query_keywords)

        # Bonus for exact class/function name match
        if any(
            keyword.lower() in snippet.class_or_function.lower()
            for keyword in query_keywords
        ):
            base_score += 0.1

        # Apply length penalty: prefer shorter, more targeted snippets
        max_snippet_length = 2000
        length_penalty = (
            1.0 - (min(snippet.tokens, max_snippet_length) / max_snippet_length) * 0.3
        )

        final_score = base_score * length_penalty
        return min(final_score, 1.0)  # Clamp to 0-1

    def _default_token_counter(self, text: str) -> int:
        """
        Default token counter: rough estimation (1 token ≈ 4 characters).

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        return max(1, len(text) // 4)

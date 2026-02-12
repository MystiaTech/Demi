"""
Tests for Demi's self-modification system.

Tests the complete autonomy stack:
- SafeCodeModifier: File modifications with safety
- GitManager: Version control
- ModificationValidator: Testing and validation
- SafetyGuard: Rate limiting and protections
- EmergencyHealing: Self-repair
- SelfImprovementSystem: Integration
"""

import asyncio
import os
import pytest
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path

# Test imports
from src.autonomy.code_modifier import (
    SafeCodeModifier,
    ModificationResult,
    ModificationContext
)
from src.autonomy.git_manager import GitManager
from src.autonomy.modification_validator import (
    ModificationValidator,
    ValidationResult
)
from src.autonomy.safety_guard import SafetyGuard, SafetyLevel, SafetyViolation
from src.autonomy.emergency_healing import EmergencyHealing
from src.autonomy.autonomy_config import SelfModificationConfig
from src.autonomy.self_improvement import (
    SelfImprovementSystem,
    ImprovementSuggestion,
    ImprovementStatus
)


class TestSafeCodeModifier:
    """Tests for SafeCodeModifier."""
    
    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def modifier(self, temp_project):
        """Create a SafeCodeModifier instance."""
        return SafeCodeModifier(
            project_root=temp_project,
            backup_dir=os.path.join(temp_project, ".backups")
        )
    
    def test_detect_project_root(self):
        """Test auto-detection of project root."""
        modifier = SafeCodeModifier()
        assert modifier.project_root.exists()
    
    @pytest.mark.asyncio
    async def test_modify_file_success(self, modifier, temp_project):
        """Test successful file modification."""
        test_file = os.path.join(temp_project, "test.py")
        original_content = "# Original\ndef hello():\n    pass"
        new_content = "# Modified\ndef hello():\n    print('hello')"
        
        # Create original file
        with open(test_file, 'w') as f:
            f.write(original_content)
        
        # Modify
        context = ModificationContext(
            suggestion_id="test_1",
            reason="Test modification"
        )
        
        result = await modifier.modify_file(test_file, new_content, context)
        
        assert result.result == ModificationResult.SUCCESS
        assert result.backup_path is not None
        assert os.path.exists(result.backup_path)
        
        # Verify file was modified
        with open(test_file, 'r') as f:
            content = f.read()
        assert content == new_content
    
    @pytest.mark.asyncio
    async def test_critical_file_blocked(self, modifier, temp_project):
        """Test that critical files are blocked."""
        # Create a fake auth.py
        auth_file = os.path.join(temp_project, "src", "api", "auth.py")
        os.makedirs(os.path.dirname(auth_file), exist_ok=True)
        
        with open(auth_file, 'w') as f:
            f.write("# Auth file")
        
        context = ModificationContext(suggestion_id="test_1", reason="Test")
        result = await modifier.modify_file(auth_file, "# Modified", context)
        
        assert result.result == ModificationResult.CRITICAL_FILE_BLOCKED
    
    @pytest.mark.asyncio
    async def test_syntax_validation(self, modifier, temp_project):
        """Test that invalid Python syntax is rejected."""
        test_file = os.path.join(temp_project, "test.py")
        
        bad_content = "def hello(\n    pass"  # Invalid syntax
        
        context = ModificationContext(suggestion_id="test_1", reason="Test")
        result = await modifier.modify_file(test_file, bad_content, context)
        
        assert result.result == ModificationResult.SYNTAX_ERROR
    
    def test_rollback(self, modifier, temp_project):
        """Test file rollback."""
        test_file = os.path.join(temp_project, "test.py")
        original = "# Original"
        
        # Setup: create and modify file
        with open(test_file, 'w') as f:
            f.write(original)
        
        # Rollback should work even without history
        success = modifier.rollback_file(test_file)
        assert not success  # No backup yet


class TestGitManager:
    """Tests for GitManager."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create a temporary Git repository."""
        temp_dir = tempfile.mkdtemp()
        
        # Initialize git repo
        os.system(f"cd {temp_dir} && git init -q")
        os.system(f"cd {temp_dir} && git config user.email 'test@test.com'")
        os.system(f"cd {temp_dir} && git config user.name 'Test'")
        
        # Create initial commit
        with open(os.path.join(temp_dir, "README.md"), 'w') as f:
            f.write("# Test")
        os.system(f"cd {temp_dir} && git add . && git commit -q -m 'Initial'")
        
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def git_manager(self, temp_repo):
        """Create a GitManager instance."""
        return GitManager(project_root=temp_repo)
    
    def test_is_available(self, git_manager):
        """Test Git availability check."""
        assert git_manager.is_available() == True
    
    def test_is_clean_working_directory(self, git_manager):
        """Test clean working directory check."""
        assert git_manager.is_clean_working_directory() == True
    
    def test_get_status(self, git_manager):
        """Test getting Git status."""
        status = git_manager.get_status()
        
        assert status["available"] == True
        assert status["is_clean"] == True
        assert status["branch"] in ["main", "master"]
    
    def test_create_modification_branch(self, git_manager):
        """Test creating a modification branch."""
        branch = git_manager.create_modification_branch(
            "sugg_123",
            "Test improvement"
        )
        
        assert branch is not None
        assert "demi/autonomy" in branch.branch_name
        assert branch.suggestion_id == "sugg_123"
        
        # Verify branch exists
        assert git_manager._get_current_branch() == branch.branch_name


class TestModificationValidator:
    """Tests for ModificationValidator."""
    
    @pytest.fixture
    def validator(self):
        """Create a ModificationValidator instance."""
        return ModificationValidator()
    
    @pytest.mark.asyncio
    async def test_validate_valid_python(self, validator):
        """Test validation of valid Python code."""
        content = """
def hello():
    print("Hello")
    return True
"""
        report = await validator.validate_modification(
            "test.py",
            content
        )
        
        assert report.overall_result in [ValidationResult.PASSED, ValidationResult.WARNING]
        
        # Check syntax validation passed
        syntax_check = next(
            (c for c in report.checks if c.name == "syntax_validation"),
            None
        )
        assert syntax_check is not None
        assert syntax_check.result == ValidationResult.PASSED
    
    @pytest.mark.asyncio
    async def test_validate_invalid_syntax(self, validator):
        """Test validation catches invalid syntax."""
        content = "def hello(\n    pass"  # Invalid
        
        report = await validator.validate_modification(
            "test.py",
            content
        )
        
        assert report.overall_result == ValidationResult.FAILED
    
    @pytest.mark.asyncio
    async def test_validate_import_failure(self, validator):
        """Test validation catches import failures."""
        content = "import nonexistent_module_xyz"  # This will fail import
        
        report = await validator.validate_modification(
            "test.py",
            content
        )
        
        # Import check may fail, but overall might pass if other checks pass
        import_check = next(
            (c for c in report.checks if c.name == "import_validation"),
            None
        )
        if import_check:
            assert import_check.result in [ValidationResult.FAILED, ValidationResult.WARNING]


class TestSafetyGuard:
    """Tests for SafetyGuard."""
    
    @pytest.fixture
    def guard(self):
        """Create a SafetyGuard instance."""
        return SafetyGuard()
    
    def test_critical_file_check(self, guard):
        """Test that critical files are blocked."""
        allowed, reason = guard.check_modification_allowed(
            "src/api/auth.py",
            "# test"
        )
        
        assert allowed == False
        assert "Critical file blocked" in reason
    
    def test_dangerous_pattern_detection(self, guard):
        """Test detection of dangerous code patterns."""
        malicious_code = "exec('rm -rf /')"
        
        allowed, reason = guard.check_modification_allowed(
            "test.py",
            malicious_code
        )
        
        assert allowed == False
        assert "Dangerous patterns" in reason
    
    def test_rate_limiting(self, guard):
        """Test rate limiting."""
        # First few should be allowed
        for i in range(5):
            allowed, _ = guard.check_modification_allowed(
                "test.py",
                f"# test {i}"
            )
            assert allowed == True
        
        # Record failures to test consecutive failure limit
        for i in range(6):
            guard.record_modification("test.py", "# test", False)
        
        # Should now be blocked due to consecutive failures
        allowed, reason = guard.check_modification_allowed(
            "test.py",
            "# test"
        )
        assert allowed == False
        assert "consecutive failures" in reason
    
    def test_safety_levels(self, guard):
        """Test safety level changes."""
        assert guard.get_safety_level() == SafetyLevel.NORMAL
        
        guard.set_safety_level(SafetyLevel.RESTRICTIVE)
        assert guard.get_safety_level() == SafetyLevel.RESTRICTIVE
        
        # In restrictive mode, more files should be blocked
        # (This depends on specific implementation)
    
    def test_emergency_stop(self, guard):
        """Test emergency stop functionality."""
        assert guard.is_emergency_stopped() == False
        
        guard.emergency_stop("Test emergency")
        
        assert guard.is_emergency_stopped() == True
        
        allowed, reason = guard.check_modification_allowed("test.py", "# test")
        assert allowed == False
        assert "Emergency stop" in reason
        
        guard.emergency_resume()
        assert guard.is_emergency_stopped() == False


class TestEmergencyHealing:
    """Tests for EmergencyHealing."""
    
    @pytest.fixture
    def healer(self):
        """Create an EmergencyHealing instance."""
        return EmergencyHealing()
    
    @pytest.mark.asyncio
    async def test_check_system_health(self, healer):
        """Test health checking."""
        checks = await healer.check_system_health()
        
        assert len(checks) > 0
        
        # Should have core imports check
        import_check = next(
            (c for c in checks if c.name == "core_imports"),
            None
        )
        assert import_check is not None
    
    def test_is_system_healthy(self, healer):
        """Test health assessment."""
        from src.autonomy.emergency_healing import HealthCheck
        
        # Healthy checks
        healthy_checks = [
            HealthCheck("test1", True, "info", "OK"),
            HealthCheck("test2", True, "info", "OK"),
        ]
        assert healer.is_system_healthy(healthy_checks) == True
        
        # Critical failure
        unhealthy_checks = [
            HealthCheck("test1", True, "info", "OK"),
            HealthCheck("test2", False, "critical", "Failed"),
        ]
        assert healer.is_system_healthy(unhealthy_checks) == False


class TestSelfImprovementSystem:
    """Integration tests for SelfImprovementSystem."""
    
    @pytest.fixture
    def temp_project_with_git(self):
        """Create a temporary project with Git repo."""
        temp_dir = tempfile.mkdtemp()
        
        # Initialize git repo
        os.system(f"cd {temp_dir} && git init -q")
        os.system(f"cd {temp_dir} && git config user.email 'test@test.com'")
        os.system(f"cd {temp_dir} && git config user.name 'Test'")
        
        # Create project structure
        src_dir = os.path.join(temp_dir, "src", "emotion")
        os.makedirs(src_dir, exist_ok=True)
        
        # Create a test file
        with open(os.path.join(src_dir, "test_module.py"), 'w') as f:
            f.write("""# Test module
def test_function():
    pass
""")
        
        # Initial commit
        os.system(f"cd {temp_dir} && git add . && git commit -q -m 'Initial'")
        
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def improvement_system(self, temp_project_with_git):
        """Create a SelfImprovementSystem instance."""
        return SelfImprovementSystem(project_root=temp_project_with_git)
    
    def test_initialization(self, improvement_system):
        """Test system initialization."""
        assert improvement_system.code_modifier is not None
        assert improvement_system.git_manager is not None
        assert improvement_system.validator is not None
        assert improvement_system.safety_guard is not None
        assert improvement_system.emergency_healing is not None
    
    def test_get_status(self, improvement_system):
        """Test getting system status."""
        status = improvement_system.get_status()
        
        assert "enabled" in status
        assert "safety_level" in status
        assert "total_suggestions" in status
        assert "git_available" in status
    
    @pytest.mark.asyncio
    async def test_check_health(self, improvement_system):
        """Test health checking."""
        health = await improvement_system.check_health()
        
        assert "healthy" in health
        assert "checks" in health
        assert "safety_stats" in health
    
    def test_create_suggestion(self, improvement_system):
        """Test creating an improvement suggestion."""
        data = {
            'file': 'src/emotion/test.py',
            'description': 'Test improvement',
            'improved_code': '# Improved code\ndef test():\n    pass',
            'priority': 'medium',
            'confidence': 0.8
        }
        
        suggestion = improvement_system._create_suggestion(data)
        
        assert suggestion.file_path == 'src/emotion/test.py'
        assert suggestion.description == 'Test improvement'
        assert suggestion.priority == 'medium'
        assert suggestion.confidence == 0.8
        assert suggestion.status == ImprovementStatus.PENDING

    def test_parse_review_response_multiline_and_fenced_code(self, improvement_system):
        """Parser should keep multiline improved code and remove markdown fences."""
        response = """FILE: src/emotion/test_module.py
PRIORITY: high
DESCRIPTION: Fix syntax edge cases
CURRENT_CODE:
def test_function():
    pass
IMPROVED_CODE:
```python
def test_function():
    return "ok"
```
CONFIDENCE: 0.95
"""
        suggestions = improvement_system._parse_review_response(response)
        assert len(suggestions) == 1
        suggestion = suggestions[0]
        assert suggestion.current_code.strip().startswith("def test_function")
        prepared, error = improvement_system._prepare_suggested_content(suggestion)
        assert error is None
        assert "```" not in prepared
        assert 'return "ok"' in prepared

    def test_prepare_suggested_content_merges_snippet_with_existing_file(self, improvement_system):
        """Snippet suggestions should expand to full file via CURRENT_CODE replacement."""
        suggestion = ImprovementSuggestion(
            suggestion_id="test_merge_1",
            file_path="src/emotion/test_module.py",
            description="Replace function body",
            suggested_content='def test_function():\n    return "updated"',
            current_code='def test_function():\n    pass',
            priority="medium",
            confidence=0.9,
            created_at=datetime.now(timezone.utc),
        )

        prepared, error = improvement_system._prepare_suggested_content(suggestion)
        assert error is None
        assert "# Test module" in prepared
        assert 'return "updated"' in prepared
    
    @pytest.mark.asyncio
    async def test_apply_suggestion_safety_blocked(self, improvement_system):
        """Test that safety checks block dangerous modifications."""
        suggestion = ImprovementSuggestion(
            suggestion_id="test_1",
            file_path="src/api/auth.py",  # Critical file
            description="Test",
            suggested_content="# test",
            priority="medium",
            confidence=0.5,
            created_at=datetime.now(timezone.utc)
        )
        
        result = await improvement_system.apply_suggestion(suggestion)
        
        assert result == False
        assert suggestion.status == ImprovementStatus.FAILED
        assert "Safety" in suggestion.error_message

    @pytest.mark.asyncio
    async def test_apply_suggestion_path_escape_blocked(self, improvement_system):
        """Suggestions targeting paths outside project root should be rejected."""
        suggestion = ImprovementSuggestion(
            suggestion_id="test_escape_1",
            file_path="/tmp/escape.py",
            description="Path escape",
            suggested_content="print('x')",
            priority="medium",
            confidence=0.5,
            created_at=datetime.now(timezone.utc),
        )

        result = await improvement_system.apply_suggestion(suggestion)
        assert result is False
        assert suggestion.status == ImprovementStatus.FAILED
        assert suggestion.error_message and suggestion.error_message.startswith("Path:")


def test_integration_flow():
    """
    Integration test demonstrating the full flow.
    
    This test shows how all components work together:
    1. Safety checks
    2. Validation
    3. File modification
    4. Git operations
    """
    # This would be a comprehensive end-to-end test
    # For brevity, we're just showing the structure
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

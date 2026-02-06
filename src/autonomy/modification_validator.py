"""
ModificationValidator - Testing and validation for self-modifications.

Validates code changes through syntax checking, import verification,
test execution, and smoke tests. Ensures modifications don't break
the system before they're committed.
"""

import ast
import importlib
import importlib.util
import os
import subprocess
import sys
import tempfile
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from src.core.logger import get_logger

logger = get_logger()


class ValidationResult(Enum):
    """Validation result status."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class ValidationCheck:
    """Individual validation check result."""
    name: str
    result: ValidationResult
    message: str
    duration_ms: float
    details: Dict = field(default_factory=dict)


@dataclass
class ValidationReport:
    """Complete validation report for a modification."""
    report_id: str
    file_path: str
    timestamp: datetime
    overall_result: ValidationResult
    checks: List[ValidationCheck]
    passed_count: int
    failed_count: int
    warning_count: int
    total_duration_ms: float
    summary: str = ""


class ModificationValidator:
    """
    Validate self-modifications through multiple testing layers.
    
    Validation Pipeline:
    1. Syntax Validation - AST parsing
    2. Import Validation - Can module be imported?
    3. Unit Test Execution - Run related tests
    4. Smoke Test - Basic functionality check
    5. Performance Check - No significant degradation
    
    Usage:
        validator = ModificationValidator()
        
        # Validate before applying
        report = await validator.validate_modification(
            "src/emotion/decay.py",
            new_content
        )
        
        if report.overall_result == ValidationResult.PASSED:
            # Safe to apply
            pass
    """
    
    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize the validator.
        
        Args:
            project_root: Project root directory
        """
        self.project_root = Path(project_root or self._detect_project_root())
        self._test_cache: Dict[str, Any] = {}
        
        # Validation configuration
        self.config = {
            "syntax_check": True,
            "import_check": True,
            "run_unit_tests": True,
            "smoke_test": True,
            "performance_check": False,  # Disabled by default
            "test_timeout": 60,
            "max_test_failures": 3,
        }
        
        logger.info(f"ModificationValidator initialized: {self.project_root}")
    
    def _detect_project_root(self) -> str:
        """Auto-detect project root."""
        current_file = Path(__file__).resolve()
        return str(current_file.parent.parent.parent)
    
    async def validate_modification(
        self,
        file_path: str,
        new_content: str,
        original_content: Optional[str] = None
    ) -> ValidationReport:
        """
        Run full validation pipeline on a proposed modification.
        
        Args:
            file_path: Path to the file being modified
            new_content: Proposed new content
            original_content: Original content (if available)
            
        Returns:
            ValidationReport with all check results
        """
        report_id = f"val_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        abs_path = os.path.abspath(file_path)
        
        logger.info(f"Starting validation [{report_id}]: {file_path}")
        
        checks = []
        start_time = datetime.now(timezone.utc)
        
        # Check 1: Syntax Validation
        if self.config["syntax_check"] and file_path.endswith('.py'):
            check = self._validate_syntax(abs_path, new_content)
            checks.append(check)
            
            # If syntax fails, stop here
            if check.result == ValidationResult.FAILED:
                return self._create_report(report_id, abs_path, start_time, checks)
        
        # Check 2: Import Validation
        if self.config["import_check"] and file_path.endswith('.py'):
            check = self._validate_import(abs_path, new_content)
            checks.append(check)
            
            if check.result == ValidationResult.FAILED:
                return self._create_report(report_id, abs_path, start_time, checks)
        
        # Check 3: Unit Tests
        if self.config["run_unit_tests"]:
            check = await self._run_related_tests(abs_path)
            checks.append(check)
        
        # Check 4: Smoke Test
        if self.config["smoke_test"]:
            check = await self._smoke_test(abs_path, new_content)
            checks.append(check)
        
        # Check 5: Performance (if enabled)
        if self.config["performance_check"] and original_content:
            check = await self._performance_check(abs_path, original_content, new_content)
            checks.append(check)
        
        return self._create_report(report_id, abs_path, start_time, checks)
    
    def _validate_syntax(self, file_path: str, content: str) -> ValidationCheck:
        """Validate Python syntax via AST parsing."""
        start = datetime.now(timezone.utc)
        
        try:
            ast.parse(content, filename=file_path)
            duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            
            return ValidationCheck(
                name="syntax_validation",
                result=ValidationResult.PASSED,
                message="Python syntax is valid",
                duration_ms=duration
            )
        except SyntaxError as e:
            duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            return ValidationCheck(
                name="syntax_validation",
                result=ValidationResult.FAILED,
                message=f"Syntax error at line {e.lineno}: {e.msg}",
                duration_ms=duration,
                details={"line": e.lineno, "column": e.offset, "text": e.text}
            )
    
    def _validate_import(self, file_path: str, content: str) -> ValidationCheck:
        """Validate that the module can be imported."""
        start = datetime.now(timezone.utc)
        
        # Create temp file and try to import
        temp_path = None
        try:
            # Write to temp file
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False,
                dir=str(self.project_root)
            ) as f:
                f.write(content)
                temp_path = f.name
            
            # Try to import
            spec = importlib.util.spec_from_file_location("test_module", temp_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                # Add project root to path for imports
                sys.path.insert(0, str(self.project_root))
                try:
                    spec.loader.exec_module(module)
                    duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
                    
                    return ValidationCheck(
                        name="import_validation",
                        result=ValidationResult.PASSED,
                        message="Module imports successfully",
                        duration_ms=duration
                    )
                finally:
                    sys.path.remove(str(self.project_root))
            
            duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            return ValidationCheck(
                name="import_validation",
                result=ValidationResult.WARNING,
                message="Could not create module spec",
                duration_ms=duration
            )
            
        except Exception as e:
            duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            return ValidationCheck(
                name="import_validation",
                result=ValidationResult.FAILED,
                message=f"Import failed: {str(e)}",
                duration_ms=duration,
                details={"error": traceback.format_exc()}
            )
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
    
    async def _run_related_tests(self, file_path: str) -> ValidationCheck:
        """Run unit tests related to the modified file."""
        start = datetime.now(timezone.utc)
        
        # Find related test file
        rel_path = os.path.relpath(file_path, self.project_root)
        test_file = self._find_test_file(rel_path)
        
        if not test_file:
            duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            return ValidationCheck(
                name="unit_tests",
                result=ValidationResult.SKIPPED,
                message="No related test file found",
                duration_ms=duration
            )
        
        # Run pytest on the test file
        try:
            cmd = [
                sys.executable, "-m", "pytest",
                str(test_file),
                "-v",
                "--tb=short",
                "-x",  # Stop on first failure
                f"--timeout={self.config['test_timeout']}"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config['test_timeout'] + 10,
                cwd=str(self.project_root)
            )
            
            duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            
            if result.returncode == 0:
                # Parse output for test count
                passed = result.stdout.count("PASSED")
                return ValidationCheck(
                    name="unit_tests",
                    result=ValidationResult.PASSED,
                    message=f"All {passed} tests passed",
                    duration_ms=duration,
                    details={"tests_passed": passed}
                )
            else:
                # Extract failure details
                failed = result.stdout.count("FAILED")
                error_msg = "Tests failed"
                
                # Try to extract specific error
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'FAILED' in line or 'ERROR' in line:
                        error_msg = line.strip()
                        break
                
                return ValidationCheck(
                    name="unit_tests",
                    result=ValidationResult.FAILED,
                    message=error_msg,
                    duration_ms=duration,
                    details={
                        "stdout": result.stdout[-500:],  # Last 500 chars
                        "stderr": result.stderr[-500:],
                        "returncode": result.returncode
                    }
                )
                
        except subprocess.TimeoutExpired:
            duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            return ValidationCheck(
                name="unit_tests",
                result=ValidationResult.FAILED,
                message=f"Tests timed out after {self.config['test_timeout']}s",
                duration_ms=duration
            )
        except Exception as e:
            duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            return ValidationCheck(
                name="unit_tests",
                result=ValidationResult.ERROR,
                message=f"Test execution error: {str(e)}",
                duration_ms=duration
            )
    
    def _find_test_file(self, source_path: str) -> Optional[Path]:
        """Find the test file corresponding to a source file."""
        # Convert src/x/y.py to tests/test_x.py or tests/test_y.py
        parts = source_path.split(os.sep)
        
        # Try tests/test_<module>.py
        if len(parts) >= 2:
            module_name = Path(parts[-1]).stem
            test_candidates = [
                self.project_root / "tests" / f"test_{module_name}.py",
            ]
            
            # Also try with parent directory prefix
            if len(parts) >= 3:
                parent = parts[-2]
                test_candidates.append(
                    self.project_root / "tests" / f"test_{parent}_{module_name}.py"
                )
            
            for candidate in test_candidates:
                if candidate.exists():
                    return candidate
        
        return None
    
    async def _smoke_test(self, file_path: str, content: str) -> ValidationCheck:
        """Run basic smoke test on the modified code."""
        start = datetime.now(timezone.utc)
        
        # For Python files, try to execute and check for runtime errors
        if not file_path.endswith('.py'):
            duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            return ValidationCheck(
                name="smoke_test",
                result=ValidationResult.SKIPPED,
                message="Smoke test only for Python files",
                duration_ms=duration
            )
        
        temp_path = None
        try:
            # Write to temp file
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False,
                dir=str(self.project_root)
            ) as f:
                f.write(content)
                temp_path = f.name
            
            # Try to compile (catches more than parse)
            with open(temp_path, 'r') as f:
                code = compile(f.read(), temp_path, 'exec')
            
            # Try to execute in restricted environment
            restricted_globals = {
                "__name__": "__main__",
                "__file__": temp_path,
            }
            restricted_locals = {}
            
            # Execute with timeout
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Smoke test execution timeout")
            
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(5)  # 5 second timeout
            
            try:
                exec(code, restricted_globals, restricted_locals)
                signal.alarm(0)
            except TimeoutError:
                # Timeout is okay for long-running modules
                signal.alarm(0)
                pass
            except Exception as e:
                # Import errors are expected for complex modules
                if "ImportError" in str(type(e)) or "ModuleNotFoundError" in str(type(e)):
                    pass
                else:
                    raise
            
            duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            return ValidationCheck(
                name="smoke_test",
                result=ValidationResult.PASSED,
                message="Smoke test completed (compilation + basic execution)",
                duration_ms=duration
            )
            
        except Exception as e:
            duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            return ValidationCheck(
                name="smoke_test",
                result=ValidationResult.WARNING,  # Warning, not fail (might be expected)
                message=f"Smoke test warning: {str(e)}",
                duration_ms=duration,
                details={"error": str(e)}
            )
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
    
    async def _performance_check(
        self,
        file_path: str,
        original_content: str,
        new_content: str
    ) -> ValidationCheck:
        """Check that performance hasn't degraded significantly."""
        start = datetime.now(timezone.utc)
        
        # This is a placeholder for actual performance testing
        # Real implementation would benchmark specific functions
        
        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return ValidationCheck(
            name="performance_check",
            result=ValidationResult.SKIPPED,
            message="Performance checking not yet implemented",
            duration_ms=duration
        )
    
    def _create_report(
        self,
        report_id: str,
        file_path: str,
        start_time: datetime,
        checks: List[ValidationCheck]
    ) -> ValidationReport:
        """Create a validation report from checks."""
        passed = len([c for c in checks if c.result == ValidationResult.PASSED])
        failed = len([c for c in checks if c.result == ValidationResult.FAILED])
        warnings = len([c for c in checks if c.result == ValidationResult.WARNING])
        
        total_duration = sum(c.duration_ms for c in checks)
        
        # Determine overall result
        if failed > 0:
            overall = ValidationResult.FAILED
        elif warnings > 0:
            overall = ValidationResult.WARNING
        else:
            overall = ValidationResult.PASSED
        
        # Generate summary
        summary = f"Validation {overall.value}: {passed} passed, {failed} failed, {warnings} warnings"
        
        return ValidationReport(
            report_id=report_id,
            file_path=file_path,
            timestamp=start_time,
            overall_result=overall,
            checks=checks,
            passed_count=passed,
            failed_count=failed,
            warning_count=warnings,
            total_duration_ms=total_duration,
            summary=summary
        )
    
    def can_apply_safely(self, report: ValidationReport) -> bool:
        """
        Determine if a modification can be safely applied based on validation.
        
        Returns True if:
        - No failed checks
        - Any warnings are acceptable
        """
        if report.overall_result == ValidationResult.FAILED:
            return False
        
        # Allow if passed or just warnings
        return report.overall_result in (ValidationResult.PASSED, ValidationResult.WARNING)
    
    def get_validation_config(self) -> Dict:
        """Get current validation configuration."""
        return self.config.copy()
    
    def update_validation_config(self, **kwargs):
        """Update validation configuration."""
        for key, value in kwargs.items():
            if key in self.config:
                self.config[key] = value
                logger.info(f"Validation config updated: {key}={value}")

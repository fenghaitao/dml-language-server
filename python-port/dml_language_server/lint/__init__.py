"""
Linting engine for the DML Language Server.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from ..config import Config, LintConfig
from ..analysis import IsolatedAnalysis, DMLError, DMLErrorKind
from ..lsp_data import DMLDiagnosticSeverity
from ..span import ZeroSpan, ZeroPosition, ZeroRange

logger = logging.getLogger(__name__)


class LintRuleLevel(Enum):
    """Severity levels for lint rules."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HINT = "hint"


@dataclass
class LintRule:
    """Base class for lint rules."""
    name: str
    description: str
    level: LintRuleLevel = LintRuleLevel.WARNING
    enabled: bool = True
    
    def check(self, file_path: Path, content: str, analysis: IsolatedAnalysis) -> List[DMLError]:
        """Check the rule against a file."""
        raise NotImplementedError


class IndentationRule(LintRule):
    """Rule for checking indentation consistency."""
    
    def __init__(self):
        super().__init__(
            name="indentation",
            description="Check for consistent indentation",
            level=LintRuleLevel.WARNING
        )
        self.expected_indent = 4  # spaces
    
    def check(self, file_path: Path, content: str, analysis: IsolatedAnalysis) -> List[DMLError]:
        """Check indentation in the file."""
        errors = []
        lines = content.splitlines()
        
        for line_num, line in enumerate(lines):
            if not line.strip():  # Skip empty lines
                continue
            
            # Count leading spaces
            leading_spaces = len(line) - len(line.lstrip(' '))
            
            # Check for tabs
            if '\t' in line[:leading_spaces + 1]:
                span = ZeroSpan(
                    str(file_path),
                    ZeroRange(
                        ZeroPosition(line_num, 0),
                        ZeroPosition(line_num, len(line))
                    )
                )
                error = DMLError(
                    kind=DMLErrorKind.SYNTAX_ERROR,
                    message="Use spaces instead of tabs for indentation",
                    span=span,
                    severity=DMLDiagnosticSeverity.WARNING,
                    code="no-tabs"
                )
                errors.append(error)
            
            # Check indentation consistency (simplified)
            if leading_spaces % self.expected_indent != 0:
                span = ZeroSpan(
                    str(file_path),
                    ZeroRange(
                        ZeroPosition(line_num, 0),
                        ZeroPosition(line_num, leading_spaces)
                    )
                )
                error = DMLError(
                    kind=DMLErrorKind.SYNTAX_ERROR,
                    message=f"Indentation should be multiple of {self.expected_indent} spaces",
                    span=span,
                    severity=DMLDiagnosticSeverity.WARNING,
                    code="indent-size"
                )
                errors.append(error)
        
        return errors


class SpacingRule(LintRule):
    """Rule for checking spacing around operators."""
    
    def __init__(self):
        super().__init__(
            name="spacing",
            description="Check spacing around operators and punctuation",
            level=LintRuleLevel.WARNING
        )
    
    def check(self, file_path: Path, content: str, analysis: IsolatedAnalysis) -> List[DMLError]:
        """Check spacing in the file."""
        errors = []
        lines = content.splitlines()
        
        for line_num, line in enumerate(lines):
            # Check for multiple spaces
            if '  ' in line and not line.strip().startswith('//'):
                # Find the position of multiple spaces
                pos = line.find('  ')
                span = ZeroSpan(
                    str(file_path),
                    ZeroRange(
                        ZeroPosition(line_num, pos),
                        ZeroPosition(line_num, pos + 2)
                    )
                )
                error = DMLError(
                    kind=DMLErrorKind.SYNTAX_ERROR,
                    message="Avoid multiple consecutive spaces",
                    span=span,
                    severity=DMLDiagnosticSeverity.INFO,
                    code="no-multiple-spaces"
                )
                errors.append(error)
            
            # Check trailing whitespace
            if line.endswith(' ') or line.endswith('\t'):
                span = ZeroSpan(
                    str(file_path),
                    ZeroRange(
                        ZeroPosition(line_num, len(line.rstrip())),
                        ZeroPosition(line_num, len(line))
                    )
                )
                error = DMLError(
                    kind=DMLErrorKind.SYNTAX_ERROR,
                    message="Trailing whitespace",
                    span=span,
                    severity=DMLDiagnosticSeverity.INFO,
                    code="no-trailing-spaces"
                )
                errors.append(error)
        
        return errors


class NamingConventionRule(LintRule):
    """Rule for checking naming conventions."""
    
    def __init__(self):
        super().__init__(
            name="naming",
            description="Check naming conventions for DML constructs",
            level=LintRuleLevel.WARNING
        )
    
    def check(self, file_path: Path, content: str, analysis: IsolatedAnalysis) -> List[DMLError]:
        """Check naming conventions."""
        errors = []
        
        for symbol in analysis.symbols:
            name = symbol.name
            kind = symbol.kind
            
            # Check device names (should be PascalCase)
            if kind.value == "device" and not self._is_pascal_case(name):
                error = DMLError(
                    kind=DMLErrorKind.SEMANTIC_ERROR,
                    message=f"Device names should use PascalCase: '{name}'",
                    span=symbol.location.span,
                    severity=DMLDiagnosticSeverity.WARNING,
                    code="device-naming"
                )
                errors.append(error)
            
            # Check method names (should be snake_case)
            if kind.value == "method" and not self._is_snake_case(name):
                error = DMLError(
                    kind=DMLErrorKind.SEMANTIC_ERROR,
                    message=f"Method names should use snake_case: '{name}'",
                    span=symbol.location.span,
                    severity=DMLDiagnosticSeverity.WARNING,
                    code="method-naming"
                )
                errors.append(error)
        
        return errors
    
    def _is_pascal_case(self, name: str) -> bool:
        """Check if name is in PascalCase."""
        return name[0].isupper() and '_' not in name
    
    def _is_snake_case(self, name: str) -> bool:
        """Check if name is in snake_case."""
        return name.islower() and ' ' not in name


class LintEngine:
    """Main linting engine."""
    
    def __init__(self, config: Config):
        self.config = config
        self.rules: List[LintRule] = []
        
        # Register default rules
        self._register_default_rules()
        
        # Apply configuration
        self._apply_config()
    
    def _register_default_rules(self) -> None:
        """Register default lint rules."""
        self.rules = [
            IndentationRule(),
            SpacingRule(),
            NamingConventionRule(),
        ]
    
    def _apply_config(self) -> None:
        """Apply lint configuration."""
        lint_config = self.config.lint_config
        if not lint_config:
            return
        
        # Enable/disable rules based on configuration
        for rule in self.rules:
            if rule.name in lint_config.disabled_rules:
                rule.enabled = False
            elif rule.name in lint_config.enabled_rules:
                rule.enabled = True
            
            # Apply rule-specific configuration
            if rule.name in lint_config.rule_configs:
                rule_config = lint_config.rule_configs[rule.name]
                self._apply_rule_config(rule, rule_config)
    
    def _apply_rule_config(self, rule: LintRule, rule_config: Dict[str, Any]) -> None:
        """Apply configuration to a specific rule."""
        if 'level' in rule_config:
            try:
                rule.level = LintRuleLevel(rule_config['level'])
            except ValueError:
                logger.warning(f"Invalid level for rule {rule.name}: {rule_config['level']}")
        
        if 'enabled' in rule_config:
            rule.enabled = bool(rule_config['enabled'])
        
        # Apply rule-specific settings
        if hasattr(rule, 'expected_indent') and 'indent_size' in rule_config:
            rule.expected_indent = int(rule_config['indent_size'])
    
    def lint_file(self, file_path: Path, content: str, analysis: IsolatedAnalysis) -> List[DMLError]:
        """
        Lint a file and return found issues.
        
        Args:
            file_path: Path to the file
            content: File content
            analysis: Analysis results for the file
            
        Returns:
            List of lint errors/warnings
        """
        all_errors = []
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            try:
                rule_errors = rule.check(file_path, content, analysis)
                all_errors.extend(rule_errors)
            except Exception as e:
                logger.error(f"Error running lint rule {rule.name} on {file_path}: {e}")
        
        return all_errors
    
    def get_rule_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all rules."""
        rule_info = {}
        
        for rule in self.rules:
            rule_info[rule.name] = {
                'description': rule.description,
                'level': rule.level.value,
                'enabled': rule.enabled
            }
        
        return rule_info
    
    def load_config(self, config_path: Path) -> None:
        """Load lint configuration from file."""
        self.config.load_lint_config(config_path)
        self._apply_config()


# Export main classes
__all__ = [
    "LintEngine",
    "LintRule",
    "LintRuleLevel",
    "IndentationRule",
    "SpacingRule", 
    "NamingConventionRule"
]
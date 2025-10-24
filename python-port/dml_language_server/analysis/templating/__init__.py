"""
DML Templating Analysis Module

This module provides comprehensive analysis of DML templates including type
resolution, method analysis, object resolution, topology analysis, and trait
support. It corresponds to the Rust implementation in src/analysis/templating/.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

from .types import *
from .methods import *
from .objects import *
from .topology import *
from .traits import *

# Core templating declaration from Rust mod.rs
from dataclasses import dataclass
from ..structure.expressions import DMLString
from .types import DMLResolvedType

@dataclass
class Declaration:
    """Template declaration matching Rust implementation."""
    type_ref: DMLResolvedType
    name: DMLString
    
    def is_abstract(self) -> bool:
        """Check if declaration is abstract."""
        return True
    
    def name(self) -> DMLString:
        """Get declaration name."""
        return self.name

__all__ = [
    # From types
    'TemplateTypeKind', 'DMLBaseType', 'DMLStructType', 'DMLConcreteType', 'DMLResolvedType',
    'TemplateTypeResolver', 'TemplateTypeChecker', 'eval_type', 'eval_type_simple',
    
    # From methods
    'MethodKind', 'MethodSignature', 'MethodDeclaration', 'MethodOverload', 
    'MethodRegistry', 'MethodAnalyzer', 'eval_method_returns',
    
    # From objects
    'ObjectResolutionKind', 'ObjectSpec', 'DMLResolvedObject', 'TemplateInstance',
    'DMLShallowObjectVariant', 'DMLAmbiguousDef', 'DMLCompositeObject', 'ObjectResolver',
    
    # From topology
    'TemplateRank', 'RankDesc', 'TemplateNode', 'DependencyEdge', 'TemplateGraph',
    'TopologyAnalyzer', 'rank_templates', 'rank_templates_aux',
    
    # From traits
    'TraitKind', 'TraitRequirement', 'TraitImplementation', 'TraitDefinition',
    'TraitMemberKind', 'TraitMethod', 'TraitParameter', 'TraitConstraint',
    'TraitInstance', 'TraitResolver',
    
    # Core declaration
    'Declaration',
]
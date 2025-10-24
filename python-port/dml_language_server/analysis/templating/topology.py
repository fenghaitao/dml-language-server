"""
DML Template Topology Analysis

Provides topology analysis for DML templates, including template ranking,
dependency resolution, and instantiation ordering. This module corresponds
to the Rust implementation in src/analysis/templating/topology.rs.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

from typing import List, Optional, Dict, Any, Union, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import heapq

from ...span import ZeroSpan, ZeroPosition, ZeroRange
from ..types import DMLError, DMLErrorKind
from ..structure.objects import Template, DMLObject, ObjectKind


class TemplateRank(Enum):
    """Template ranking for instantiation order."""
    BASE = 0        # Base templates with no dependencies
    DERIVED = 1     # Templates that extend other templates
    SPECIALIZED = 2 # Specialized versions of templates
    COMPLEX = 3     # Templates with complex dependencies


@dataclass
class RankDesc:
    """Template rank description."""
    rank: TemplateRank
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    depth: int = 0
    
    def add_dependency(self, template_name: str) -> None:
        """Add a template dependency."""
        self.dependencies.add(template_name)
    
    def add_dependent(self, template_name: str) -> None:
        """Add a template that depends on this one."""
        self.dependents.add(template_name)
    
    def has_dependencies(self) -> bool:
        """Check if template has dependencies."""
        return len(self.dependencies) > 0
    
    def is_leaf(self) -> bool:
        """Check if template is a leaf (no dependents)."""
        return len(self.dependents) == 0


@dataclass
class TemplateNode:
    """Node in template dependency graph."""
    template: Template
    rank_desc: RankDesc
    visited: bool = False
    in_progress: bool = False
    resolved: bool = False
    
    def get_name(self) -> str:
        """Get template name."""
        return self.template.name.value


@dataclass
class DependencyEdge:
    """Edge in template dependency graph."""
    from_template: str
    to_template: str
    dependency_type: str = "extends"  # extends, uses, etc.
    span: Optional[ZeroSpan] = None


class TemplateGraph:
    """Graph representing template dependencies."""
    
    def __init__(self):
        self.nodes: Dict[str, TemplateNode] = {}
        self.edges: List[DependencyEdge] = []
        self.errors: List[DMLError] = []
    
    def add_template(self, template: Template) -> None:
        """Add a template to the graph."""
        name = template.name.value
        
        if name in self.nodes:
            error = DMLError(
                kind=DMLErrorKind.DUPLICATE_SYMBOL,
                message=f"Duplicate template: {name}",
                span=template.span
            )
            self.errors.append(error)
            return
        
        rank_desc = RankDesc(rank=TemplateRank.BASE)
        node = TemplateNode(template=template, rank_desc=rank_desc)
        self.nodes[name] = node
    
    def add_dependency(self, from_template: str, to_template: str, 
                      dependency_type: str = "extends", span: Optional[ZeroSpan] = None) -> None:
        """Add a dependency edge."""
        if from_template not in self.nodes:
            error = DMLError(
                kind=DMLErrorKind.TEMPLATE_ERROR,
                message=f"Unknown template: {from_template}",
                span=span or ZeroSpan("unknown", ZeroRange(ZeroPosition(0, 0), ZeroPosition(0, 0)))
            )
            self.errors.append(error)
            return
        
        if to_template not in self.nodes:
            error = DMLError(
                kind=DMLErrorKind.TEMPLATE_ERROR,
                message=f"Unknown template dependency: {to_template}",
                span=span or ZeroSpan("unknown", ZeroRange(ZeroPosition(0, 0), ZeroPosition(0, 0)))
            )
            self.errors.append(error)
            return
        
        # Add edge
        edge = DependencyEdge(
            from_template=from_template,
            to_template=to_template,
            dependency_type=dependency_type,
            span=span
        )
        self.edges.append(edge)
        
        # Update rank descriptions
        from_node = self.nodes[from_template]
        to_node = self.nodes[to_template]
        
        from_node.rank_desc.add_dependency(to_template)
        to_node.rank_desc.add_dependent(from_template)
    
    def detect_cycles(self) -> List[DMLError]:
        """Detect circular dependencies in template graph."""
        errors = []
        
        # Reset visit state
        for node in self.nodes.values():
            node.visited = False
            node.in_progress = False
        
        def visit(node_name: str, path: List[str]) -> None:
            node = self.nodes[node_name]
            
            if node.in_progress:
                # Cycle detected
                cycle_start = path.index(node_name)
                cycle = path[cycle_start:] + [node_name]
                cycle_str = " -> ".join(cycle)
                
                error = DMLError(
                    kind=DMLErrorKind.CIRCULAR_DEPENDENCY,
                    message=f"Circular template dependency: {cycle_str}",
                    span=node.template.span
                )
                errors.append(error)
                return
            
            if node.visited:
                return
            
            node.in_progress = True
            
            # Visit dependencies
            for dep_name in node.rank_desc.dependencies:
                visit(dep_name, path + [node_name])
            
            node.in_progress = False
            node.visited = True
        
        # Visit all nodes
        for node_name in self.nodes:
            if not self.nodes[node_name].visited:
                visit(node_name, [])
        
        return errors
    
    def compute_ranks(self) -> None:
        """Compute template ranks based on dependencies."""
        # Reset visit state
        for node in self.nodes.values():
            node.visited = False
            node.rank_desc.depth = 0
        
        def compute_depth(node_name: str) -> int:
            node = self.nodes[node_name]
            
            if node.visited:
                return node.rank_desc.depth
            
            node.visited = True
            
            # Compute max depth of dependencies
            max_depth = 0
            for dep_name in node.rank_desc.dependencies:
                dep_depth = compute_depth(dep_name)
                max_depth = max(max_depth, dep_depth + 1)
            
            node.rank_desc.depth = max_depth
            
            # Assign rank based on depth and characteristics
            if max_depth == 0:
                node.rank_desc.rank = TemplateRank.BASE
            elif node.rank_desc.is_leaf():
                node.rank_desc.rank = TemplateRank.SPECIALIZED
            elif len(node.rank_desc.dependencies) > 2:
                node.rank_desc.rank = TemplateRank.COMPLEX
            else:
                node.rank_desc.rank = TemplateRank.DERIVED
            
            return node.rank_desc.depth
        
        # Compute depths for all nodes
        for node_name in self.nodes:
            compute_depth(node_name)
    
    def get_instantiation_order(self) -> List[str]:
        """Get templates in instantiation order (topological sort)."""
        # Use Kahn's algorithm for topological sort
        in_degree = {}
        for node_name in self.nodes:
            in_degree[node_name] = len(self.nodes[node_name].rank_desc.dependencies)
        
        queue = []
        for node_name, degree in in_degree.items():
            if degree == 0:
                # Use negative rank value for priority queue (min-heap)
                heapq.heappush(queue, (self.nodes[node_name].rank_desc.rank.value, node_name))
        
        result = []
        
        while queue:
            _, node_name = heapq.heappop(queue)
            result.append(node_name)
            
            # Reduce in-degree of dependents
            node = self.nodes[node_name]
            for dependent in node.rank_desc.dependents:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    dependent_node = self.nodes[dependent]
                    heapq.heappush(queue, (dependent_node.rank_desc.rank.value, dependent))
        
        return result
    
    def get_nodes_by_rank(self, rank: TemplateRank) -> List[TemplateNode]:
        """Get all nodes with specific rank."""
        return [node for node in self.nodes.values() if node.rank_desc.rank == rank]
    
    def get_template_dependencies(self, template_name: str) -> Set[str]:
        """Get all dependencies of a template."""
        if template_name not in self.nodes:
            return set()
        return self.nodes[template_name].rank_desc.dependencies.copy()
    
    def get_template_dependents(self, template_name: str) -> Set[str]:
        """Get all templates that depend on this template."""
        if template_name not in self.nodes:
            return set()
        return self.nodes[template_name].rank_desc.dependents.copy()


class TopologyAnalyzer:
    """Analyzes template topology and dependencies."""
    
    def __init__(self):
        self.graph = TemplateGraph()
        self.errors: List[DMLError] = []
        self.analysis_complete = False
    
    def add_template(self, template: Template) -> None:
        """Add a template for analysis."""
        self.graph.add_template(template)
        
        # Extract template dependencies from object structure
        self._extract_dependencies(template)
        
        self.analysis_complete = False
    
    def _extract_dependencies(self, template: Template) -> None:
        """Extract dependencies from template structure."""
        template_name = template.name.value
        
        # Check template applications in the template itself
        for applied_template in template.templates:
            self.graph.add_dependency(
                from_template=template_name,
                to_template=applied_template,
                dependency_type="extends",
                span=template.span
            )
        
        # Check dependencies in child objects
        self._extract_object_dependencies(template, template_name)
    
    def _extract_object_dependencies(self, obj: DMLObject, template_name: str) -> None:
        """Extract dependencies from object and its children."""
        # Check template applications in child objects
        for applied_template in obj.templates:
            self.graph.add_dependency(
                from_template=template_name,
                to_template=applied_template,
                dependency_type="uses",
                span=obj.span
            )
        
        # Recursively check children
        for child in obj.children:
            self._extract_object_dependencies(child, template_name)
    
    def analyze(self) -> None:
        """Perform complete topology analysis."""
        if self.analysis_complete:
            return
        
        # Detect circular dependencies
        cycle_errors = self.graph.detect_cycles()
        self.errors.extend(cycle_errors)
        
        if not cycle_errors:
            # Compute ranks only if no cycles
            self.graph.compute_ranks()
        
        # Collect graph errors
        self.errors.extend(self.graph.errors)
        
        self.analysis_complete = True
    
    def get_instantiation_order(self) -> List[str]:
        """Get templates in instantiation order."""
        self.analyze()
        return self.graph.get_instantiation_order()
    
    def get_template_rank(self, template_name: str) -> Optional[TemplateRank]:
        """Get rank of a specific template."""
        self.analyze()
        node = self.graph.nodes.get(template_name)
        return node.rank_desc.rank if node else None
    
    def get_base_templates(self) -> List[str]:
        """Get all base templates (no dependencies)."""
        self.analyze()
        base_nodes = self.graph.get_nodes_by_rank(TemplateRank.BASE)
        return [node.get_name() for node in base_nodes]
    
    def get_template_dependencies(self, template_name: str) -> Set[str]:
        """Get direct dependencies of a template."""
        return self.graph.get_template_dependencies(template_name)
    
    def get_all_dependencies(self, template_name: str) -> Set[str]:
        """Get all transitive dependencies of a template."""
        self.analyze()
        
        visited = set()
        
        def collect_deps(name: str) -> Set[str]:
            if name in visited:
                return set()
            
            visited.add(name)
            deps = self.graph.get_template_dependencies(name)
            
            all_deps = deps.copy()
            for dep in deps:
                all_deps.update(collect_deps(dep))
            
            return all_deps
        
        return collect_deps(template_name)
    
    def check_template_compatibility(self, template1: str, template2: str) -> bool:
        """Check if two templates can be used together."""
        self.analyze()
        
        # Check if either depends on the other
        deps1 = self.get_all_dependencies(template1)
        deps2 = self.get_all_dependencies(template2)
        
        # Templates are incompatible if they have conflicting dependencies
        # This is a simplified check - more sophisticated analysis needed
        return template1 not in deps2 and template2 not in deps1
    
    def get_errors(self) -> List[DMLError]:
        """Get topology analysis errors."""
        return self.errors
    
    def has_cycles(self) -> bool:
        """Check if template graph has circular dependencies."""
        self.analyze()
        return any(error.kind == DMLErrorKind.CIRCULAR_DEPENDENCY for error in self.errors)


def rank_templates(templates: Dict[str, Template]) -> Dict[str, TemplateRank]:
    """Rank templates by their dependencies."""
    analyzer = TopologyAnalyzer()
    
    # Add all templates
    for template in templates.values():
        analyzer.add_template(template)
    
    # Analyze topology
    analyzer.analyze()
    
    # Return ranks
    ranks = {}
    for template_name in templates:
        rank = analyzer.get_template_rank(template_name)
        ranks[template_name] = rank if rank else TemplateRank.BASE
    
    return ranks


def rank_templates_aux(templates: Dict[str, Template], 
                      errors: List[DMLError]) -> Tuple[Dict[str, TemplateRank], List[str]]:
    """Auxiliary function to rank templates and return instantiation order."""
    analyzer = TopologyAnalyzer()
    
    # Add all templates
    for template in templates.values():
        analyzer.add_template(template)
    
    # Analyze topology
    analyzer.analyze()
    
    # Collect errors
    errors.extend(analyzer.get_errors())
    
    # Get ranks
    ranks = {}
    for template_name in templates:
        rank = analyzer.get_template_rank(template_name)
        ranks[template_name] = rank if rank else TemplateRank.BASE
    
    # Get instantiation order
    order = analyzer.get_instantiation_order()
    
    return ranks, order


__all__ = [
    'TemplateRank', 'RankDesc', 'TemplateNode', 'DependencyEdge', 'TemplateGraph',
    'TopologyAnalyzer', 'rank_templates', 'rank_templates_aux'
]
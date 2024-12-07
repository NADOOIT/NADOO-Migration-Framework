"""Migration manager to handle codebase migrations."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Type, Optional, Set
from collections import defaultdict

from .base import Migration

class MigrationManager:
    """Manages the application of migrations."""
    
    def __init__(self, app_dir: str):
        """Initialize migration manager.
        
        Args:
            app_dir (str): Root directory of the application.
        """
        self.app_dir = Path(app_dir)
        self.migrations_dir = self.app_dir / 'migrations'
        self.migrations_file = self.app_dir / '.migration_state.json'
        self.migrations: Dict[str, Type[Migration]] = {}
        self.applied_migrations: Dict[str, dict] = self._load_applied_migrations()
        
    def _load_applied_migrations(self) -> Dict[str, dict]:
        """Load applied migrations from state file."""
        if not self.migrations_file.exists():
            return {}
        try:
            with open(self.migrations_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    
    def _save_applied_migrations(self) -> None:
        """Save applied migrations to state file."""
        with open(self.migrations_file, 'w') as f:
            json.dump(self.applied_migrations, f, indent=2)
    
    def register_migration(self, migration_class: Type[Migration]) -> None:
        """Register a migration class.
        
        Args:
            migration_class (Type[Migration]): Migration class to register.
        """
        migration = migration_class()
        self.migrations[migration.version] = migration_class
    
    def _get_migration_graph(self) -> Dict[str, Set[str]]:
        """Build migration dependency graph.
        
        Returns:
            Dict[str, Set[str]]: Graph representing migration dependencies.
        """
        graph = {}
        # First, create nodes for all migrations
        for version, migration_class in self.migrations.items():
            migration = migration_class()
            graph[migration.version] = set()
        
        # Then, add dependencies
        for version, migration_class in self.migrations.items():
            migration = migration_class()
            # Add all dependencies, even if they don't exist
            graph[migration.version] = set(migration.dependencies)
        return graph
    
    def _has_cycle(self, graph: Dict[str, Set[str]], node: str, visited: Set[str], stack: Set[str]) -> bool:
        """Check if graph has a cycle starting from node."""
        visited.add(node)
        stack.add(node)
        
        # Only check neighbors that exist in the graph
        for neighbor in graph.get(node, set()):
            if neighbor not in graph:
                continue
            if neighbor not in visited:
                if self._has_cycle(graph, neighbor, visited, stack):
                    return True
            elif neighbor in stack:
                return True
        
        stack.remove(node)
        return False
    
    def _topological_sort(self, graph: Dict[str, Set[str]]) -> List[str]:
        """Sort migrations topologically based on dependencies.
        
        Args:
            graph (Dict[str, Set[str]]): Graph representing migration dependencies.
        
        Returns:
            List[str]: List of migration versions in topological order.
            
        Raises:
            ValueError: If a circular dependency is detected.
        """
        # First check for cycles
        visited = set()
        stack = set()
        for node in graph:
            if node not in visited:
                if self._has_cycle(graph, node, visited, stack):
                    raise ValueError("Circular dependency detected")
        
        # Create a copy of the graph to avoid modifying it during iteration
        remaining = {k: set(v) for k, v in graph.items()}
        result = []
        
        while remaining:
            # Find all nodes with no dependencies or with only satisfied dependencies
            available = [n for n, d in remaining.items() if not (d - set(result))]
            if not available:
                # If there are no available nodes but the graph is not empty,
                # we have a circular dependency (should never happen as we check above)
                if remaining:
                    raise ValueError("Circular dependency detected")
                break
            
            # Add the first available node to the result
            node = sorted(available)[0]
            result.append(node)
            
            # Remove the node from the graph
            del remaining[node]
        
        return result
    
    def migrate(self, target_version: Optional[str] = None) -> None:
        """Run migrations up to target_version.
        
        Args:
            target_version (Optional[str]): Target version to migrate to. If None,
                                          run all pending migrations.
                                          
        Raises:
            ValueError: If target_version is not found.
        """
        graph = self._get_migration_graph()
        sorted_versions = self._topological_sort(graph)
        
        if target_version:
            if target_version not in self.migrations:
                raise ValueError(f"Target version {target_version} not found")
            target_idx = sorted_versions.index(target_version)
            sorted_versions = sorted_versions[:target_idx + 1]
        
        for version in sorted_versions:
            if version not in self.applied_migrations:
                migration_class = self.migrations[version]
                migration = migration_class()
                
                if migration.check_if_needed():
                    print(f"Applying migration {migration.__class__.__name__}...")
                    try:
                        migration.up()
                        self.applied_migrations[version] = migration.get_state()
                        self._save_applied_migrations()
                        print(f"Successfully applied migration {migration.__class__.__name__}")
                    except Exception as e:
                        print(f"Error applying migration {migration.__class__.__name__}: {e}")
                        self.rollback(1)
                        raise
    
    def rollback(self, steps: int = 1) -> None:
        """Rollback the last n migrations.
        
        Args:
            steps (int): Number of migrations to roll back.
        """
        if not self.applied_migrations:
            print("No migrations to rollback")
            return
            
        graph = self._get_migration_graph()
        sorted_versions = self._topological_sort(graph)
        applied_versions = [v for v in sorted_versions if v in self.applied_migrations]
        
        if not applied_versions:
            print("No applied migrations to rollback")
            return
            
        versions_to_rollback = applied_versions[-steps:]
        for version in reversed(versions_to_rollback):
            migration_class = self.migrations[version]
            migration = migration_class()
            
            print(f"Rolling back migration {migration.__class__.__name__}...")
            try:
                migration.down()
                del self.applied_migrations[version]
                self._save_applied_migrations()
                print(f"Successfully rolled back migration {migration.__class__.__name__}")
            except Exception as e:
                print(f"Error rolling back migration {migration.__class__.__name__}: {e}")
                raise

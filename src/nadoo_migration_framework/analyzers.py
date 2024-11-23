"""Project analyzers for detecting and analyzing different project types."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

from .functions import code_analysis, project_structure, dependency_analysis

class ProjectAnalyzer(ABC):
    """Base class for project analyzers."""

    def __init__(self, project_path: Path):
        """Initialize analyzer with project path.
        
        Args:
            project_path (Path): Path to the project root
        """
        self.project_path = project_path
        
    @abstractmethod
    def analyze(self) -> Dict[str, any]:
        """Analyze the project and return findings.
        
        Returns:
            Dict[str, any]: Analysis results including project type, structure, etc.
        """
        pass
    
    @abstractmethod
    def get_required_migrations(self) -> List[str]:
        """Determine required migrations based on analysis.
        
        Returns:
            List[str]: List of required migration identifiers
        """
        pass

class NADOOProjectAnalyzer(ProjectAnalyzer):
    """Analyzer for existing NADOO Framework projects."""
    
    def analyze(self) -> Dict[str, any]:
        results = {
            'project_type': 'nadoo',
            'version': None,
            'structure': project_structure.get_package_structure(self.project_path),
            'dependencies': dependency_analysis.analyze_project_dependencies(self.project_path),
            'code_analysis': self._analyze_code()
        }
        
        return results
    
    def get_required_migrations(self) -> List[str]:
        analysis = self.analyze()
        migrations = []
        
        # Add migrations based on version differences
        current_version = analysis.get('version')
        if current_version:
            # TODO: Compare with target NADOO version and add required migrations
            pass
            
        return migrations
    
    def _analyze_code(self) -> Dict[str, any]:
        """Analyze the codebase structure."""
        analysis = {
            'classes': [],
            'functions': [],
            'imports': set()
        }
        
        # Find all Python files
        python_files = project_structure.find_python_files(self.project_path)
        
        # Analyze each file
        for file_path in python_files:
            # Get classes and functions
            analysis['classes'].extend(code_analysis.find_class_definitions(file_path))
            analysis['functions'].extend(code_analysis.find_function_definitions(file_path))
            
            # Get imports
            analysis['imports'].update(code_analysis.extract_imports(file_path))
            
        return analysis

class NonNADOOProjectAnalyzer(ProjectAnalyzer):
    """Analyzer for non-NADOO projects to be migrated."""
    
    def analyze(self) -> Dict[str, any]:
        results = {
            'project_type': 'non-nadoo',
            'structure': project_structure.get_package_structure(self.project_path),
            'dependencies': dependency_analysis.analyze_project_dependencies(self.project_path),
            'entry_points': project_structure.find_entry_points(self.project_path),
            'code_analysis': self._analyze_code()
        }
        
        return results
    
    def get_required_migrations(self) -> List[str]:
        analysis = self.analyze()
        migrations = []
        
        # Add basic NADOO setup migration
        migrations.append('SetupNADOOBase')
        
        # Add migrations based on project structure
        if analysis['entry_points']:
            migrations.append('MigrateEntryPoints')
            
        # Add migrations based on dependencies
        if analysis['dependencies']['declared']['requirements.txt']:
            migrations.append('MigrateDependencies')
            
        return migrations
    
    def _analyze_code(self) -> Dict[str, any]:
        """Analyze the codebase structure."""
        analysis = {
            'classes': [],
            'functions': [],
            'imports': set(),
            'framework_hints': []
        }
        
        # Find all Python files
        python_files = project_structure.find_python_files(self.project_path)
        
        # Analyze each file
        for file_path in python_files:
            # Get classes and functions
            classes = code_analysis.find_class_definitions(file_path)
            functions = code_analysis.find_function_definitions(file_path)
            
            analysis['classes'].extend(classes)
            analysis['functions'].extend(functions)
            
            # Get imports
            imports = code_analysis.extract_imports(file_path)
            analysis['imports'].update(imports)
            
            # Look for framework hints in imports
            framework_imports = {
                'flask': 'Flask',
                'django': 'Django',
                'fastapi': 'FastAPI',
                'pyramid': 'Pyramid'
            }
            
            for imp in imports:
                base_package = imp.split('.')[0]
                if base_package in framework_imports:
                    analysis['framework_hints'].append(framework_imports[base_package])
                    
        return analysis

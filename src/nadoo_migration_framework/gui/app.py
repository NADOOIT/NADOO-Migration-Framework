"""GUI application for NADOO Migration Framework."""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional
from ..migrations.repository_scanner import RepositoryScanner
from ..migrations.dry_run import DryRunManager
from ..version import Version, ProjectVersion
from ..functions.project_structure_migrator import ProjectStructure

class ProjectRow:
    """GUI row for a project."""
    
    def __init__(self, parent: ttk.Frame, project: ProjectVersion, on_migrate=None):
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Project name
        ttk.Label(self.frame, text=project.project_name, width=30).pack(side=tk.LEFT)
        
        # Status
        status_frame = ttk.Frame(self.frame)
        status_frame.pack(side=tk.LEFT, padx=10)
        ttk.Label(status_frame, text=project.status).pack()
        
        # Migration button
        if project.needs_migration:
            self.migrate_btn = ttk.Button(
                self.frame, 
                text="Migrate",
                command=lambda: on_migrate(project) if on_migrate else None
            )
            self.migrate_btn.pack(side=tk.RIGHT)
        
        # Separator
        ttk.Separator(parent, orient='horizontal').pack(fill=tk.X, padx=5, pady=2)

class MigrationApp:
    """Main GUI application."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("NADOO Migration Framework")
        self.root.geometry("600x400")
        
        self.setup_ui()
        self.projects: Dict[str, ProjectVersion] = {}
    
    def setup_ui(self):
        """Set up the user interface."""
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X)
        
        ttk.Label(
            header_frame, 
            text="NADOO Migration Framework", 
            font=('Arial', 16, 'bold')
        ).pack(side=tk.LEFT)
        
        # Scan button
        self.scan_btn = ttk.Button(
            header_frame,
            text="Scan Repositories",
            command=self.scan_repositories
        )
        self.scan_btn.pack(side=tk.RIGHT)
        
        # Projects list
        self.projects_frame = ttk.Frame(main_frame)
        self.projects_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Column headers
        headers_frame = ttk.Frame(self.projects_frame)
        headers_frame.pack(fill=tk.X, padx=5)
        ttk.Label(headers_frame, text="Project", width=30).pack(side=tk.LEFT)
        ttk.Label(headers_frame, text="Status", width=20).pack(side=tk.LEFT, padx=10)
        ttk.Label(headers_frame, text="Actions", width=10).pack(side=tk.RIGHT)
        
        ttk.Separator(self.projects_frame, orient='horizontal').pack(fill=tk.X, pady=5)
        
        # Scrollable frame for projects
        self.canvas = tk.Canvas(self.projects_frame)
        scrollbar = ttk.Scrollbar(self.projects_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def scan_repositories(self):
        """Scan for repositories."""
        github_path = os.path.expanduser("~/Documents/GitHub")
        scanner = RepositoryScanner(github_path)
        
        try:
            repos = scanner.scan_repositories()
            
            # Clear existing projects
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()
            
            self.projects.clear()
            
            # Add new projects
            for repo in repos:
                project = ProjectVersion(
                    project_name=repo['name'],
                    current_version=None  # Will be determined by scanning project
                )
                self.projects[repo['name']] = project
                ProjectRow(self.scrollable_frame, project, self.migrate_project)
            
            if not repos:
                ttk.Label(
                    self.scrollable_frame,
                    text="No eligible repositories found",
                    font=('Arial', 10, 'italic')
                ).pack(pady=20)
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to scan repositories: {str(e)}")
    
    def migrate_project(self, project: ProjectVersion):
        """Migrate a project."""
        # First do a dry run
        try:
            dry_run = DryRunManager(project.project_name)
            results = dry_run.dry_run_all([])  # Add your migrations here
            
            # Show changes that would be made
            changes = "\n".join(
                f"- {change.action}: {change.path}"
                for result in results
                for change in result.changes
            )
            
            if messagebox.askyesno(
                "Confirm Migration",
                f"The following changes will be made:\n\n{changes}\n\nProceed?"
            ):
                # Perform actual migration
                pass  # Add actual migration code here
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to migrate {project.project_name}: {str(e)}")

def main():
    """Run the GUI application."""
    root = tk.Tk()
    app = MigrationApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()

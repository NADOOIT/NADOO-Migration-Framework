"""NADOO Migration Framework GUI window."""

import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import asyncio
import os
import shutil
from datetime import datetime
from pathlib import Path

class MigrationStep:
    def __init__(self, title, description, action_func, rollback_func=None):
        self.title = title
        self.description = description
        self.action_func = action_func
        self.rollback_func = rollback_func
        self.status = "pending"  # pending, in_progress, completed, failed
        
class MigrationWindow(toga.MainWindow):
    def __init__(self, title, project_path, changes):
        """Initialize migration window.
        
        Args:
            title (str): Window title
            project_path (Path): Path to project to migrate
            changes (list): List of changes to apply
        """
        super().__init__(title=title)
        self.project_path = Path(project_path)
        self.backup_path = self.project_path.parent / f"{self.project_path.name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.changes = changes
        self.steps = self._create_migration_steps()
        self.current_step = 0
        self.is_migrating = False
        
        # Create main box
        main_box = toga.Box(style=Pack(direction=COLUMN, padding=10))
        
        # Add header
        header = toga.Box(style=Pack(direction=COLUMN, padding=(0, 0, 10, 0)))
        title_label = toga.Label(
            'NADOO Migration Framework',
            style=Pack(font_size=20, padding=(0, 0, 5, 0))
        )
        subtitle = toga.Label(
            f'Project: {self.project_path}',
            style=Pack(font_size=14, padding=(0, 0, 10, 0))
        )
        header.add(title_label)
        header.add(subtitle)
        
        # Create steps list
        self.steps_box = toga.Box(style=Pack(direction=COLUMN, padding=5))
        self._update_steps_display()
        
        # Create buttons
        button_box = toga.Box(style=Pack(direction=ROW, padding=(10, 0)))
        self.start_button = toga.Button(
            'Start Migration',
            on_press=self.start_migration,
            style=Pack(padding=(0, 5))
        )
        self.cancel_button = toga.Button(
            'Cancel',
            on_press=self.cancel_migration,
            style=Pack(padding=(0, 5))
        )
        button_box.add(self.start_button)
        button_box.add(self.cancel_button)
        
        # Add components to main box
        main_box.add(header)
        main_box.add(self.steps_box)
        main_box.add(button_box)
        
        self.content = main_box
        
        # Create toolbar
        self.toolbar = toga.Toolbar()
        
    def _create_migration_steps(self):
        """Create list of migration steps."""
        steps = []
        
        # Add backup step
        steps.append(MigrationStep(
            "Create Backup",
            "Create backup of current project",
            self._create_backup,
            self._rollback_backup
        ))
        
        # Add framework steps
        for change in self.changes:
            steps.append(MigrationStep(
                change,
                f"Apply change: {change}",
                lambda c=change: self._apply_change(c)
            ))
            
        return steps
        
    def _update_steps_display(self):
        """Update the display of migration steps."""
        self.steps_box.remove(*self.steps_box.children)
        
        for step in self.steps:
            step_box = toga.Box(style=Pack(direction=ROW, padding=(0, 0, 5, 0)))
            
            # Add status indicator
            status_colors = {
                "pending": "#808080",  # Gray
                "in_progress": "#FFA500",  # Orange
                "completed": "#008000",  # Green
                "failed": "#FF0000"  # Red
            }
            status = toga.Label(
                "●",
                style=Pack(
                    color=status_colors[step.status],
                    font_size=16,
                    padding=(0, 5, 0, 5)
                )
            )
            
            # Add step title
            title = toga.Label(
                step.title,
                style=Pack(padding=(0, 5, 0, 0))
            )
            
            step_box.add(status)
            step_box.add(title)
            self.steps_box.add(step_box)
            
    async def start_migration(self, widget):
        """Start the migration process."""
        if self.is_migrating:
            return
            
        self.is_migrating = True
        self.start_button.enabled = False
        self.cancel_button.enabled = False
        
        try:
            for step in self.steps:
                if not self.is_migrating:
                    break
                    
                step.status = "in_progress"
                self._update_steps_display()
                
                try:
                    await step.action_func()
                    step.status = "completed"
                except Exception as e:
                    step.status = "failed"
                    # Rollback all completed steps
                    for completed_step in reversed([s for s in self.steps if s.status == "completed"]):
                        if completed_step.rollback_func:
                            await completed_step.rollback_func()
                    break
                    
                self._update_steps_display()
                await asyncio.sleep(0.1)  # Allow GUI to update
                
            if all(step.status == "completed" for step in self.steps):
                self.main_window.info_dialog(
                    "Migration Complete",
                    "Project has been successfully migrated!"
                )
            elif not self.is_migrating:
                self.main_window.info_dialog(
                    "Migration Cancelled",
                    "Migration process was cancelled."
                )
            else:
                self.main_window.error_dialog(
                    "Migration Failed",
                    "An error occurred during migration. Changes have been rolled back."
                )
                
        finally:
            self.is_migrating = False
            self.start_button.enabled = True
            self.cancel_button.enabled = True
            
    def cancel_migration(self, widget):
        """Cancel the migration process."""
        if self.is_migrating:
            self.is_migrating = False
        else:
            self.close()
            
    def get_progress(self) -> str:
        """Get migration progress as a string."""
        completed = sum(1 for step in self.steps if step.status == "completed")
        total = len(self.steps)
        return f"{completed} of {total} steps completed"
        
    async def _create_backup(self):
        """Create backup of project."""
        shutil.copytree(self.project_path, self.backup_path)
        
    async def _rollback_backup(self):
        """Restore from backup."""
        if self.backup_path.exists():
            shutil.rmtree(self.project_path)
            shutil.copytree(self.backup_path, self.project_path)
            shutil.rmtree(self.backup_path)
            
    async def _apply_change(self, change):
        """Apply a single migration change."""
        # TODO: Implement actual change application
        await asyncio.sleep(1)  # Simulate work

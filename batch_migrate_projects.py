#!/usr/bin/env python3
import os
import shutil
from pathlib import Path
import subprocess
import logging
import json
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('migration.log'), logging.StreamHandler()],
)

# Configuration
GITHUB_FOLDER = "/Users/christophbackhaus/Documents/GitHub"
SD_CARD_BASE = "/Volumes/SD-CARD-"
TARGET_FOLDER_NAME = "NADOOIT_MIGRATED"
INDEX_FILE = "nadoo_projects_index.json"


class ProjectIndex:
    def __init__(self):
        self.index = self.load_index()

    def load_index(self):
        if os.path.exists(INDEX_FILE):
            with open(INDEX_FILE, 'r') as f:
                return json.load(f)
        return {"last_updated": datetime.now().isoformat(), "projects": {}, "sd_cards": {}}

    def save_index(self):
        self.index["last_updated"] = datetime.now().isoformat()
        with open(INDEX_FILE, 'w') as f:
            json.dump(self.index, f, indent=2)

    def add_project(self, project_name, sd_card, size_mb, status):
        self.index["projects"][project_name] = {
            "location": sd_card,
            "size_mb": size_mb,
            "status": status,
            "migration_date": datetime.now().isoformat(),
        }

        if sd_card not in self.index["sd_cards"]:
            self.index["sd_cards"][sd_card] = {"projects": [], "total_size_mb": 0}

        self.index["sd_cards"][sd_card]["projects"].append(project_name)
        self.index["sd_cards"][sd_card]["total_size_mb"] += size_mb
        self.save_index()


def is_git_repo(path):
    """Check if the given path is a git repository."""
    return os.path.isdir(os.path.join(path, '.git'))


def clear_sd_card(sd_card_path):
    """Clear the target folder on the SD card."""
    target_folder = os.path.join(sd_card_path, TARGET_FOLDER_NAME)
    if os.path.exists(target_folder):
        shutil.rmtree(target_folder)
    os.makedirs(target_folder, exist_ok=True)
    logging.info(f"Cleared and prepared {target_folder}")


def find_available_sd_card(required_space):
    """Find an SD card with enough space."""
    for i in range(1, 100):  # Check SD-CARD-01 through SD-CARD-99
        card_num = f"{i:02d}"
        card_path = f"{SD_CARD_BASE}{card_num}"

        if not os.path.exists(card_path):
            continue

        target_folder = os.path.join(card_path, TARGET_FOLDER_NAME)
        os.makedirs(target_folder, exist_ok=True)

        stats = os.statvfs(target_folder)
        free_space = stats.f_frsize * stats.f_bavail

        if free_space >= required_space:
            return card_num, target_folder

    return None, None


def get_directory_size(path):
    """Get the size of a directory excluding .git folders."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        if '.git' in dirpath:
            continue
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size


def copy_project(src, dst):
    """Copy project files excluding .git directory."""

    def ignore_patterns(path, names):
        return [n for n in names if n == '.git' or n.endswith('.pyc') or '__pycache__' in n]

    shutil.copytree(src, dst, ignore=ignore_patterns, symlinks=True)


def migrate_project(project_path, project_index, target_folder, card_num):
    """Migrate a single project."""
    project_name = os.path.basename(project_path)
    target_project_path = os.path.join(target_folder, project_name)

    logging.info(f"Starting migration of {project_name} to SD-CARD-{card_num}")

    try:
        # Skip if project already exists
        if os.path.exists(target_project_path):
            logging.warning(
                f"Project {project_name} already exists in SD-CARD-{card_num}. Skipping..."
            )
            project_index.add_project(project_name, f"SD-CARD-{card_num}", 0, "already_exists")
            return

        # Copy project to target location
        copy_project(project_path, target_project_path)
        logging.info(f"Successfully copied {project_name} to SD-CARD-{card_num}")

        # Run nadoo migrate on the copied project
        try:
            subprocess.run(
                ['nadoo-migrate'],
                cwd=target_project_path,
                check=True,
                capture_output=True,
                text=True,
            )
            logging.info(f"Successfully migrated {project_name}")
            project_index.add_project(project_name, f"SD-CARD-{card_num}", 0, "success")

        except subprocess.CalledProcessError as e:
            logging.error(f"Migration failed for {project_name}: {e.stderr}")
            project_index.add_project(project_name, f"SD-CARD-{card_num}", 0, "failed_migration")

    except Exception as e:
        logging.error(f"Error processing {project_name}: {str(e)}")
        project_index.add_project(project_name, None, 0, "failed_error")
        # Clean up failed migration
        if os.path.exists(target_project_path):
            shutil.rmtree(target_project_path)


def main():
    """Main function to process all projects."""
    try:
        project_index = ProjectIndex()

        # Clear both SD cards
        for i in range(1, 3):  # Assuming SD-CARD-01 and SD-CARD-02
            card_path = f"{SD_CARD_BASE}{i:02d}"
            clear_sd_card(card_path)

        # Find a suitable SD card for all projects
        github_path = Path(GITHUB_FOLDER)
        total_required_space = sum(
            get_directory_size(str(d))
            for d in github_path.iterdir()
            if d.is_dir() and is_git_repo(str(d))
        )
        card_num, target_folder = find_available_sd_card(total_required_space)

        if not card_num:
            logging.error("No single SD card with enough space for all projects.")
            return

        logging.info(f"Using SD-CARD-{card_num} for all projects.")

        # Process each project
        for project_path in github_path.iterdir():
            if project_path.is_dir() and is_git_repo(str(project_path)):
                migrate_project(str(project_path), project_index, target_folder, card_num)

        logging.info("Migration process completed!")

    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")


if __name__ == "__main__":
    main()

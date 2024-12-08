"""NADOO Migration Framework main entry point."""

import sys
from pathlib import Path
from .cli import migrate
from nadoo_migration_framework.app import main


if __name__ == '__main__':
    print("Starting main loop...")
    main().main_loop()
    print("Main loop started.")

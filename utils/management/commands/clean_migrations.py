import os
import shutil
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Deletes all migration files and __pycache__ directories except __init__.py"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        base_dir = settings.BASE_DIR

        cleaned_apps = []
        ignored_dirs = ["venv", "moreV", ".git", "__pycache__", "node_modules"]

        # Get all apps from INSTALLED_APPS that are local
        django_apps = ["django.contrib", "rest_framework"]
        local_apps = [
            app
            for app in settings.INSTALLED_APPS
            if not any(app.startswith(prefix) for prefix in django_apps)
        ]

        self.stdout.write(
            self.style.WARNING("Looking for migration files in these directories:")
        )
        for app in local_apps:
            self.stdout.write(f"  - {app}")

        # Walk through all directories
        for root, dirs, files in os.walk(base_dir):
            # Skip directories we don't care about
            dirs[:] = [d for d in dirs if d not in ignored_dirs]

            # If this is a migrations directory
            if os.path.basename(root) == "migrations":
                app_name = os.path.basename(os.path.dirname(root))
                cleaned_apps.append(app_name)

                # Process migration files
                for file in files:
                    # Skip __init__.py
                    if file == "__init__.py":
                        continue

                    # Skip files that aren't Python files
                    if not file.endswith(".py"):
                        continue

                    file_path = os.path.join(root, file)
                    if dry_run:
                        self.stdout.write(f"Would delete: {file_path}")
                    else:
                        try:
                            os.remove(file_path)
                            self.stdout.write(f"Deleted: {file_path}")
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f"Error deleting {file_path}: {e}")
                            )

                # Handle __pycache__ directory
                pycache_dir = os.path.join(root, "__pycache__")
                if os.path.exists(pycache_dir):
                    if dry_run:
                        self.stdout.write(f"Would delete directory: {pycache_dir}")
                    else:
                        try:
                            shutil.rmtree(pycache_dir)
                            self.stdout.write(f"Deleted directory: {pycache_dir}")
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f"Error deleting {pycache_dir}: {e}")
                            )

                # Ensure __init__.py exists
                init_path = os.path.join(root, "__init__.py")
                if not os.path.exists(init_path):
                    if dry_run:
                        self.stdout.write(f"Would create: {init_path}")
                    else:
                        try:
                            open(init_path, "w").close()
                            self.stdout.write(f"Created: {init_path}")
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f"Error creating {init_path}: {e}")
                            )

        # Summary
        cleaned_apps = list(set(cleaned_apps))
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Dry run completed! Would clean migrations in {len(cleaned_apps)} apps."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully cleaned migrations in {len(cleaned_apps)} apps."
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    "Now run 'python manage.py makemigrations' to create fresh migrations."
                )
            )

        if cleaned_apps:
            self.stdout.write("Cleaned apps:")
            for app in sorted(cleaned_apps):
                self.stdout.write(f"  - {app}")

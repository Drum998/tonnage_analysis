"""Pytest configuration and shared fixtures."""
import os

# Set required env vars before app module is imported (load_dotenv won't override existing)
for key, default in [
    ("DB_HOST", "localhost"),
    ("DB_USER", "test"),
    ("DB_PASSWORD", "test"),
    ("DB_DATABASE", "test"),
]:
    os.environ.setdefault(key, default)

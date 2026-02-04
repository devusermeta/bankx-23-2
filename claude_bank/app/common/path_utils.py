"""
Path Utilities for Environment-Aware Path Resolution

This module provides utilities to resolve file paths correctly in both:
- Local development environment
- Docker container environment

The key difference:
- Local: Files are in the project root (claude_bank/)
- Docker: Files are copied to /app/ directory
"""

import os
from pathlib import Path




# def get_base_dir() -> Path:
#     """
#     Get the base directory for the application.
    
#     This function detects whether the code is running in a Docker container
#     or in a local development environment and returns the appropriate base path.
    
#     Returns:
#         Path: Base directory (/app/ in Docker, project root locally)
#     """
#     if os.path.exists("/.dockerenv"):
#         # Running in Docker - data is at /app/
#         return Path("/app")
#     else:
#         # Running locally - need to go up to project root
#         # This assumes the file calling this is somewhere under app/
#         # Most MCP servers are at: app/business-api/python/{service}/
#         # So we need to go up 5 levels to reach project root
#         # But we'll use an environment variable or working directory approach
        
#         # Try to find project root by looking for a marker file
#         current = Path(__file__).resolve()
        
#         # Go up until we find schemas/ directory (project root marker)
#         for parent in current.parents:
#             if (parent / "schemas").exists() and (parent / "app").exists():
#                 return parent
        
#         # Fallback: assume we're in app/common/, go up 2 levels
#         return Path(__file__).parent.parent.parent






def get_base_dir() -> Path:
    """
    Get the base directory for the application.

    Handles both local development and containerized environments
    (Docker, Azure Container Apps).

    Returns:
        Path: Base directory path
    """
    # 1) Explicit override via environment variable (optional escape hatch)
    override = os.getenv("BANKX_BASE_DIR")
    if override:
        p = Path(override)
        if p.exists():
            return p

    # 2) Common container layout: our WORKDIR is /app and we copy folders there
    app_dir = Path("/app")
    if app_dir.exists() and (app_dir / "schemas").exists():
        return app_dir

    # 3) Docker detection (some platforms don't expose /.dockerenv)
    if os.path.exists("/.dockerenv"):
        return app_dir

    # 4) Local dev: walk up until we find project root containing both app/ and schemas/
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "schemas").exists() and (parent / "app").exists():
            return parent

    # 5) Conservative fallback: assume this file lives in app/common/
    # Going up ONE level gives us /.../app (not /)
    maybe_app = Path(__file__).resolve().parent.parent
    if (maybe_app / "schemas").exists():
        return maybe_app
    return maybe_app  # final fallback


def get_schemas_dir() -> Path:
    """Get the schemas directory path."""
    return get_base_dir() / "schemas"


def get_dynamic_data_dir() -> Path:
    """Get the dynamic_data directory path."""
    return get_base_dir() / "dynamic_data"


def get_data_dir() -> Path:
    """Get the data directory path."""
    return get_base_dir() / "data"


def get_csv_data_dir() -> Path:
    """Get the CSV synthetic data directory path."""
    return get_schemas_dir() / "tools-sandbox" / "uc1_synthetic_data"

#!/usr/bin/env python3
"""
Check required packages are installed and print versions
Exit non-zero if critical packages missing
"""

import sys
import importlib
from typing import List, Tuple

# Critical packages that must be present
CRITICAL_PACKAGES = [
    "fastapi",
    "uvicorn",
    "pydantic",
    "aiohttp",
    "httpx",
    "aioarango",
    "motor",
    "pymongo",
    "arango",
    "langchain",
    "numpy",
]

# Optional packages (warn but don't fail)
OPTIONAL_PACKAGES = [
    "sentence_transformers",
    "langraph",
    "crew_ai",
    "einops",
    "chromadb",
    "faiss",
    "pytest",
    "pytest_asyncio",
    "respx",
    "aioresponses",
    "mongomock",
    "black",
    "flake8",
    "mypy",
]


def check_package(package_name: str) -> Tuple[bool, str]:
    """Check if package is available and return version"""
    try:
        module = importlib.import_module(package_name.replace("-", "_"))
        version = getattr(module, "__version__", "unknown")
        return True, version
    except ImportError:
        return False, "not installed"


def main():
    print("=== Package Installation Check ===")

    missing_critical = []
    missing_optional = []

    print("\nCritical packages:")
    for pkg in CRITICAL_PACKAGES:
        installed, version = check_package(pkg)
        status = "OK" if installed else "MISSING"
        print(f"  [{status}] {pkg}: {version}")
        if not installed:
            missing_critical.append(pkg)

    print("\nOptional packages:")
    for pkg in OPTIONAL_PACKAGES:
        installed, version = check_package(pkg)
        status = "OK" if installed else "WARN"
        print(f"  [{status}] {pkg}: {version}")
        if not installed:
            missing_optional.append(pkg)

    # Summary
    print(f"\n=== Summary ===")
    print(f"Critical packages missing: {len(missing_critical)}")
    print(f"Optional packages missing: {len(missing_optional)}")

    if missing_critical:
        print(f"\nCRITICAL PACKAGES MISSING: {', '.join(missing_critical)}")
        return 1

    if missing_optional:
        print(f"\nOptional packages missing: {', '.join(missing_optional)}")

    print("All critical packages installed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

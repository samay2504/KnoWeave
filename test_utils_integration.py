#!/usr/bin/env python3
"""
Test script for server/utils package integration
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "server"))

# Apply warning suppression
from scripts.warning_suppression import suppress_all_warnings, configure_clean_logging
suppress_all_warnings()
configure_clean_logging()

print("🧪 TESTING SERVER/UTILS PACKAGE INTEGRATION")
print("=" * 60)

def test_import(module_name, item_name=None):
    """Test importing a module or specific item"""
    try:
        if item_name:
            exec(f"from {module_name} import {item_name}")
            print(f"✅ {module_name}.{item_name}: SUCCESS")
        else:
            exec(f"import {module_name}")
            print(f"✅ {module_name}: SUCCESS")
        return True
    except Exception as e:
        print(f"❌ {module_name}{('.' + item_name) if item_name else ''}: FAILED - {e}")
        return False

# Test individual modules
success_count = 0
total_tests = 0

print("\n📦 TESTING INDIVIDUAL MODULES:")
print("-" * 40)

# Test chunker module
total_tests += 1
if test_import("server.utils.chunker"):
    success_count += 1

total_tests += 1
if test_import("server.utils.chunker", "TextChunker"):
    success_count += 1

total_tests += 1
if test_import("server.utils.chunker", "TextChunk"):
    success_count += 1

total_tests += 1
if test_import("server.utils.chunker", "chunk_text"):
    success_count += 1

# Test embeddings module
total_tests += 1
if test_import("server.utils.embeddings"):
    success_count += 1

total_tests += 1
if test_import("server.utils.embeddings", "get_embeddings"):
    success_count += 1

# Test logging module
total_tests += 1
if test_import("server.utils.logging_cfg"):
    success_count += 1

total_tests += 1
if test_import("server.utils.logging_cfg", "setup_logging"):
    success_count += 1

total_tests += 1
if test_import("server.utils.logging_cfg", "get_logger"):
    success_count += 1

# Test schemas module
total_tests += 1
if test_import("server.utils.schemas"):
    success_count += 1

total_tests += 1
if test_import("server.utils.schemas", "BaseSchema"):
    success_count += 1

total_tests += 1
if test_import("server.utils.schemas", "TopicType"):
    success_count += 1

# Test package imports
print("\n📦 TESTING PACKAGE IMPORTS:")
print("-" * 40)

total_tests += 1
if test_import("server.utils"):
    success_count += 1

# Test importing from __init__.py
try:
    from server.utils import TextChunker, TextChunk, chunk_text
    print("✅ server.utils chunker exports: SUCCESS")
    success_count += 1
except Exception as e:
    print(f"❌ server.utils chunker exports: FAILED - {e}")
total_tests += 1

try:
    from server.utils import BaseSchema, TopicType, SuggestionMode
    print("✅ server.utils schema exports: SUCCESS")
    success_count += 1
except Exception as e:
    print(f"❌ server.utils schema exports: FAILED - {e}")
total_tests += 1

try:
    from server.utils import setup_logging, get_logger
    print("✅ server.utils logging exports: SUCCESS")
    success_count += 1
except Exception as e:
    print(f"❌ server.utils logging exports: FAILED - {e}")
total_tests += 1

# Test embeddings (might be commented out)
try:
    from server.utils import EmbeddingsProvider, EmbeddingResult
    print("✅ server.utils embeddings exports: SUCCESS")
    success_count += 1
except Exception as e:
    print(f"⚠️  server.utils embeddings exports: SKIPPED - {e}")
    # Don't count as failure since it's intentionally commented out
total_tests += 1

print("\n🧪 FUNCTIONAL TESTING:")
print("-" * 40)

# Test TextChunker functionality
try:
    from server.utils import TextChunker
    chunker = TextChunker(chunk_size=100, overlap=20)
    test_text = "This is a test document. It has multiple sentences. We want to test chunking functionality."
    chunks = chunker.chunk_text(test_text)
    print(f"✅ TextChunker functionality: SUCCESS ({len(chunks)} chunks created)")
    success_count += 1
except Exception as e:
    print(f"❌ TextChunker functionality: FAILED - {e}")
total_tests += 1

# Test embeddings functionality
try:
    from server.utils.embeddings import get_embeddings
    test_texts = ["Hello world", "Test embeddings"]
    embeddings = get_embeddings(test_texts)
    print(f"✅ Embeddings functionality: SUCCESS ({len(embeddings)} embeddings created)")
    success_count += 1
except Exception as e:
    print(f"❌ Embeddings functionality: FAILED - {e}")
total_tests += 1

# Test logging functionality
try:
    from server.utils import setup_logging, get_logger
    setup_logging()
    logger = get_logger("test")
    logger.info("Test log message")
    print("✅ Logging functionality: SUCCESS")
    success_count += 1
except Exception as e:
    print(f"❌ Logging functionality: FAILED - {e}")
total_tests += 1

# Test schema functionality
try:
    from server.utils import BaseSchema, TopicType
    
    # Test enum
    topic = TopicType.STORY
    print(f"✅ Schema enums: SUCCESS (topic: {topic})")
    
    # Test BaseSchema (if available)
    if hasattr(BaseSchema, 'dict'):
        print("✅ Schema BaseSchema: SUCCESS (Pydantic available)")
    else:
        print("✅ Schema BaseSchema: SUCCESS (Dataclass fallback)")
    
    success_count += 1
except Exception as e:
    print(f"❌ Schema functionality: FAILED - {e}")
total_tests += 1

print("\n" + "=" * 60)
print(f"📊 UTILS PACKAGE TEST SUMMARY:")
print(f"   Tests Passed: {success_count}/{total_tests}")
print(f"   Success Rate: {(success_count/total_tests)*100:.1f}%")

if success_count == total_tests:
    print("🎉 ALL UTILS TESTS PASSED! Package is well integrated.")
else:
    print("⚠️  Some tests failed. Check the issues above.")

print("\n🔍 PACKAGE STRUCTURE VALIDATION:")
print("-" * 40)

# Check __all__ exports match actual imports
try:
    import server.utils
    
    # Get __all__ from the module
    if hasattr(server.utils, '__all__'):
        declared_exports = server.utils.__all__
        print(f"✅ __all__ declaration found: {len(declared_exports)} items")
        
        # Test each declared export
        missing_exports = []
        for export in declared_exports:
            if not hasattr(server.utils, export):
                missing_exports.append(export)
        
        if missing_exports:
            print(f"⚠️  Missing exports in __all__: {missing_exports}")
        else:
            print("✅ All declared exports are available")
    else:
        print("⚠️  No __all__ declaration found")
        
except Exception as e:
    print(f"❌ Package structure validation failed: {e}")

print("\n✨ Utils package integration test complete!")

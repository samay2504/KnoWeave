"""
Migration and testing script for production-ready import system
Run this to test the new import system before full deployment
"""

import sys
from pathlib import Path

# Add project root to path for testing
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_core_system():
    """Test the new core import system"""
    print("🔧 Testing Core Import System...")
    
    try:
        from server.core import PROJECT_ROOT, SERVER_ROOT, get_project_root
        print(f"✅ Core system loaded successfully")
        print(f"   Project Root: {PROJECT_ROOT}")
        print(f"   Server Root: {SERVER_ROOT}")
        
        from server.core.imports import import_manager, optional_import
        print(f"✅ Import manager loaded successfully")
        
        from server.core.config import config, load_config
        print(f"✅ Configuration system loaded successfully")
        print(f"   Environment: {config.environment}")
        print(f"   Database Mode: {config.database_mode}")
        
        return True
    except Exception as e:
        print(f"❌ Core system test failed: {e}")
        return False

def test_dependencies():
    """Test the new dependency system"""
    print("\n🔧 Testing Dependency System...")
    
    try:
        from server.dependencies import ProductionDependencyContainer, get_container
        print(f"✅ Production dependency container loaded")
        
        # Test container creation
        container = ProductionDependencyContainer()
        print(f"✅ Container created successfully")
        print(f"   Config loaded: {type(container.config).__name__}")
        
        return True
    except Exception as e:
        print(f"❌ Dependency system test failed: {e}")
        return False

def test_backward_compatibility():
    """Test that old imports still work during transition"""
    print("\n🔧 Testing Backward Compatibility...")
    
    try:
        # Test old import patterns still work
        from server.utils.logging_cfg import get_logger
        logger = get_logger("test")
        print(f"✅ Logging system compatible")
        
        # Test optional imports
        try:
            from server.server_config import ServerConfig
            config = ServerConfig()
            print(f"✅ ServerConfig backward compatible")
        except ImportError:
            print(f"ℹ️  ServerConfig using fallback (expected during transition)")
        
        return True
    except Exception as e:
        print(f"❌ Backward compatibility test failed: {e}")
        return False

def test_app_import():
    """Test that the main app can still be imported"""
    print("\n🔧 Testing App Import...")
    
    try:
        # This is the critical test - can we still import the main app?
        from server.app import create_app
        print(f"✅ Main app can be imported")
        
        return True
    except Exception as e:
        print(f"❌ App import test failed: {e}")
        print(f"   This might be expected during transition - check manually")
        return False

def generate_migration_report():
    """Generate a report on what needs to be migrated"""
    print("\n📋 Migration Report:")
    print("=" * 50)
    
    # Find all Python files with import statements
    server_dir = Path(__file__).parent / "server"
    python_files = list(server_dir.rglob("*.py"))
    
    files_to_update = []
    for file_path in python_files:
        if file_path.name.startswith('__pycache__'):
            continue
            
        try:
            content = file_path.read_text(encoding='utf-8')
            # Look for problematic import patterns
            problematic_patterns = [
                'from server.server_config import',
                'from server.db.mongo_client import', 
                'from server.db.arango_client import',
                'from .server_config import',
                'from .db.mongo_client import',
                'from .db.arango_client import'
            ]
            
            has_problematic_imports = any(pattern in content for pattern in problematic_patterns)
            if has_problematic_imports:
                files_to_update.append(file_path.relative_to(server_dir))
                
        except Exception:
            continue
    
    if files_to_update:
        print(f"📝 Files that may need import updates:")
        for file_path in files_to_update:
            print(f"   • {file_path}")
    else:
        print(f"✅ No files found with problematic imports")
    
    print(f"\n📊 Summary:")
    print(f"   • Total Python files: {len(python_files)}")
    print(f"   • Files needing updates: {len(files_to_update)}")
    print(f"   • Migration status: {'⚠️ Needs work' if files_to_update else '✅ Ready'}")

def main():
    """Run all tests and generate migration report"""
    print("🚀 Production Import System Migration Test")
    print("=" * 50)
    
    tests = [
        test_core_system,
        test_dependencies, 
        test_backward_compatibility,
        test_app_import
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    generate_migration_report()
    
    print(f"\n🎯 Overall Results:")
    print(f"   Tests passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print(f"   Status: ✅ Ready for production deployment")
    elif any(results):
        print(f"   Status: ⚠️ Partial success - continue migration")
    else:
        print(f"   Status: ❌ Migration needs work")
    
    print(f"\n💡 Next Steps:")
    if all(results):
        print(f"   • Update remaining files to use new import system")
        print(f"   • Test server startup with new system")
        print(f"   • Deploy to production")
    else:
        print(f"   • Fix failing tests")
        print(f"   • Review import patterns in flagged files")
        print(f"   • Test incrementally")

if __name__ == "__main__":
    main()

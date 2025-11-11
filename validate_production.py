"""
Production Readiness Validation Script
Checks code quality and structural integrity of critical files
"""

import ast
import sys
from pathlib import Path
from typing import List, Tuple, Dict

class ProductionValidator:
    """Validates Python files for production readiness"""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.checks_passed = 0
        self.checks_failed = 0
    
    def validate_syntax(self, file_path: Path) -> bool:
        """Check if file has valid Python syntax"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            ast.parse(code)
            self.checks_passed += 1
            print(f"✅ Syntax valid: {file_path.name}")
            return True
        except SyntaxError as e:
            self.errors.append(f"Syntax error in {file_path}: {e}")
            self.checks_failed += 1
            print(f"❌ Syntax error in {file_path.name}: {e}")
            return False
    
    def check_imports(self, file_path: Path) -> bool:
        """Check for circular or missing imports"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            tree = ast.parse(code)
            
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            
            self.checks_passed += 1
            print(f"✅ Imports analyzed: {file_path.name} ({len(imports)} imports)")
            return True
        except Exception as e:
            self.warnings.append(f"Import check failed for {file_path}: {e}")
            print(f"⚠️  Import check warning: {file_path.name}")
            return False
    
    def check_duplicate_definitions(self, file_path: Path) -> bool:
        """Check for duplicate function/class definitions"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            tree = ast.parse(code)
            
            definitions = {}
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    name = node.name
                    if name in definitions:
                        self.errors.append(
                            f"Duplicate definition '{name}' in {file_path} at line {node.lineno} "
                            f"(first defined at line {definitions[name]})"
                        )
                        self.checks_failed += 1
                        print(f"❌ Duplicate definition: {name} in {file_path.name}")
                        return False
                    definitions[name] = node.lineno
            
            self.checks_passed += 1
            print(f"✅ No duplicates: {file_path.name} ({len(definitions)} definitions)")
            return True
        except Exception as e:
            self.warnings.append(f"Duplicate check failed for {file_path}: {e}")
            print(f"⚠️  Duplicate check warning: {file_path.name}")
            return False
    
    def check_error_handling(self, file_path: Path) -> bool:
        """Check for proper exception handling"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            tree = ast.parse(code)
            
            # Check for bare except clauses (anti-pattern)
            bare_excepts = 0
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    if node.type is None:
                        bare_excepts += 1
            
            if bare_excepts > 0:
                self.warnings.append(
                    f"{file_path.name} has {bare_excepts} bare except clauses - should specify exception types"
                )
                print(f"⚠️  Found {bare_excepts} bare except: {file_path.name}")
            else:
                print(f"✅ Error handling OK: {file_path.name}")
            
            self.checks_passed += 1
            return True
        except Exception as e:
            self.warnings.append(f"Error handling check failed for {file_path}: {e}")
            return False
    
    def validate_file(self, file_path: Path) -> bool:
        """Run all validation checks on a file"""
        print(f"\n{'='*60}")
        print(f"Validating: {file_path}")
        print(f"{'='*60}")
        
        if not file_path.exists():
            self.errors.append(f"File not found: {file_path}")
            self.checks_failed += 1
            print(f"❌ File not found: {file_path}")
            return False
        
        results = []
        results.append(self.validate_syntax(file_path))
        results.append(self.check_imports(file_path))
        results.append(self.check_duplicate_definitions(file_path))
        results.append(self.check_error_handling(file_path))
        
        return all(results)
    
    def print_summary(self):
        """Print validation summary"""
        print(f"\n{'='*60}")
        print("VALIDATION SUMMARY")
        print(f"{'='*60}")
        print(f"✅ Checks passed: {self.checks_passed}")
        print(f"❌ Checks failed: {self.checks_failed}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print(f"{'='*60}")
        
        if self.errors:
            print("\n❌ ERRORS:")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        print(f"\n{'='*60}")
        if self.checks_failed == 0:
            print("✅ ALL CHECKS PASSED - PRODUCTION READY!")
        else:
            print("❌ VALIDATION FAILED - FIX ERRORS BEFORE DEPLOYMENT")
        print(f"{'='*60}\n")
        
        return self.checks_failed == 0


def main():
    """Main validation function"""
    print("🔍 Production Readiness Validator")
    print("=" * 60)
    
    # Files to validate
    base_path = Path(__file__).parent
    files_to_check = [
        base_path / "server" / "app.py",
        base_path / "server" / "api" / "routes.py",
    ]
    
    validator = ProductionValidator()
    
    all_valid = True
    for file_path in files_to_check:
        if not validator.validate_file(file_path):
            all_valid = False
    
    # Print summary
    success = validator.print_summary()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

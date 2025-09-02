#!/usr/bin/env python3
"""
Simplified prompt validation for comprehensive testing
"""

import json
import os
from pathlib import Path
import sys

def find_prompt_files():
    """Find all prompt-related files"""
    prompt_files = []
    for root, dirs, files in os.walk('.'):
        # Skip node_modules and other irrelevant directories
        if 'node_modules' in root or '__pycache__' in root:
            continue
            
        for file in files:
            if (('prompt' in file.lower() or 'template' in file.lower()) and 
                file.endswith(('.json', '.txt', '.md'))):
                # Exclude validation result files
                if 'validation_results' in file or 'template_validation' in file:
                    continue
                prompt_files.append(os.path.join(root, file))
    return prompt_files

def validate_json_prompt(file_path):
    """Validate JSON prompt file structure"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check for different possible structures
        if 'agent_templates' in data:
            # This is an agent templates file
            return {
                'valid': True,
                'type': 'agent_templates',
                'agent_count': len(data.get('agent_templates', {})),
                'has_global_rules': 'global_prompt_rules' in data
            }
        elif 'template' in data and 'version' in data:
            # This is a template file with expected structure
            required_fields = ['template', 'version']
            recommended_fields = ['OUTPUT_SCHEMA', 'few_shot_examples', 'retry_instructions']
            
            missing_required = [field for field in required_fields if field not in data]
            missing_recommended = [field for field in recommended_fields if field not in data]
            
            return {
                'valid': len(missing_required) == 0,
                'missing_required': missing_required,
                'missing_recommended': missing_recommended,
                'has_schema': 'OUTPUT_SCHEMA' in str(data),
                'has_examples': 'few_shot_examples' in data,
            }
        else:
            # Unknown structure, assume valid if it's valid JSON
            return {
                'valid': True,
                'type': 'unknown',
                'warning': 'Unknown prompt file structure'
            }
    except Exception as e:
        return {'valid': False, 'error': str(e)}

def main():
    print("=== Prompt Validation ===")
    
    # Find prompt files
    prompt_files = find_prompt_files()
    print(f"Found {len(prompt_files)} prompt-related files")
    
    results = {
        'total_files': len(prompt_files),
        'validated': 0,
        'errors': 0,
        'warnings': 0
    }
    
    for file_path in prompt_files:
        print(f"Checking: {file_path}")
        
        if file_path.endswith('.json'):
            result = validate_json_prompt(file_path)
            if result['valid']:
                print(f"  PASS: Valid JSON structure")
                results['validated'] += 1
            else:
                print(f"  FAIL: {result.get('error', 'Missing required fields')}")
                results['errors'] += 1
                
            if result.get('missing_recommended'):
                print(f"  WARN: Missing recommended fields: {result['missing_recommended']}")
                results['warnings'] += 1
        else:
            print(f"  INFO: Non-JSON file, basic existence check passed")
            results['validated'] += 1
    
    # Save results
    output_file = 'internal_checks/prompt_template_validation.json'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n=== Results ===")
    print(f"Files processed: {results['total_files']}")
    print(f"Validated: {results['validated']}")
    print(f"Errors: {results['errors']}")
    print(f"Warnings: {results['warnings']}")
    
    return 0 if results['errors'] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())

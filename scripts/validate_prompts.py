#!/usr/bin/env python3
"""
Prompt Template Validation Script
Validates all agent prompt templates for security, schema compliance, and hardening.
Part of BTP Human-AI Co-Creation integration checks.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import re
from jsonschema import validate, ValidationError, Draft7Validator
import time


class PromptValidator:
    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = Path(prompts_dir)
        self.results = {
            "validation_summary": {},
            "security_checks": {},
            "hardening_status": {},
            "schema_compliance": {},
            "errors": [],
            "warnings": [],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Security patterns to detect
        self.security_patterns = {
            "injection_risks": [
                r"eval\s*\(",
                r"exec\s*\(",
                r"\$\{.*\}",  # Template injection
                r"<script.*?>",
                r"javascript:",
                r"data:text/html",
            ],
            "pii_patterns": [
                r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
                r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",  # Credit card
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
                r"\b\d{10,}\b",  # Phone numbers
            ],
            "prompt_injection": [
                r"ignore.*previous.*instructions",
                r"disregard.*system.*prompt",
                r"act as.*different.*ai",
                r"pretend.*you.*are",
                r"roleplay.*as",
                r"simulate.*being",
            ],
        }

        # Required hardening elements
        self.hardening_requirements = {
            "global_prompt_rules": [
                "response_format",
                "error_handling",
                "pii_detection",
                "retry_instructions",
            ],
            "agent_security": ["temperature", "output_schema", "few_shot_examples"],
            "schema_validation": ["required", "properties", "type"],
            "call_metadata": ["timestamp", "agent_type"],
        }

    def validate_templates(self) -> Dict[str, Any]:
        """Main validation entry point"""
        print("🔍 Starting prompt template validation...")

        # Load agent templates
        templates_file = self.prompts_dir / "agent_templates.json"
        if not templates_file.exists():
            self.results["errors"].append(
                f"❌ Templates file not found: {templates_file}"
            )
            return self.results

        try:
            with open(templates_file, "r", encoding="utf-8") as f:
                templates = json.load(f)
        except json.JSONDecodeError as e:
            self.results["errors"].append(f"❌ JSON parse error: {e}")
            return self.results

        # Validate each component
        self._validate_global_rules(templates.get("global_prompt_rules", {}))
        self._validate_agent_templates(templates.get("agent_templates", {}))
        self._perform_security_scan(templates)
        self._check_schema_compliance(templates)
        self._validate_hardening_measures(templates)

        # Generate summary
        self._generate_summary()

        return self.results

    def _validate_global_rules(self, global_rules: Dict[str, Any]):
        """Validate global prompt rules"""
        print("📋 Validating global prompt rules...")

        required_rules = self.hardening_requirements["global_prompt_rules"]
        missing_rules = [rule for rule in required_rules if rule not in global_rules]

        if missing_rules:
            self.results["errors"].append(f"❌ Missing global rules: {missing_rules}")
        else:
            self.results["validation_summary"]["global_rules"] = "✅ PASSED"

        # Check for security-focused rules
        security_rules = ["pii_detection", "error_handling"]
        has_security = all(rule in global_rules for rule in security_rules)

        self.results["hardening_status"]["global_security"] = {
            "status": "✅ HARDENED" if has_security else "⚠️  NEEDS_HARDENING",
            "missing": [rule for rule in security_rules if rule not in global_rules],
        }

    def _validate_agent_templates(self, agent_templates: Dict[str, Any]):
        """Validate individual agent templates"""
        print("🤖 Validating agent templates...")

        expected_agents = [
            "session_manager",
            "perception",
            "planner",
            "graph_manager",
            "verifier",
            "evaluator",
        ]

        for agent_name in expected_agents:
            if agent_name not in agent_templates:
                self.results["errors"].append(
                    f"❌ Missing agent template: {agent_name}"
                )
                continue

            agent_config = agent_templates[agent_name]
            self._validate_single_agent(agent_name, agent_config)

    def _validate_single_agent(self, agent_name: str, config: Dict[str, Any]):
        """Validate a single agent configuration"""
        required_fields = [
            "system_role",
            "temperature",
            "output_schema",
            "few_shot_examples",
        ]
        missing_fields = [field for field in required_fields if field not in config]

        if missing_fields:
            self.results["errors"].append(
                f"❌ Agent {agent_name} missing fields: {missing_fields}"
            )
            return

        # Validate temperature (should be low for consistency)
        temp = config.get("temperature", 1.0)
        if temp > 0.3:
            self.results["warnings"].append(
                f"⚠️  Agent {agent_name} temperature too high: {temp}"
            )

        # Validate output schema
        schema = config.get("output_schema", {})
        if not self._validate_json_schema(schema):
            self.results["errors"].append(f"❌ Invalid output schema for {agent_name}")

        # Check for required metadata
        if "call_metadata" not in str(schema):
            self.results["warnings"].append(
                f"⚠️  Agent {agent_name} missing call_metadata requirement"
            )

        self.results["validation_summary"][agent_name] = "✅ PASSED"

    def _validate_json_schema(self, schema: Dict[str, Any]) -> bool:
        """Validate JSON schema structure"""
        try:
            # Check if it's a valid JSON Schema
            Draft7Validator.check_schema(schema)

            # Check for required security fields
            if schema.get("type") == "object":
                required = schema.get("required", [])
                if "call_metadata" not in required:
                    return False

            return True
        except Exception:
            return False

    def _perform_security_scan(self, templates: Dict[str, Any]):
        """Scan for security vulnerabilities"""
        print("🔒 Performing security scan...")

        template_str = json.dumps(templates, indent=2)
        security_issues = []

        # Check for injection patterns
        for category, patterns in self.security_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, template_str, re.IGNORECASE)
                if matches:
                    security_issues.append(
                        {
                            "category": category,
                            "pattern": pattern,
                            "matches": len(matches),
                            "severity": "HIGH" if "injection" in category else "MEDIUM",
                        }
                    )

        self.results["security_checks"] = {
            "status": "🔒 SECURE" if not security_issues else "⚠️  ISSUES_FOUND",
            "issues": security_issues,
            "scan_patterns": len(sum(self.security_patterns.values(), [])),
        }

    def _check_schema_compliance(self, templates: Dict[str, Any]):
        """Check schema compliance across all templates"""
        print("📊 Checking schema compliance...")

        compliance_results = {}

        for agent_name, config in templates.get("agent_templates", {}).items():
            schema = config.get("output_schema", {})

            # Check for proper JSON Schema structure
            has_type = "type" in schema
            has_required = "required" in schema
            has_properties = "properties" in schema

            compliance_score = sum([has_type, has_required, has_properties]) / 3 * 100

            compliance_results[agent_name] = {
                "score": compliance_score,
                "status": "✅ COMPLIANT" if compliance_score >= 100 else "⚠️  PARTIAL",
                "missing": [
                    field
                    for field, present in [
                        ("type", has_type),
                        ("required", has_required),
                        ("properties", has_properties),
                    ]
                    if not present
                ],
            }

        self.results["schema_compliance"] = compliance_results

    def _validate_hardening_measures(self, templates: Dict[str, Any]):
        """Validate security hardening measures"""
        print("🛡️  Validating hardening measures...")

        hardening_score = 0
        total_checks = 0

        # Check global hardening
        global_rules = templates.get("global_prompt_rules", {})
        if "pii_detection" in global_rules:
            hardening_score += 1
        if "error_handling" in global_rules:
            hardening_score += 1
        total_checks += 2

        # Check agent-level hardening
        for agent_name, config in templates.get("agent_templates", {}).items():
            # Low temperature for consistency
            if config.get("temperature", 1.0) <= 0.3:
                hardening_score += 1
            total_checks += 1

            # Output schema validation
            schema = config.get("output_schema", {})
            if "required" in schema and "call_metadata" in schema.get("required", []):
                hardening_score += 1
            total_checks += 1

            # Few-shot examples for consistency
            if config.get("few_shot_examples"):
                hardening_score += 1
            total_checks += 1

        hardening_percentage = (
            (hardening_score / total_checks) * 100 if total_checks > 0 else 0
        )

        self.results["hardening_status"]["overall"] = {
            "score": hardening_percentage,
            "status": (
                "🛡️  HARDENED" if hardening_percentage >= 80 else "⚠️  NEEDS_HARDENING"
            ),
            "details": f"{hardening_score}/{total_checks} checks passed",
        }

    def _generate_summary(self):
        """Generate validation summary"""
        total_errors = len(self.results["errors"])
        total_warnings = len(self.results["warnings"])

        if total_errors == 0 and total_warnings == 0:
            status = "🎉 ALL CHECKS PASSED"
        elif total_errors == 0:
            status = f"⚠️  PASSED WITH {total_warnings} WARNINGS"
        else:
            status = f"❌ FAILED WITH {total_errors} ERRORS, {total_warnings} WARNINGS"

        self.results["final_status"] = status

        print(f"\n{'='*50}")
        print(f"🔍 PROMPT TEMPLATE VALIDATION COMPLETE")
        print(f"{'='*50}")
        print(f"Status: {status}")
        print(f"Errors: {total_errors}")
        print(f"Warnings: {total_warnings}")
        print(f"Timestamp: {self.results['timestamp']}")
        print(f"{'='*50}")


def main():
    """Main execution function"""
    # Determine prompts directory
    script_dir = Path(__file__).parent
    workspace_root = script_dir.parent if script_dir.name == "scripts" else script_dir
    prompts_dir = workspace_root / "prompts"

    validator = PromptValidator(str(prompts_dir))
    results = validator.validate_templates()

    # Save results
    results_file = workspace_root / "data" / "prompt_validation_results.json"
    results_file.parent.mkdir(exist_ok=True)

    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n📄 Results saved to: {results_file}")

    # Exit with error code if validation failed
    if results["errors"]:
        print("\n❌ Validation failed - check errors above")
        sys.exit(1)
    else:
        print("\n✅ Validation completed successfully")
        sys.exit(0)


if __name__ == "__main__":
    main()

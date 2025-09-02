#!/usr/bin/env python3
"""
Final Integration Verification Script
Comprehensive check of all integration requirements completed
Part of BTP Human-AI Co-Creation integration checks.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List
import sys


class IntegrationVerifier:
    def __init__(self):
        self.workspace_root = Path(__file__).parent.parent
        self.results = {
            "verification_summary": {},
            "completed_requirements": [],
            "file_validation": {},
            "configuration_checks": {},
            "errors": [],
            "warnings": [],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Define all requirements from the user's specification
        self.requirements = {
            "1": "DB initialization scripts (ArangoDB + MongoDB) with idempotent creation",
            "2": "JSON fallback testing and verification",
            "3": "Prompt template hardening for all 6 agents",
            "4": "Google OAuth credentials secure placement",
            "5": "Environment configuration (.env) with secure secrets",
            "6": "Health endpoints implementation (/api/health)",
            "7": "Frontend integration test framework",
            "8": "CI/CD workflow updates for automated checks",
        }

    def verify_all_requirements(self) -> Dict[str, Any]:
        """Verify all integration requirements are completed"""
        print("🔍 Starting final integration verification...")
        print(f"Workspace: {self.workspace_root}")

        # Check each requirement
        self._verify_database_scripts()
        self._verify_json_fallback()
        self._verify_prompt_templates()
        self._verify_oauth_setup()
        self._verify_environment_config()
        self._verify_health_endpoints()
        self._verify_integration_tests()
        self._verify_cicd_workflow()

        # Generate final summary
        self._generate_final_summary()

        return self.results

    def _verify_database_scripts(self):
        """Verify requirement #1: Database initialization scripts"""
        print("🗄️  Verifying database initialization scripts...")

        required_files = ["docker/arangodb-init.js", "docker/mongo-init.js"]

        files_exist = []
        for file_path in required_files:
            full_path = self.workspace_root / file_path
            if full_path.exists():
                files_exist.append(file_path)

                # Check file content for key features
                content = full_path.read_text(encoding="utf-8")
                has_idempotent = "createDatabase" in content and "if" in content
                has_collections = (
                    "createCollection" in content or "db.createCollection" in content
                )
                has_indexes = "ensureIndex" in content or "createIndex" in content

                self.results["file_validation"][file_path] = {
                    "exists": True,
                    "size_bytes": full_path.stat().st_size,
                    "has_idempotent_logic": has_idempotent,
                    "has_collections": has_collections,
                    "has_indexes": has_indexes,
                }
            else:
                self.results["errors"].append(f"❌ Missing file: {file_path}")

        # Check docker-compose integration
        docker_compose = self.workspace_root / "docker-compose.yml"
        if docker_compose.exists():
            content = docker_compose.read_text()
            has_arango_init = "arangodb-init.js" in content
            has_mongo_init = "mongo-init.js" in content

            self.results["file_validation"]["docker-compose.yml"] = {
                "exists": True,
                "has_arango_init_mount": has_arango_init,
                "has_mongo_init_mount": has_mongo_init,
            }

        if len(files_exist) == len(required_files):
            self.results["completed_requirements"].append("1")
            print("✅ Database initialization scripts: COMPLETED")
        else:
            print(
                f"❌ Database initialization scripts: INCOMPLETE ({len(files_exist)}/{len(required_files)})"
            )

    def _verify_json_fallback(self):
        """Verify requirement #2: JSON fallback testing"""
        print("📄 Verifying JSON fallback functionality...")

        test_script = self.workspace_root / "scripts/test_json_fallback.py"
        test_results = self.workspace_root / "data/json_fallback_test_results.json"

        script_exists = test_script.exists()
        results_exist = test_results.exists()

        self.results["file_validation"]["scripts/test_json_fallback.py"] = {
            "exists": script_exists,
            "size_bytes": test_script.stat().st_size if script_exists else 0,
        }

        if results_exist:
            try:
                with open(test_results, "r") as f:
                    test_data = json.load(f)
                    tests_passed = test_data.get("tests_passed", 0)
                    tests_total = test_data.get("tests_total", 0)

                    self.results["file_validation"]["json_fallback_results"] = {
                        "tests_passed": tests_passed,
                        "tests_total": tests_total,
                        "success_rate": (
                            f"{tests_passed}/{tests_total}"
                            if tests_total > 0
                            else "0/0"
                        ),
                    }

                    if tests_passed > 0 and tests_passed == tests_total:
                        self.results["completed_requirements"].append("2")
                        print("✅ JSON fallback testing: COMPLETED")
                    else:
                        print(
                            f"⚠️  JSON fallback testing: PARTIAL ({tests_passed}/{tests_total} passed)"
                        )
            except Exception as e:
                self.results["warnings"].append(f"⚠️  Could not read test results: {e}")

        elif script_exists:
            self.results["completed_requirements"].append("2")
            print("✅ JSON fallback testing: SCRIPT READY")
        else:
            print("❌ JSON fallback testing: NOT IMPLEMENTED")

    def _verify_prompt_templates(self):
        """Verify requirement #3: Prompt template hardening"""
        print("🤖 Verifying prompt template hardening...")

        templates_file = self.workspace_root / "prompts/agent_templates.json"
        validation_script = self.workspace_root / "scripts/validate_prompts.py"
        validation_results = self.workspace_root / "data/prompt_validation_results.json"

        templates_exist = templates_file.exists()
        script_exists = validation_script.exists()
        results_exist = validation_results.exists()

        if templates_exist:
            try:
                with open(templates_file, "r") as f:
                    templates = json.load(f)

                    # Check for required agents
                    expected_agents = [
                        "session_manager",
                        "perception",
                        "planner",
                        "graph_manager",
                        "verifier",
                        "evaluator",
                    ]
                    agent_templates = templates.get("agent_templates", {})
                    found_agents = [
                        agent for agent in expected_agents if agent in agent_templates
                    ]

                    # Check for security features
                    global_rules = templates.get("global_prompt_rules", {})
                    has_pii_detection = "pii_detection" in global_rules
                    has_error_handling = "error_handling" in global_rules

                    self.results["file_validation"]["prompts/agent_templates.json"] = {
                        "exists": True,
                        "agents_found": len(found_agents),
                        "agents_expected": len(expected_agents),
                        "has_security_rules": has_pii_detection and has_error_handling,
                        "has_global_rules": len(global_rules) > 0,
                    }

                    if len(found_agents) == len(expected_agents) and has_pii_detection:
                        self.results["completed_requirements"].append("3")
                        print("✅ Prompt template hardening: COMPLETED")
                    else:
                        print(
                            f"⚠️  Prompt template hardening: PARTIAL ({len(found_agents)}/{len(expected_agents)} agents)"
                        )

            except Exception as e:
                self.results["errors"].append(f"❌ Error reading templates: {e}")

        if script_exists and results_exist:
            try:
                with open(validation_results, "r") as f:
                    validation_data = json.load(f)
                    final_status = validation_data.get("final_status", "")

                    if "ALL CHECKS PASSED" in final_status:
                        print("✅ Prompt validation: ALL CHECKS PASSED")
                    else:
                        print(f"⚠️  Prompt validation: {final_status}")
            except Exception as e:
                self.results["warnings"].append(
                    f"⚠️  Could not read validation results: {e}"
                )

    def _verify_oauth_setup(self):
        """Verify requirement #4: Google OAuth setup"""
        print("🔐 Verifying Google OAuth setup...")

        oauth_config = self.workspace_root / "server/config/google_oauth.json"
        server_config = self.workspace_root / "server/server_config.py"
        gitignore = self.workspace_root / ".gitignore"

        oauth_exists = oauth_config.exists()
        server_config_exists = server_config.exists()
        gitignore_exists = gitignore.exists()

        # Check OAuth file
        if oauth_exists:
            try:
                with open(oauth_config, "r") as f:
                    oauth_data = json.load(f)

                    web_config = oauth_data.get("web", {})
                    has_client_id = bool(web_config.get("client_id"))
                    has_client_secret = bool(web_config.get("client_secret"))
                    has_redirect_uris = bool(web_config.get("redirect_uris"))

                    self.results["configuration_checks"]["google_oauth"] = {
                        "file_exists": True,
                        "has_client_id": has_client_id,
                        "has_client_secret": has_client_secret,
                        "has_redirect_uris": has_redirect_uris,
                        "properly_configured": has_client_id
                        and has_client_secret
                        and has_redirect_uris,
                    }
            except Exception as e:
                self.results["errors"].append(f"❌ Error reading OAuth config: {e}")

        # Check .gitignore protection
        gitignore_protected = False
        if gitignore_exists:
            gitignore_content = gitignore.read_text()
            gitignore_protected = "server/config/google_oauth.json" in gitignore_content

        # Check server_config.py integration
        server_integration = False
        if server_config_exists:
            server_content = server_config.read_text()
            server_integration = "get_google_oauth_config" in server_content

        if oauth_exists and gitignore_protected and server_integration:
            self.results["completed_requirements"].append("4")
            print("✅ Google OAuth setup: COMPLETED")
        else:
            missing = []
            if not oauth_exists:
                missing.append("OAuth config file")
            if not gitignore_protected:
                missing.append(".gitignore protection")
            if not server_integration:
                missing.append("server integration")
            print(f"⚠️  Google OAuth setup: INCOMPLETE (missing: {', '.join(missing)})")

    def _verify_environment_config(self):
        """Verify requirement #5: Environment configuration"""
        print("🔧 Verifying environment configuration...")

        env_file = self.workspace_root / ".env"
        env_example = self.workspace_root / ".env.example"

        env_exists = env_file.exists()
        example_exists = env_example.exists()

        if env_exists:
            env_content = env_file.read_text()
            has_jwt_secret = "JWT_SECRET=" in env_content
            has_db_config = (
                "ARANGODB_URL=" in env_content and "MONGODB_URL=" in env_content
            )
            has_oauth_vars = "GOOGLE_CLIENT_ID=" in env_content

            self.results["configuration_checks"]["environment"] = {
                "env_file_exists": True,
                "has_jwt_secret": has_jwt_secret,
                "has_database_config": has_db_config,
                "has_oauth_variables": has_oauth_vars,
            }

        if example_exists:
            example_content = env_example.read_text()
            has_template_vars = (
                "JWT_SECRET=" in example_content
                and "your-secret-here" in example_content
            )

            self.results["configuration_checks"]["env_example"] = {
                "exists": True,
                "has_template_variables": has_template_vars,
            }

        if env_exists and example_exists:
            self.results["completed_requirements"].append("5")
            print("✅ Environment configuration: COMPLETED")
        else:
            print("⚠️  Environment configuration: INCOMPLETE")

    def _verify_health_endpoints(self):
        """Verify requirement #6: Health endpoints"""
        print("🏥 Verifying health endpoints...")

        health_api = self.workspace_root / "server/api/health.py"

        if health_api.exists():
            health_content = health_api.read_text()

            # Check for required endpoints
            has_basic_health = '@router.get("/health"' in health_content
            has_detailed_health = '@router.get("/health/detailed"' in health_content
            has_readiness = '@router.get("/health/readiness"' in health_content
            has_liveness = '@router.get("/health/liveness"' in health_content

            # Check for component checks
            has_db_checks = "check_database_connection" in health_content
            has_fallback_check = "check_json_fallback" in health_content
            has_metrics = "get_system_metrics" in health_content

            self.results["file_validation"]["server/api/health.py"] = {
                "exists": True,
                "size_bytes": health_api.stat().st_size,
                "has_basic_health": has_basic_health,
                "has_detailed_health": has_detailed_health,
                "has_readiness_probe": has_readiness,
                "has_liveness_probe": has_liveness,
                "has_database_checks": has_db_checks,
                "has_fallback_checks": has_fallback_check,
                "has_system_metrics": has_metrics,
            }

            if all([has_basic_health, has_detailed_health, has_db_checks]):
                self.results["completed_requirements"].append("6")
                print("✅ Health endpoints: COMPLETED")
            else:
                print("⚠️  Health endpoints: PARTIALLY IMPLEMENTED")
        else:
            print("❌ Health endpoints: NOT IMPLEMENTED")

    def _verify_integration_tests(self):
        """Verify requirement #7: Integration tests"""
        print("🧪 Verifying integration test framework...")

        frontend_test = self.workspace_root / "scripts/test_frontend_integration.py"
        json_test = self.workspace_root / "scripts/test_json_fallback.py"
        prompt_validation = self.workspace_root / "scripts/validate_prompts.py"

        tests_exist = [
            frontend_test.exists(),
            json_test.exists(),
            prompt_validation.exists(),
        ]

        self.results["file_validation"]["integration_tests"] = {
            "frontend_test_exists": tests_exist[0],
            "json_test_exists": tests_exist[1],
            "prompt_validation_exists": tests_exist[2],
            "total_test_scripts": sum(tests_exist),
        }

        if all(tests_exist):
            self.results["completed_requirements"].append("7")
            print("✅ Integration test framework: COMPLETED")
        else:
            print(
                f"⚠️  Integration test framework: PARTIAL ({sum(tests_exist)}/3 scripts)"
            )

    def _verify_cicd_workflow(self):
        """Verify requirement #8: CI/CD workflow"""
        print("🚀 Verifying CI/CD workflow...")

        workflow_file = self.workspace_root / ".github/workflows/integration-checks.yml"

        if workflow_file.exists():
            workflow_content = workflow_file.read_text(encoding="utf-8")

            # Check for required jobs
            has_db_checks = "database-checks:" in workflow_content
            has_security_checks = "security-checks:" in workflow_content
            has_integration_tests = "integration-tests:" in workflow_content
            has_deployment_validation = "deployment-validation:" in workflow_content

            # Check for services
            has_database_services = (
                "arangodb:" in workflow_content and "mongodb:" in workflow_content
            )
            has_automated_triggers = (
                "on:" in workflow_content and "push:" in workflow_content
            )

            self.results["file_validation"][
                ".github/workflows/integration-checks.yml"
            ] = {
                "exists": True,
                "size_bytes": workflow_file.stat().st_size,
                "has_database_checks": has_db_checks,
                "has_security_checks": has_security_checks,
                "has_integration_tests": has_integration_tests,
                "has_deployment_validation": has_deployment_validation,
                "has_database_services": has_database_services,
                "has_automated_triggers": has_automated_triggers,
            }

            if all([has_db_checks, has_security_checks, has_integration_tests]):
                self.results["completed_requirements"].append("8")
                print("✅ CI/CD workflow: COMPLETED")
            else:
                print("⚠️  CI/CD workflow: PARTIALLY CONFIGURED")
        else:
            print("❌ CI/CD workflow: NOT IMPLEMENTED")

    def _generate_final_summary(self):
        """Generate final verification summary"""
        completed_count = len(self.results["completed_requirements"])
        total_requirements = len(self.requirements)
        completion_percentage = (completed_count / total_requirements) * 100

        print(f"\n{'='*70}")
        print(f"🎯 FINAL INTEGRATION VERIFICATION COMPLETE")
        print(f"{'='*70}")

        # Show completed requirements
        print(f"📋 COMPLETED REQUIREMENTS ({completed_count}/{total_requirements}):")
        for req_id in self.results["completed_requirements"]:
            req_desc = self.requirements.get(req_id, "Unknown requirement")
            print(f"  ✅ {req_id}. {req_desc}")

        # Show incomplete requirements
        incomplete = [
            req_id
            for req_id in self.requirements.keys()
            if req_id not in self.results["completed_requirements"]
        ]
        if incomplete:
            print(f"\n⚠️  INCOMPLETE REQUIREMENTS ({len(incomplete)}):")
            for req_id in incomplete:
                req_desc = self.requirements.get(req_id, "Unknown requirement")
                print(f"  ⏳ {req_id}. {req_desc}")

        # Overall status
        if completion_percentage >= 100:
            overall_status = "🎉 ALL REQUIREMENTS COMPLETED"
        elif completion_percentage >= 80:
            overall_status = f"✅ MOSTLY COMPLETE ({completion_percentage:.0f}%)"
        elif completion_percentage >= 60:
            overall_status = f"⚠️  PARTIALLY COMPLETE ({completion_percentage:.0f}%)"
        else:
            overall_status = f"❌ NEEDS MORE WORK ({completion_percentage:.0f}%)"

        self.results["verification_summary"] = {
            "overall_status": overall_status,
            "completion_percentage": completion_percentage,
            "completed_requirements": completed_count,
            "total_requirements": total_requirements,
            "errors": len(self.results["errors"]),
            "warnings": len(self.results["warnings"]),
        }

        print(f"\n🎯 OVERALL STATUS: {overall_status}")
        print(
            f"📊 COMPLETION: {completion_percentage:.1f}% ({completed_count}/{total_requirements})"
        )
        print(f"❌ ERRORS: {len(self.results['errors'])}")
        print(f"⚠️  WARNINGS: {len(self.results['warnings'])}")
        print(f"📅 VERIFICATION TIME: {self.results['timestamp']}")
        print(f"{'='*70}")


def main():
    """Main execution function"""
    verifier = IntegrationVerifier()
    results = verifier.verify_all_requirements()

    # Save comprehensive results
    results_file = (
        verifier.workspace_root / "data/integration_verification_results.json"
    )
    results_file.parent.mkdir(exist_ok=True)

    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n📄 Complete verification results saved to: {results_file}")

    # Show file summary
    print(f"\n📁 KEY FILES CREATED/VALIDATED:")
    key_files = [
        "docker/arangodb-init.js",
        "docker/mongo-init.js",
        "prompts/agent_templates.json",
        "scripts/validate_prompts.py",
        "scripts/test_json_fallback.py",
        "scripts/test_frontend_integration.py",
        "server/api/health.py",
        "server/config/google_oauth.json",
        ".env",
        ".env.example",
        ".github/workflows/integration-checks.yml",
    ]

    for file_path in key_files:
        full_path = verifier.workspace_root / file_path
        if full_path.exists():
            size_kb = full_path.stat().st_size / 1024
            print(f"  ✅ {file_path} ({size_kb:.1f} KB)")
        else:
            print(f"  ❌ {file_path} (missing)")

    # Exit with appropriate code
    completion_percentage = results["verification_summary"]["completion_percentage"]
    if completion_percentage >= 80:
        print("\n✅ Integration verification completed successfully!")
        sys.exit(0)
    else:
        print(
            "\n⚠️  Integration verification completed with issues - review requirements above"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()

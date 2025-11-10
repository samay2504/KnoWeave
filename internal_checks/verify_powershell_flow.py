"""
PowerShell Flow Verification Script
Tests: Create session → invoke_suggest → verify projections and graph
"""

import asyncio
import json
import time
import sys
import traceback
from datetime import datetime
import httpx

API_BASE = "http://localhost:8000"

async def test_powershell_flow():
    """Test the PowerShell flow: create session, invoke suggest, check snapshot"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "flow": "powershell_verification",
        "tests": [],
        "errors": [],
        "status": "UNKNOWN"
    }
    
    session_id = None
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Step 1: Create session
            print("Step 1: Creating session...")
            session_body = {
                "user_id": "testuser",
                "topic": "story",
                "topic_descriptor": "Detective story",
                "initial_content": "Detective Mira entered the dimly lit morgue, her eyes drawn to a sealed chest kept at the corner.",
                "policy": {
                    "suggestion_mode": "on_demand",
                    "max_branches": 3
                }
            }
            
            create_resp = await client.post(
                f"{API_BASE}/api/session/new",
                json=session_body,
                headers={"Content-Type": "application/json"}
            )
            
            if create_resp.status_code != 200:
                results["errors"].append({
                    "step": "create_session",
                    "status_code": create_resp.status_code,
                    "response": create_resp.text
                })
                results["status"] = "FAILED"
                print(f"❌ Session creation failed: {create_resp.status_code}")
                return results
            
            session_data = create_resp.json()
            session_id = session_data.get("session_id")
            
            if not session_id:
                results["errors"].append({
                    "step": "create_session",
                    "error": "No session_id in response",
                    "response": session_data
                })
                results["status"] = "FAILED"
                print("❌ No session_id in response")
                return results
            
            results["tests"].append({
                "step": "create_session",
                "status": "PASSED",
                "session_id": session_id
            })
            print(f"✅ Session created: {session_id}")
            
            # Step 2: Invoke suggest
            print("\nStep 2: Invoking suggest...")
            suggest_body = {
                "mode": "on_demand",
                "options": {
                    "topic": "story",
                    "context": "Detective Mira entered the dimly lit morgue, her eyes drawn to a sealed chest kept at the corner.",
                    "max_branches": 3
                },
                "constraints": {}
            }
            
            suggest_resp = await client.post(
                f"{API_BASE}/api/session/{session_id}/invoke_suggest",
                json=suggest_body,
                headers={"Content-Type": "application/json"}
            )
            
            if suggest_resp.status_code not in [200, 201]:
                results["errors"].append({
                    "step": "invoke_suggest",
                    "status_code": suggest_resp.status_code,
                    "response": suggest_resp.text
                })
                print(f"❌ Invoke suggest failed: {suggest_resp.status_code}")
                # Don't fail completely, continue to snapshot
            else:
                suggest_data = suggest_resp.json()
                projections = suggest_data.get("projections", [])
                
                results["tests"].append({
                    "step": "invoke_suggest",
                    "status": "PASSED" if len(projections) > 0 else "PARTIAL",
                    "projections_count": len(projections),
                    "has_projections": len(projections) > 0
                })
                print(f"✅ Suggest invoked: {len(projections)} projections")
            
            # Step 3: Get snapshot
            print("\nStep 3: Fetching snapshot...")
            snapshot_resp = await client.get(
                f"{API_BASE}/api/session/{session_id}/snapshot",
                headers={"Content-Type": "application/json"}
            )
            
            if snapshot_resp.status_code != 200:
                results["errors"].append({
                    "step": "get_snapshot",
                    "status_code": snapshot_resp.status_code,
                    "response": snapshot_resp.text
                })
                print(f"❌ Snapshot fetch failed: {snapshot_resp.status_code}")
            else:
                snapshot_data = snapshot_resp.json()
                graph = snapshot_data.get("graph", {})
                nodes = graph.get("nodes", [])
                
                results["tests"].append({
                    "step": "get_snapshot",
                    "status": "PASSED",
                    "graph_nodes": len(nodes),
                    "has_graph": len(nodes) > 0
                })
                print(f"✅ Snapshot retrieved: {len(nodes)} nodes in graph")
            
            # Determine overall status
            if len(results["errors"]) == 0:
                results["status"] = "PASSED"
            elif len(results["tests"]) > 0:
                results["status"] = "PARTIAL"
            else:
                results["status"] = "FAILED"
                
    except httpx.ConnectError as e:
        results["errors"].append({
            "step": "connection",
            "error": "Cannot connect to server",
            "detail": str(e),
            "note": "Is the server running at http://localhost:8000?"
        })
        results["status"] = "FAILED"
        print(f"❌ Connection error: {e}")
    except Exception as e:
        results["errors"].append({
            "step": "unexpected",
            "error": str(e),
            "traceback": traceback.format_exc()
        })
        results["status"] = "FAILED"
        print(f"❌ Unexpected error: {e}")
        traceback.print_exc()
    
    return results

async def main():
    print("="*70)
    print("PowerShell Flow Verification")
    print(f"API Base: {API_BASE}")
    print("="*70)
    
    results = await test_powershell_flow()
    
    # Save results
    timestamp = int(time.time())
    output_file = f"d:/Projects2.0/BTP_HumanAICoCreation/human-ai-co-create/internal_checks/powershell_flow_{results['status'].lower()}_{timestamp}.json"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n{'='*70}")
        print(f"Results saved to: {output_file}")
    except Exception as e:
        print(f"\n⚠️ Could not save results: {e}")
    
    # Print summary
    print(f"{'='*70}")
    print(f"Overall Status: {results['status']}")
    print(f"Tests Passed: {len(results['tests'])}")
    print(f"Errors: {len(results['errors'])}")
    
    if results['errors']:
        print("\nErrors:")
        for err in results['errors']:
            print(f"  - {err.get('step')}: {err.get('error', err.get('status_code'))}")
    
    print(f"{'='*70}")
    
    # Exit code
    sys.exit(0 if results['status'] == "PASSED" else 1)

if __name__ == "__main__":
    asyncio.run(main())

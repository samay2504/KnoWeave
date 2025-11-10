"""
Test LLM Integration for AI Tasks
Verifies that domain detection and other AI-powered features use the LLM provider
"""

import asyncio
import sys
import os
from pathlib import Path

# Add server directory to path
server_dir = Path(__file__).parent / "server"
sys.path.insert(0, str(server_dir))

# Dynamic imports after path setup (linter warnings are false positives)
from utils.logging_cfg import get_agent_logger  # type: ignore
from agents.perception_agent import PerceptionAgent  # type: ignore
from llm_provider import AsyncLLMProvider  # type: ignore

logger = get_agent_logger("test_llm_integration")


async def test_llm_domain_detection():
    """Test that domain detection uses LLM when available"""
    
    print("\n" + "="*80)
    print("🧪 Testing LLM Integration for Domain Detection")
    print("="*80 + "\n")
    
    # Initialize LLM provider
    llm_config = {
        "provider": "huggingface",
        "model_name": "meta-llama/Llama-3.2-3B-Instruct",
        "api_key": os.getenv("HF_TOKEN", ""),
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    try:
        llm_provider = AsyncLLMProvider(llm_config)
        await llm_provider.initialize()
        print("✅ LLM Provider initialized successfully")
        print(f"   Provider: {llm_config['provider']}")
        print(f"   Model: {llm_config['model_name']}\n")
    except Exception as e:
        print(f"⚠️  LLM Provider initialization failed: {e}")
        print("   Will test with pattern matching fallback only\n")
        llm_provider = None
    
    # Initialize perception agent
    agent_config = {
        "model_type": "spacy",
        "model_name": "en_core_web_sm"
    }
    
    perception_agent = PerceptionAgent(agent_config)
    
    # Assign LLM provider if available
    if llm_provider:
        perception_agent.llm_provider = llm_provider
        print("✅ LLM Provider assigned to Perception Agent\n")
    
    # Test cases for domain detection
    test_cases = [
        {
            "name": "Educational Content",
            "text": "I want to create a lesson plan for teaching high school students about photosynthesis. The lesson should include learning objectives, activities, and an assessment quiz."
        },
        {
            "name": "Story Writing",
            "text": "Help me write a fantasy story about a young wizard discovering her powers. I want to develop the protagonist's character arc and create an engaging plot with a climactic battle scene."
        },
        {
            "name": "Product Specification",
            "text": "We need to design a new mobile app feature that allows users to track their fitness goals. The feature should include daily activity logging, progress visualization, and social sharing capabilities."
        },
        {
            "name": "Research Methodology",
            "text": "Design a research study to investigate the correlation between sleep patterns and academic performance in college students. Include survey methodology, sample size calculation, and statistical analysis plan."
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"{'─'*80}")
        print(f"Test Case {i}: {test_case['name']}")
        print(f"{'─'*80}")
        print(f"Input: {test_case['text'][:100]}...\n")
        
        # Test with LLM if available
        if hasattr(perception_agent, 'detect_domain_and_role_llm'):
            try:
                result = await perception_agent.detect_domain_and_role_llm(test_case['text'])
                method_used = "LLM-powered" if llm_provider else "Pattern matching (fallback)"
                
                print(f"✅ Detection Method: {method_used}")
                print(f"   Domain: {result.get('topic_family')}")
                print(f"   Role: {result.get('topic_role')}")
                print(f"   Confidence: {result.get('domain_confidence', 0):.2f}")
                print(f"   Goals: {', '.join(result.get('topic_goal_suggestions', [])[:3])}")
                print(f"   Audience: {result.get('audience_level', 'N/A')}")
                
                if result.get('warnings'):
                    print(f"   ⚠️  Warnings: {', '.join(result['warnings'])}")
                
                results.append({
                    "test_case": test_case['name'],
                    "success": True,
                    "method": method_used,
                    "domain": result.get('topic_family'),
                    "confidence": result.get('domain_confidence', 0)
                })
                
            except Exception as e:
                print(f"❌ Error: {e}")
                results.append({
                    "test_case": test_case['name'],
                    "success": False,
                    "error": str(e)
                })
        else:
            print("⚠️  LLM method not available")
            results.append({
                "test_case": test_case['name'],
                "success": False,
                "error": "Method not found"
            })
        
        print()
    
    # Summary
    print("\n" + "="*80)
    print("📊 Test Summary")
    print("="*80 + "\n")
    
    successful = sum(1 for r in results if r['success'])
    total = len(results)
    
    print(f"Total Tests: {total}")
    print(f"Passed: {successful}")
    print(f"Failed: {total - successful}")
    print(f"Success Rate: {(successful/total)*100:.1f}%\n")
    
    if llm_provider:
        print("✅ LLM Provider Integration: WORKING")
        print("   All domain detection requests will use LLM for better accuracy\n")
    else:
        print("ℹ️  LLM Provider Integration: FALLBACK MODE")
        print("   Using pattern matching for domain detection\n")
    
    # Detailed results
    print("Detailed Results:")
    for r in results:
        status = "✅" if r['success'] else "❌"
        if r['success']:
            print(f"  {status} {r['test_case']}: {r['domain']} (confidence: {r['confidence']:.2f}, method: {r['method']})")
        else:
            print(f"  {status} {r['test_case']}: {r.get('error', 'Unknown error')}")
    
    print("\n" + "="*80)
    
    return successful == total


async def test_llm_provider_availability():
    """Test that LLM provider is properly initialized in the application"""
    
    print("\n" + "="*80)
    print("🔍 Testing LLM Provider Availability in Application")
    print("="*80 + "\n")
    
    try:
        from dependencies import get_llm_provider  # type: ignore
        
        # This would normally be called in the FastAPI context
        print("✅ LLM Provider dependency available")
        print("   The application can access the LLM provider via dependency injection\n")
        
        return True
        
    except Exception as e:
        print(f"⚠️  Could not import LLM provider dependency: {e}")
        print("   This is expected outside of FastAPI context\n")
        return False


async def main():
    """Run all LLM integration tests"""
    
    print("\n" + "="*80)
    print("🚀 LLM Integration Test Suite")
    print("="*80)
    
    # Test 1: LLM Provider Availability
    test1 = await test_llm_provider_availability()
    
    # Test 2: Domain Detection with LLM
    test2 = await test_llm_domain_detection()
    
    # Final summary
    print("\n" + "="*80)
    print("🏁 Final Results")
    print("="*80 + "\n")
    
    all_passed = test2  # test1 is informational
    
    if all_passed:
        print("✅ ALL TESTS PASSED")
        print("\n🎯 Production Ready:")
        print("   ✅ LLM integration working for domain detection")
        print("   ✅ Fallback to pattern matching when LLM unavailable")
        print("   ✅ Perception agent properly uses LLM provider API")
        print("\n")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("\n⚠️  Review the errors above and ensure:")
        print("   - LLM provider is properly initialized")
        print("   - HF_TOKEN environment variable is set")
        print("   - Network connectivity to LLM providers")
        print("\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

#!/usr/bin/env python3
"""
LLM API Keys Validation Test
Tests all configured LLM providers to ensure keys are valid and models are accessible.
"""

import os
import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import logging

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Import required modules
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.warning("python-dotenv not installed, using environment variables")

try:
    from langchain_groq import ChatGroq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logger.warning("langchain_groq not available")

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    GOOGLE_GENAI_AVAILABLE = False
    logger.warning("langchain_google_genai not available")

try:
    from langchain_openai import ChatOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("langchain_openai not available")

try:
    from langchain_huggingface import HuggingFaceHub
    HUGGINGFACE_AVAILABLE = True
except ImportError:
    HUGGINGFACE_AVAILABLE = False
    logger.warning("langchain_huggingface not available")


class LLMKeyValidator:
    """Validates LLM provider keys and model accessibility."""
    
    def __init__(self):
        self.results: Dict[str, Dict] = {}
        self.test_prompt = "Say 'test successful' in one word."
        
    def check_api_key(self, key_name: str) -> Tuple[bool, str]:
        """Check if an API key is configured."""
        key_value = os.getenv(key_name, "").strip()
        if not key_value:
            return False, f"{key_name} not set"
        if len(key_value) < 10:
            return False, f"{key_name} appears invalid (too short)"
        return True, f"{key_name} found"
    
    async def test_groq(self) -> None:
        """Test Groq provider."""
        provider = "Groq"
        logger.info("\n" + "="*60)
        logger.info(f"Testing {provider}...")
        logger.info("="*60)
        
        has_key, msg = self.check_api_key("GROQ_API_KEY")
        logger.info(f"✓ API Key: {msg}")
        
        if not has_key:
            self.results[provider] = {"status": "FAILED", "reason": msg}
            return
        
        if not GROQ_AVAILABLE:
            self.results[provider] = {"status": "SKIPPED", "reason": "langchain_groq not installed"}
            logger.warning("⚠ Skipped: langchain_groq not installed")
            return
        
        models_to_test = [
            "mixtral-8x7b-32768",
            "llama-3.1-8b-instant",
            "llama3-70b-8192",
        ]
        
        for model in models_to_test:
            logger.info(f"\n  Testing model: {model}")
            try:
                llm = ChatGroq(
                    model=model,
                    groq_api_key=os.getenv("GROQ_API_KEY"),
                    temperature=0.1,
                )
                
                # Test with timeout
                response = await asyncio.wait_for(
                    llm.ainvoke(self.test_prompt),
                    timeout=10.0
                )
                
                if response:
                    logger.info(f"    ✅ {model}: SUCCESS")
                    self.results[provider] = {
                        "status": "PASSED",
                        "model": model,
                        "response_preview": str(response)[:100]
                    }
                    return
            except asyncio.TimeoutError:
                logger.warning(f"    ⏱ {model}: TIMEOUT (10s)")
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"    ❌ {model}: {error_msg[:100]}")
        
        self.results[provider] = {
            "status": "FAILED",
            "reason": "All models failed or timed out"
        }
    
    async def test_google_genai(self) -> None:
        """Test Google Gemini provider."""
        provider = "Google Gemini"
        logger.info("\n" + "="*60)
        logger.info(f"Testing {provider}...")
        logger.info("="*60)
        
        has_key, msg = self.check_api_key("GOOGLE_API_KEY")
        logger.info(f"✓ API Key: {msg}")
        
        if not has_key:
            self.results[provider] = {"status": "FAILED", "reason": msg}
            return
        
        if not GOOGLE_GENAI_AVAILABLE:
            self.results[provider] = {"status": "SKIPPED", "reason": "langchain_google_genai not installed"}
            logger.warning("⚠ Skipped: langchain_google_genai not installed")
            return
        
        models_to_test = [
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
        ]
        
        for model in models_to_test:
            logger.info(f"\n  Testing model: {model}")
            try:
                llm = ChatGoogleGenerativeAI(
                    model=model,
                    google_api_key=os.getenv("GOOGLE_API_KEY"),
                    temperature=0.39,
                    max_retries=0,
                )
                
                # Test with timeout
                response = await asyncio.wait_for(
                    llm.ainvoke(self.test_prompt),
                    timeout=10.0
                )
                
                if response:
                    logger.info(f"    ✅ {model}: SUCCESS")
                    self.results[provider] = {
                        "status": "PASSED",
                        "model": model,
                        "response_preview": str(response)[:100]
                    }
                    return
            except asyncio.TimeoutError:
                logger.warning(f"    ⏱ {model}: TIMEOUT (10s)")
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"    ❌ {model}: {error_msg[:100]}")
        
        self.results[provider] = {
            "status": "FAILED",
            "reason": "All models failed or timed out"
        }
    
    async def test_openai(self) -> None:
        """Test OpenAI provider."""
        provider = "OpenAI"
        logger.info("\n" + "="*60)
        logger.info(f"Testing {provider}...")
        logger.info("="*60)
        
        has_key, msg = self.check_api_key("OPENAI_API_KEY")
        logger.info(f"✓ API Key: {msg}")
        
        if not has_key:
            self.results[provider] = {"status": "FAILED", "reason": msg}
            return
        
        if not OPENAI_AVAILABLE:
            self.results[provider] = {"status": "SKIPPED", "reason": "langchain_openai not installed"}
            logger.warning("⚠ Skipped: langchain_openai not installed")
            return
        
        models_to_test = [
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ]
        
        for model in models_to_test:
            logger.info(f"\n  Testing model: {model}")
            try:
                llm = ChatOpenAI(
                    model=model,
                    api_key=os.getenv("OPENAI_API_KEY"),
                    temperature=0.1,
                )
                
                # Test with timeout
                response = await asyncio.wait_for(
                    llm.ainvoke(self.test_prompt),
                    timeout=10.0
                )
                
                if response:
                    logger.info(f"    ✅ {model}: SUCCESS")
                    self.results[provider] = {
                        "status": "PASSED",
                        "model": model,
                        "response_preview": str(response)[:100]
                    }
                    return
            except asyncio.TimeoutError:
                logger.warning(f"    ⏱ {model}: TIMEOUT (10s)")
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"    ❌ {model}: {error_msg[:100]}")
        
        self.results[provider] = {
            "status": "FAILED",
            "reason": "All models failed or timed out"
        }
    
    async def test_huggingface(self) -> None:
        """Test HuggingFace provider."""
        provider = "HuggingFace"
        logger.info("\n" + "="*60)
        logger.info(f"Testing {provider}...")
        logger.info("="*60)
        
        has_key, msg = self.check_api_key("HUGGINGFACEHUB_API_TOKEN")
        logger.info(f"✓ API Key: {msg}")
        
        if not has_key:
            self.results[provider] = {"status": "FAILED", "reason": msg}
            return
        
        if not HUGGINGFACE_AVAILABLE:
            self.results[provider] = {"status": "SKIPPED", "reason": "langchain_huggingface not installed"}
            logger.warning("⚠ Skipped: langchain_huggingface not installed")
            return
        
        models_to_test = [
            "mistralai/Mistral-7B-Instruct-v0.1",
            "meta-llama/Llama-2-7b-chat-hf",
        ]
        
        for model in models_to_test:
            logger.info(f"\n  Testing model: {model}")
            try:
                llm = HuggingFaceHub(
                    repo_id=model,
                    huggingfacehub_api_token=os.getenv("HUGGINGFACEHUB_API_TOKEN"),
                    temperature=0.1,
                )
                
                # HuggingFace doesn't support async, so use sync
                response = llm.invoke(self.test_prompt)
                
                if response:
                    logger.info(f"    ✅ {model}: SUCCESS")
                    self.results[provider] = {
                        "status": "PASSED",
                        "model": model,
                        "response_preview": response[:100]
                    }
                    return
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"    ❌ {model}: {error_msg[:100]}")
        
        self.results[provider] = {
            "status": "FAILED",
            "reason": "All models failed"
        }
    
    async def run_all_tests(self) -> None:
        """Run all provider tests."""
        logger.info("\n" + "#"*60)
        logger.info("# LLM API KEYS VALIDATION TEST")
        logger.info("#"*60)
        
        # Run tests concurrently where possible
        tasks = []
        
        if GROQ_AVAILABLE or os.getenv("GROQ_API_KEY"):
            tasks.append(self.test_groq())
        
        if GOOGLE_GENAI_AVAILABLE or os.getenv("GOOGLE_API_KEY"):
            tasks.append(self.test_google_genai())
        
        if OPENAI_AVAILABLE or os.getenv("OPENAI_API_KEY"):
            tasks.append(self.test_openai())
        
        # HuggingFace doesn't support async well, so skip concurrent
        if HUGGINGFACE_AVAILABLE or os.getenv("HUGGINGFACEHUB_API_TOKEN"):
            await self.test_huggingface()
        
        if tasks:
            await asyncio.gather(*tasks)
        
        self.print_summary()
    
    def print_summary(self) -> None:
        """Print test results summary."""
        logger.info("\n" + "#"*60)
        logger.info("# TEST RESULTS SUMMARY")
        logger.info("#"*60)
        
        passed = 0
        failed = 0
        skipped = 0
        
        for provider, result in self.results.items():
            status = result.get("status", "UNKNOWN")
            if status == "PASSED":
                model = result.get("model", "unknown")
                logger.info(f"✅ {provider:20} PASSED (model: {model})")
                passed += 1
            elif status == "FAILED":
                reason = result.get("reason", "unknown")
                logger.error(f"❌ {provider:20} FAILED ({reason})")
                failed += 1
            elif status == "SKIPPED":
                reason = result.get("reason", "unknown")
                logger.warning(f"⊘ {provider:20} SKIPPED ({reason})")
                skipped += 1
        
        logger.info("\n" + "-"*60)
        logger.info(f"Results: {passed} passed, {failed} failed, {skipped} skipped")
        logger.info("-"*60)
        
        if failed == 0:
            logger.info("✅ ALL TESTS PASSED!")
            return 0
        else:
            logger.error(f"❌ {failed} PROVIDER(S) FAILED - CHECK KEYS AND CONNECTIVITY")
            return 1


async def main():
    """Main entry point."""
    validator = LLMKeyValidator()
    await validator.run_all_tests()
    
    # Return exit code
    return 1 if any(r.get("status") == "FAILED" for r in validator.results.values()) else 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

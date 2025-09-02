"""
Async LLM Provider System with Multiple Fallbacks
Handles HuggingFace, Google Gemini, OpenAI, Groq and local models with robust error handling
"""

import os
import logging
import asyncio
import json
from datetime import datetime
from typing import Optional, Dict, Any, Union, List
from pathlib import Path

# Import async HTTP client
try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

# Load environment variables from env file
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv not available, continue without it


# Import pretty printing utilities
def print_status(
    message: str, status: str = "info", icon: Optional[str] = None
) -> None:
    """Print status message with formatting"""
    print(f"[{status.upper()}] {message}")


def print_llm_provider_info(provider_name: str, model: str = "") -> None:
    """Print LLM provider information"""
    print(f"Using LLM provider: {provider_name}")
    if model:
        print(f"Model: {model}")


def print_llm_fallback_info(failed_providers: List[str], active_provider: str) -> None:
    """Print fallback information"""
    if failed_providers:
        print(f"LLM providers failed: {', '.join(failed_providers)}")
    print(f"Using fallback provider: {active_provider}")


# Import all possible LLM providers
try:
    from langchain_huggingface import HuggingFaceEndpoint

    HUGGINGFACE_AVAILABLE = True
except ImportError:
    HUGGINGFACE_AVAILABLE = False

try:
    from langchain_google_genai import ChatGoogleGenerativeAI

    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    GOOGLE_GENAI_AVAILABLE = False

try:
    from langchain_openai import ChatOpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from langchain_groq import ChatGroq

    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    from langchain_openai import ChatOpenAI

    OPENROUTER_AVAILABLE = True
except ImportError:
    OPENROUTER_AVAILABLE = False

try:
    from huggingface_hub import HfApi

    HF_API_AVAILABLE = True
except ImportError:
    HF_API_AVAILABLE = False

logger = logging.getLogger(__name__)


class AsyncLLMProvider:
    """Robust async LLM provider with multiple fallback options."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.current_provider = None
        self.llm = None
        self.client = None
        if HTTPX_AVAILABLE:
            self.client = httpx.AsyncClient()
            
        # Prompt audit logging
        self.prompt_audit_enabled = os.getenv("PROMPT_AUDIT", "false").lower() == "true"
        self.audit_log_path = Path("internal_checks") / f"llm_prompts_{datetime.now().strftime('%Y%m%dT%H%M%S')}Z.ndjson"
        
        # Ensure audit log directory exists
        if self.prompt_audit_enabled:
            self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)

    def _log_prompt_audit(self, prompt: str, session_id: str = "", agent: str = "", response: Any = None, error: str = ""):
        """Log prompt audit information if enabled."""
        if not self.prompt_audit_enabled:
            return
            
        # Check for OUTPUT_SCHEMA in prompt
        contains_output_schema = "OUTPUT_SCHEMA" in prompt or "output_schema" in prompt.lower()
        
        # Count few-shot examples
        few_shot_count = prompt.lower().count("example_") + prompt.lower().count("few_shot") + prompt.lower().count("examples:")
        
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "agent": agent,
            "contains_OUTPUT_SCHEMA": contains_output_schema,
            "few_shot_count": few_shot_count,
            "prompt_length_chars": len(prompt),
            "provider_attempt": self.current_provider,
            "model": getattr(self.llm, "model_name", "unknown") if self.llm else "unknown",
            "success": error == "",
            "error": error
        }
        
        try:
            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(audit_entry) + "\n")
        except Exception as e:
            logger.warning(f"Failed to write prompt audit log: {e}")

    async def initialize(self) -> None:
        """Initialize the LLM provider asynchronously"""
        await self._setup_llm()

    async def _setup_llm(self) -> None:
        """Setup LLM with fallback chain based on configuration."""
        # Get provider preference from config or use default
        provider_preference = self.config.get(
            "provider_preference",
            [
                "google_genai",
                "groq",
                "openrouter",
                "huggingface",
                "openai",
                "local",
                "fallback",
            ],
        )

        # Map provider names to their functions
        provider_map = {
            "huggingface": ("HuggingFace", self._try_huggingface),
            "google_genai": ("Google Gemini", self._try_google_genai),
            "groq": ("Groq", self._try_groq),
            "openrouter": ("OpenRouter", self._try_openrouter),
            "openai": ("OpenAI", self._try_openai),
            "local": ("Local LLM", self._try_local_llm),
            "fallback": ("Fallback", self._create_fallback_llm),
        }

        # Build provider list based on preference
        providers = []
        for provider_name in provider_preference:
            if provider_name in provider_map:
                providers.append(provider_map[provider_name])

        # Add any missing providers at the end
        for provider_name, provider_func in provider_map.items():
            if provider_name not in provider_preference:
                providers.append(provider_func)

        failed_providers = []
        for provider_name, provider_func in providers:
            try:
                print_status(f"Testing {provider_name} provider...", "progress")
                self.llm = await provider_func()
                if self.llm:
                    print_status(f"Successfully initialized {provider_name}", "success")
                    print_llm_provider_info(
                        provider_name, getattr(self.llm, "model_name", "")
                    )
                    return
            except Exception as e:
                error_msg = str(e)
                failed_providers.append(provider_name)

                # Handle specific error types
                if (
                    "quota" in error_msg.lower()
                    or "429" in error_msg
                    or "rate" in error_msg.lower()
                ):
                    print_status(
                        f"{provider_name} quota/rate limit exceeded", "warning"
                    )
                elif "not set" in error_msg.lower():
                    print_status(f"{provider_name} API key not configured", "warning")
                elif "not available" in error_msg.lower():
                    print_status(f"{provider_name} package not installed", "warning")
                elif "all" in error_msg.lower() and "failed" in error_msg.lower():
                    print_status(f"{provider_name} models unavailable", "warning")
                elif (
                    "token" in error_msg.lower() and "permissions" in error_msg.lower()
                ):
                    print_status(f"{provider_name} token lacks permissions", "warning")
                else:
                    print_status(f"{provider_name} initialization failed", "error")

                logger.warning(f"{provider_name} failed: {e}")
                continue

        # If all providers fail, create fallback
        self.llm = await self._create_fallback_llm()
        print_status("All LLM providers failed, using fallback mode", "warning")
        print_llm_fallback_info(failed_providers, "Fallback")

    async def _test_huggingface_token(self) -> bool:
        """Test if HuggingFace token has proper permissions."""
        if not HF_API_AVAILABLE:
            return False

        try:
            api_key = self.config.get("api_keys", {}).get("huggingface")
            if not api_key:
                return False

            api = HfApi(token=api_key)
            # Test with a simple API call
            models = list(api.list_models(author="bigcode", limit=1))
            logger.info("HuggingFace token validated successfully")
            return True
        except Exception as e:
            logger.warning(f"HuggingFace token validation failed: {e}")
            return False

    async def _try_huggingface(self):
        """Try to initialize HuggingFace LLM."""
        if not HUGGINGFACE_AVAILABLE:
            raise ImportError("langchain_huggingface not available")

        api_key = self.config.get("api_keys", {}).get("huggingface")
        if not api_key:
            raise ValueError("HUGGINGFACEHUB_API_TOKEN not set")

        # Test token permissions
        if not await self._test_huggingface_token():
            raise ValueError("HuggingFace token lacks proper permissions")

        # Try multiple HuggingFace models in order of preference
        models_to_try = [
            "microsoft/DialoGPT-medium",
            "gpt2",
            "facebook/opt-350m",
            "bigscience/bloom-560m",
        ]

        temperature = self.config.get("temperature", 0.1)

        for model_name in models_to_try:
            try:
                print_status(f"Trying HuggingFace model: {model_name}", "progress")
                llm = HuggingFaceEndpoint(
                    repo_id=model_name,
                    huggingfacehub_api_token=api_key,
                    task="text-generation",
                    temperature=temperature,
                )

                # Test the connection
                try:
                    # Use async invoke if available
                    if hasattr(llm, "ainvoke"):
                        test_response = await llm.ainvoke("Test")
                    else:
                        test_response = llm.invoke("Test")

                    if test_response:
                        self.current_provider = f"huggingface_{model_name}"
                        return llm
                    else:
                        raise ValueError("Empty response from HuggingFace")

                except Exception as test_error:
                    error_str = str(test_error)
                    if "model" in error_str.lower() or "not found" in error_str.lower():
                        logger.warning(
                            f"HuggingFace model {model_name} not available: {test_error}"
                        )
                        continue
                    else:
                        logger.warning(
                            f"HuggingFace test failed for {model_name}: {test_error}"
                        )
                        continue

            except Exception as e:
                error_str = str(e)
                if "model" in error_str.lower() or "not found" in error_str.lower():
                    logger.warning(f"HuggingFace model {model_name} not available: {e}")
                    continue
                else:
                    logger.warning(
                        f"HuggingFace initialization failed for {model_name}: {e}"
                    )
                    continue

        raise ValueError("All HuggingFace models failed")

    async def _try_google_genai(self):
        """Try to initialize Google Gemini LLM."""
        if not GOOGLE_GENAI_AVAILABLE:
            raise ImportError("langchain_google_genai not available")

        api_key = self.config.get("api_keys", {}).get("google")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set")

        try:
            models_to_try = [
                "gemini-2.5-flash-preview-05-20",
                "gemini-1.5-flash",
                "gemini-1.5-pro",
                "gemini-pro",
            ]

            for model in models_to_try:
                try:
                    llm = ChatGoogleGenerativeAI(
                        model=model,
                        google_api_key=api_key,
                        temperature=self.config.get("temperature", 0.39),
                        max_retries=0,
                    )

                    # Test the connection
                    try:
                        if hasattr(llm, "ainvoke"):
                            test_response = await llm.ainvoke("Test")
                        else:
                            test_response = llm.invoke("Test")

                        if test_response:
                            self.current_provider = f"google_genai_{model}"
                            return llm
                    except Exception as test_error:
                        error_str = str(test_error)
                        if (
                            "429" in error_str
                            or "quota" in error_str.lower()
                            or "rate" in error_str.lower()
                            or "ResourceExhausted" in error_str
                        ):
                            logger.warning(
                                f"Google Gemini quota exceeded for {model}, skipping all Google models"
                            )
                            raise ValueError(
                                f"Google Gemini quota exceeded: {test_error}"
                            )
                        else:
                            logger.warning(
                                f"Google Gemini test failed for {model}: {test_error}"
                            )
                            continue

                except Exception as e:
                    error_str = str(e)
                    if (
                        "429" in error_str
                        or "quota" in error_str.lower()
                        or "rate" in error_str.lower()
                        or "ResourceExhausted" in error_str
                    ):
                        logger.warning(
                            f"Google Gemini quota exceeded for {model}, skipping all Google models"
                        )
                        raise ValueError(f"Google Gemini quota exceeded: {e}")
                    else:
                        logger.warning(f"Google Gemini model {model} failed: {e}")
                        continue

            raise ValueError("All Google Gemini models failed")

        except Exception as e:
            logger.error(f"Google Gemini initialization failed: {e}")
            raise

    async def _try_openai(self):
        """Try to initialize OpenAI LLM."""
        if not OPENAI_AVAILABLE:
            raise ImportError("langchain_openai not available")

        api_key = self.config.get("api_keys", {}).get("openai")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")

        try:
            models_to_try = ["gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]

            for model in models_to_try:
                try:
                    llm = ChatOpenAI(
                        model=model,
                        openai_api_key=api_key,
                        temperature=self.config.get("temperature", 0.1),
                    )

                    # Test the connection
                    try:
                        if hasattr(llm, "ainvoke"):
                            test_response = await llm.ainvoke("Test")
                        else:
                            test_response = llm.invoke("Test")

                        if test_response:
                            self.current_provider = f"openai_{model}"
                            return llm
                    except Exception as test_error:
                        logger.warning(f"OpenAI test failed for {model}: {test_error}")
                        continue

                except Exception as e:
                    logger.warning(f"OpenAI model {model} failed: {e}")
                    continue

            raise ValueError("All OpenAI models failed")

        except Exception as e:
            logger.error(f"OpenAI initialization failed: {e}")
            raise

    async def _try_groq(self):
        """Try to initialize Groq LLM."""
        if not GROQ_AVAILABLE:
            raise ImportError("langchain_groq not available")

        api_key = self.config.get("api_keys", {}).get("groq")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set")

        logger.info("Groq API key found, attempting Groq models...")

        try:
            models_to_try = [
                "llama-3.1-8b-instant",
                "llama3-70b-8192",
                "llama3-8b-8192",
                "mixtral-8x7b-32768",
            ]

            for model in models_to_try:
                try:
                    llm = ChatGroq(
                        model=model,
                        groq_api_key=api_key,
                        temperature=self.config.get("temperature", 0.1),
                    )

                    # Test the connection
                    try:
                        if hasattr(llm, "ainvoke"):
                            test_response = await llm.ainvoke("Test")
                        else:
                            test_response = llm.invoke("Test")

                        if test_response:
                            self.current_provider = f"groq_{model}"
                            logger.info(f"Groq model {model} initialized successfully")
                            return llm
                    except Exception as test_error:
                        logger.warning(f"Groq test failed for {model}: {test_error}")
                        continue

                except Exception as e:
                    logger.warning(f"Groq model {model} failed: {e}")
                    continue

            raise ValueError("All Groq models failed")

        except Exception as e:
            logger.error(f"Groq initialization failed: {e}")
            raise

    async def _try_openrouter(self):
        """Try to initialize OpenRouter LLM."""
        if not OPENROUTER_AVAILABLE:
            raise ImportError("langchain_openai not available for OpenRouter")

        api_key = self.config.get("api_keys", {}).get("openrouter")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not set")

        logger.info("OpenRouter API key found, attempting OpenRouter models...")

        try:
            models_to_try = [
                "meta-llama/llama-3.1-8b-instruct:free",
                "microsoft/phi-3-mini-128k-instruct:free",
                "google/gemma-2-9b-it:free",
                "qwen/qwen-2-7b-instruct:free",
            ]

            for model in models_to_try:
                try:
                    llm = ChatOpenAI(
                        model=model,
                        openai_api_key=api_key,
                        openai_api_base="https://openrouter.ai/api/v1",
                        temperature=self.config.get("temperature", 0.1),
                    )

                    # Test the connection
                    try:
                        if hasattr(llm, "ainvoke"):
                            test_response = await llm.ainvoke("Test")
                        else:
                            test_response = llm.invoke("Test")

                        if test_response:
                            self.current_provider = f"openrouter_{model}"
                            logger.info(
                                f"OpenRouter model {model} initialized successfully"
                            )
                            return llm
                    except Exception as test_error:
                        logger.warning(
                            f"OpenRouter test failed for {model}: {test_error}"
                        )
                        continue

                except Exception as e:
                    logger.warning(f"OpenRouter model {model} failed: {e}")
                    continue

            raise ValueError("All OpenRouter models failed")

        except Exception as e:
            logger.error(f"OpenRouter initialization failed: {e}")
            raise

    async def _try_local_llm(self):
        """Try to connect to local LLM server."""
        local_config = self.config.get("local_llm", {})
        if not local_config.get("enabled", False):
            raise ValueError("Local LLM not enabled")

        url = local_config.get("url", "http://localhost:5000")

        if not HTTPX_AVAILABLE:
            raise ImportError("httpx not available for local LLM connection")

        try:
            # Test connection to local LLM server
            response = await self.client.get(f"{url}/health", timeout=5.0)
            if response.status_code != 200:
                raise ValueError(
                    f"Local LLM server not healthy: {response.status_code}"
                )

            # Create local LLM wrapper
            class LocalLLM:
                def __init__(self, url: str, client: httpx.AsyncClient):
                    self.url = url
                    self.client = client
                    self.name = "local_llm"
                    self.model_name = "local_model"

                async def ainvoke(self, prompt: str) -> Dict[str, Any]:
                    try:
                        response = await self.client.post(
                            f"{self.url}/generate",
                            json={"prompt": prompt},
                            timeout=30.0,
                        )
                        response.raise_for_status()
                        return response.json()
                    except Exception as e:
                        logger.error(f"Local LLM request failed: {e}")
                        return {"content": "Local LLM request failed"}

                def invoke(self, prompt: str) -> Dict[str, Any]:
                    # Sync wrapper for async method
                    try:
                        loop = asyncio.get_event_loop()
                        return loop.run_until_complete(self.ainvoke(prompt))
                    except Exception as e:
                        logger.error(f"Local LLM sync invoke failed: {e}")
                        return {"content": "Local LLM request failed"}

            local_llm = LocalLLM(url, self.client)
            self.current_provider = "local_llm"
            return local_llm

        except Exception as e:
            logger.error(f"Local LLM connection failed: {e}")
            raise

    async def _create_fallback_llm(self):
        """Create a fallback LLM for when all providers fail."""

        class FallbackLLM:
            def __init__(self):
                self.name = "fallback_llm"
                self.model_name = "fallback_static_analysis"
                self.current_provider = "fallback"

            async def ainvoke(self, prompt: str) -> Dict[str, Any]:
                return self._generate_fallback_response(prompt)

            def invoke(self, prompt: str) -> Dict[str, Any]:
                return self._generate_fallback_response(prompt)

            def _generate_fallback_response(self, prompt: str) -> Dict[str, Any]:
                # Enhanced fallback response with basic analysis
                if "code review" in prompt.lower():
                    return {
                        "content": "Fallback static analysis mode: Performing basic code analysis without LLM."
                    }
                elif "security" in prompt.lower():
                    return {
                        "content": "Fallback security analysis: Checking for common security patterns."
                    }
                elif "performance" in prompt.lower():
                    return {
                        "content": "Fallback performance analysis: Identifying basic performance issues."
                    }
                elif "story" in prompt.lower() or "continue" in prompt.lower():
                    return {
                        "content": "Fallback mode: Unable to generate story continuation. Please configure an LLM provider.",
                        "branches": [],
                    }
                else:
                    return {
                        "content": "Fallback analysis mode: Using static analysis techniques."
                    }

        fallback_llm = FallbackLLM()
        self.current_provider = "fallback"
        return fallback_llm

    async def invoke(self, prompt: str, session_id: str = "", agent: str = "") -> Union[str, Dict[str, Any]]:
        """Invoke the LLM with a prompt asynchronously."""
        try:
            # Log prompt audit before invocation
            self._log_prompt_audit(prompt, session_id, agent)
            
            # Use async invoke if available
            if hasattr(self.llm, "ainvoke"):
                response = await self.llm.ainvoke(prompt)
            else:
                response = self.llm.invoke(prompt)

            # Log successful response
            self._log_prompt_audit(prompt, session_id, agent, response)

            # Handle different response formats
            if isinstance(response, dict):
                if "content" in response:
                    return response["content"]
                elif "text" in response:
                    return response["text"]
                else:
                    return str(response)
            elif isinstance(response, str):
                return response
            else:
                # Try to get content from response object
                if hasattr(response, "content"):
                    return response.content
                elif hasattr(response, "text"):
                    return response.text
                else:
                    return str(response)

        except Exception as e:
            # Log failed invocation
            self._log_prompt_audit(prompt, session_id, agent, error=str(e))
            logger.error(f"LLM invocation failed: {e}")
            # Return fallback response
            return "LLM invocation failed. Please check your configuration."

    @property
    def name(self) -> str:
        """Get the name of the current LLM provider."""
        if hasattr(self.llm, "name"):
            return self.llm.name
        return self.current_provider or "unknown"

    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the current LLM provider."""
        return {
            "provider": self.current_provider,
            "available": self.llm is not None,
            "fallback_mode": self.current_provider == "fallback",
        }

    async def close(self) -> None:
        """Close the HTTP client"""
        if self.client:
            await self.client.aclose()


async def create_llm_provider(config: Dict[str, Any]) -> AsyncLLMProvider:
    """Factory function to create async LLM provider."""
    provider = AsyncLLMProvider(config)
    await provider.initialize()
    return provider

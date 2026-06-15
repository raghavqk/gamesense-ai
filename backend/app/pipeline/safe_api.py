"""
Production-Grade Safe API Layer for Groq
Single source of control for retries, backoff, and rate limiting.
FOLLOWING RULES 1-10: No wait_for, global semaphore, proper CancelledError handling.
"""
import asyncio
import random
import logging
from typing import Dict, Any, Optional, List
from httpx import HTTPStatusError

logger = logging.getLogger(__name__)

# RULE 3: GLOBAL RATE LIMITER (MANDATORY)
# Single semaphore controlling ALL API calls
GLOBAL_SEMAPHORE = asyncio.Semaphore(2)

# Configuration
MAX_RETRIES = 5
BASE_DELAY = 1.0
FALLBACK_RESULT = {"kills": [], "error": "api_failed"}


async def safe_groq_call(client, payload: Dict[str, Any]) -> Optional[Dict]:
    """
    RULE 4: Safe API wrapper - single source of control.
    
    Responsibilities:
    - Handle retries (max 5)
    - Handle HTTP 429 specifically  
    - Apply exponential backoff with jitter
    - Handle graceful cancellation (RULE 8)
    - Return fallback instead of crashing
    
    CRITICAL: NO asyncio.wait_for inside this function (RULE 2)
    """
    for attempt in range(MAX_RETRIES):
        try:
            # RULE 3: ALL API calls through global semaphore
            async with GLOBAL_SEMAPHORE:
                logger.debug(f"API call attempt {attempt + 1}/{MAX_RETRIES}")
                
                # Make API call - NO timeout wrapper here (RULE 2)
                response = await client.chat.completions.create(**payload)
                
                # Parse response
                content = response.choices[0].message.content
                try:
                    import json
                    return json.loads(content)
                except json.JSONDecodeError:
                    # Try to extract JSON from markdown
                    import re
                    json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group(1))
                    return {"raw_response": content}
                    
        except HTTPStatusError as e:
            # RULE 5: Exponential backoff for 429 errors
            if e.response.status_code == 429:
                delay = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"429 rate limit hit, backing off for {delay:.1f}s (attempt {attempt + 1})")
                
                try:
                    await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    # RULE 8: Handle cancellation gracefully
                    logger.warning("API call cancelled during backoff")
                    return None
            else:
                # Non-429 error - log and continue to retry
                logger.warning(f"HTTP error {e.response.status_code}: {str(e)[:100]}")
                if attempt < MAX_RETRIES - 1:
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    try:
                        await asyncio.sleep(delay)
                    except asyncio.CancelledError:
                        logger.warning("API call cancelled during backoff")
                        return None
                else:
                    break
                    
        except asyncio.CancelledError:
            # RULE 8: Handle cancellation at top level too
            logger.warning("API call cancelled")
            return None
            
        except Exception as e:
            # Other errors (network, etc.) - retry with backoff
            error_str = str(e)
            if "429" in error_str or "Too Many Requests" in error_str:
                delay = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"Rate limit detected in error message, backing off {delay:.1f}s")
            else:
                delay = (2 ** attempt) + random.uniform(0, 1)
                logger.debug(f"API error: {error_str[:100]}, retrying in {delay:.1f}s")
            
            if attempt < MAX_RETRIES - 1:
                try:
                    await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    logger.warning("API call cancelled during error backoff")
                    return None
            else:
                logger.error(f"Final retry failed: {error_str[:100]}")
                break
    
    # All retries exhausted
    logger.error(f"API call failed after {MAX_RETRIES} retries")
    return None


async def safe_groq_call_batch(client, payload: Dict[str, Any], batch_info: str = "") -> Optional[Dict]:
    """
    Batched version of safe_groq_call with additional logging.
    """
    for attempt in range(MAX_RETRIES):
        try:
            async with GLOBAL_SEMAPHORE:
                if batch_info:
                    logger.debug(f"Batch {batch_info}: attempt {attempt + 1}/{MAX_RETRIES}")
                
                response = await client.chat.completions.create(**payload)
                
                content = response.choices[0].message.content
                try:
                    import json
                    return json.loads(content)
                except json.JSONDecodeError:
                    import re
                    json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group(1))
                    return {"raw_response": content}
                    
        except HTTPStatusError as e:
            if e.response.status_code == 429:
                delay = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"Batch {batch_info}: 429 hit, backing off {delay:.1f}s")
                try:
                    await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    logger.warning(f"Batch {batch_info} cancelled during backoff")
                    return None
            else:
                if attempt < MAX_RETRIES - 1:
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    try:
                        await asyncio.sleep(delay)
                    except asyncio.CancelledError:
                        return None
                else:
                    break
                    
        except asyncio.CancelledError:
            logger.warning(f"Batch {batch_info} cancelled")
            return None
            
        except Exception as e:
            error_str = str(e)
            delay = (2 ** attempt) + random.uniform(0, 1)
            
            if "429" in error_str or "Too Many Requests" in error_str:
                logger.warning(f"Batch {batch_info}: rate limit in error, backoff {delay:.1f}s")
            
            if attempt < MAX_RETRIES - 1:
                try:
                    await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    return None
            else:
                logger.error(f"Batch {batch_info} failed after {MAX_RETRIES} retries")
                break
    
    return None


# Stats tracking for monitoring
_api_stats = {
    "total_calls": 0,
    "429_errors": 0,
    "retries": 0,
    "failures": 0,
}


def get_api_stats() -> Dict[str, int]:
    """Get API call statistics for monitoring."""
    return _api_stats.copy()


def reset_api_stats():
    """Reset API statistics."""
    global _api_stats
    _api_stats = {
        "total_calls": 0,
        "429_errors": 0,
        "retries": 0,
        "failures": 0,
    }

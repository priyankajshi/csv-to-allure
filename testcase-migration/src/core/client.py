import asyncio
import logging
import aiohttp
from typing import Dict, Any, Optional

class AllureClient:
    """
    Async client for interacting with Allure TestOps API.
    """
    def __init__(self, api_endpoint: str, api_token: str, timeout: int = 30, max_retries: int = 3, insecure: bool = False):
        self.api_endpoint = api_endpoint
        self.api_token = api_token
        self.timeout = timeout
        self.max_retries = max_retries
        self.insecure = insecure
        self.logger = logging.getLogger("migration.client")
        self.headers = {
            "Authorization": f"Api-Token {self.api_token}",
            "Content-Type": "application/json"
        }

    async def migrate_test_case(self, session: aiohttp.ClientSession, payload: Dict[str, Any]) -> bool:
        """
        Sends the payload to the Allure TestOps API with retry logic.
        """
        test_name = payload.get('name', 'Unknown')
        self.logger.debug(f"Migrating '{test_name}' to {self.api_endpoint}")
        
        for attempt in range(self.max_retries):
            try:
                # Disable SSL verification if requested
                ssl_context = False if self.insecure else None
                
                async with session.post(
                    self.api_endpoint, 
                    json=payload, 
                    headers=self.headers, 
                    timeout=self.timeout,
                    ssl=ssl_context
                ) as response:
                    
                    if response.status == 200 or response.status == 201:
                        result = await response.json()
                        self.logger.info(
                            f"SUCCESS: '{test_name}' migrated. "
                            f"ID: {result.get('id')}, External ID: {result.get('externalId')}"
                        )
                        return True
                    
                    elif response.status == 429:  # Rate limit
                        wait_time = 2 ** attempt
                        self.logger.warning(f"Rate limited for '{test_name}', retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    else:
                        text = await response.text()
                        self.logger.error(
                            f"FAILURE: '{test_name}' - Status: {response.status}, Response: {text[:200]}"
                        )
                        return False

            except asyncio.TimeoutError:
                self.logger.warning(f"Timeout for '{test_name}' on attempt {attempt + 1}, retrying...")
            except aiohttp.ClientError as e:
                self.logger.error(f"Request error for '{test_name}' on attempt {attempt + 1}: {e}")
            
            if attempt < self.max_retries - 1:
                await asyncio.sleep(1)
        
        self.logger.error(f"Failed to migrate '{test_name}' after {self.max_retries} attempts")
        return False

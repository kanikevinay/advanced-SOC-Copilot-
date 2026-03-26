"""VirusTotal API Integration for IP Reputation Scanning"""

import os
import time
from typing import Optional, Dict
from dataclasses import dataclass
from datetime import datetime
import requests
from functools import lru_cache

from soc_copilot.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class VTIPInfo:
    """VirusTotal IP reputation information"""
    ip_address: str
    reputation: int  # -100 to 100 (negative = malicious)
    malicious_votes: int
    undetected_votes: int
    last_update: str
    asn: Optional[str] = None
    country: Optional[str] = None
    error: Optional[str] = None
    
    @property
    def is_malicious(self) -> bool:
        """Check if IP has malicious reputation"""
        return self.reputation < -50 or self.malicious_votes > 5
    
    @property
    def risk_level(self) -> str:
        """Categorize risk: Critical, High, Medium, Low, Unknown"""
        if self.error:
            return "Unknown"
        if self.reputation < -75 or self.malicious_votes > 20:
            return "Critical"
        if self.reputation < -50 or self.malicious_votes > 10:
            return "High"
        if self.reputation < -25 or self.malicious_votes > 5:
            return "Medium"
        if self.reputation < 0 or self.malicious_votes > 0:
            return "Low"
        return "Clean"


class VirusTotalClient:
    """Client for VirusTotal IP reputation API"""
    
    API_BASE = "https://www.virustotal.com/api/v3"
    
    def __init__(self, api_key: Optional[str] = None, cache_size: int = 500):
        """
        Initialize VT client
        
        Args:
            api_key: VirusTotal API key (optional, from env var VT_API_KEY)
            cache_size: Number of lookups to cache
        """
        self.api_key = api_key or os.environ.get("VT_API_KEY")
        self.cache_size = cache_size
        self._cache: Dict[str, VTIPInfo] = {}
        self._request_count = 0
        self._last_request_time = 0
        self._enabled = bool(self.api_key)
        
        if not self._enabled:
            logger.warning(
                "virustotal_disabled",
                reason="No API key provided. Set VT_API_KEY env var or pass api_key parameter."
            )
    
    def lookup_ip(self, ip: str, force_refresh: bool = False) -> VTIPInfo:
        """
        Lookup IP reputation on VirusTotal
        
        Args:
            ip: IP address to lookup
            force_refresh: Skip cache and force API call
            
        Returns:
            VTIPInfo with reputation data or error information
        """
        if not ip:
            return VTIPInfo(ip, 0, 0, 0, "", error="Empty IP address")
        
        # Check cache first
        if not force_refresh and ip in self._cache:
            logger.debug(f"vt_cache_hit", ip=ip)
            return self._cache[ip]
        
        # If API key not available, return limited info
        if not self._enabled:
            result = VTIPInfo(
                ip_address=ip,
                reputation=0,
                malicious_votes=0,
                undetected_votes=0,
                last_update=datetime.now().isoformat(),
                error="VirusTotal API key not configured"
            )
            self._update_cache(ip, result)
            return result
        
        # Call VT API
        return self._fetch_ip_reputation(ip)
    
    def _fetch_ip_reputation(self, ip: str) -> VTIPInfo:
        """Fetch IP reputation from VirusTotal API"""
        try:
            # Rate limiting: max 4 requests per minute
            self._rate_limit()
            
            url = f"{self.API_BASE}/ip_addresses/{ip}"
            headers = {"x-apikey": self.api_key}
            
            logger.debug(f"vt_api_call", ip=ip, url=url)
            
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            
            data = response.json().get("data", {})
            attributes = data.get("attributes", {})
            
            # Extract reputation and voting data
            last_analysis = attributes.get("last_analysis_results", {})
            malicious_count = sum(
                1 for v in last_analysis.values() 
                if v.get("category") == "malicious"
            )
            undetected_count = sum(
                1 for v in last_analysis.values() 
                if v.get("category") == "undetected"
            )
            
            result = VTIPInfo(
                ip_address=ip,
                reputation=attributes.get("reputation", 0),
                malicious_votes=malicious_count,
                undetected_votes=undetected_count,
                last_update=datetime.fromtimestamp(
                    attributes.get("last_analysis_date", 0)
                ).isoformat() if attributes.get("last_analysis_date") else "Unknown",
                asn=attributes.get("asn", {}).get("asn"),
                country=attributes.get("country"),
            )
            
            logger.info(
                "vt_lookup_success",
                ip=ip,
                reputation=result.reputation,
                risk=result.risk_level
            )
            
            self._update_cache(ip, result)
            return result
            
        except requests.exceptions.Timeout:
            logger.warning(f"vt_timeout", ip=ip)
            result = VTIPInfo(ip, 0, 0, 0, "", error="Request timeout")
            self._update_cache(ip, result)
            return result
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"vt_api_error", ip=ip, error=str(e))
            result = VTIPInfo(ip, 0, 0, 0, "", error=f"API error: {str(e)[:50]}")
            self._update_cache(ip, result)
            return result
            
        except Exception as e:
            logger.error(f"vt_parse_error", ip=ip, error=str(e))
            result = VTIPInfo(ip, 0, 0, 0, "", error=f"Parse error: {str(e)[:50]}")
            self._update_cache(ip, result)
            return result
    
    def _rate_limit(self):
        """Enforce rate limit: max 4 requests per minute for free tier"""
        now = time.time()
        if self._request_count >= 4:
            time_since_first = now - self._last_request_time
            if time_since_first < 60:
                sleep_time = 60 - time_since_first
                logger.debug(f"vt_rate_limit", sleep_seconds=sleep_time)
                time.sleep(sleep_time)
            self._request_count = 0
            self._last_request_time = now
        else:
            self._last_request_time = now
        
        self._request_count += 1
    
    def _update_cache(self, ip: str, result: VTIPInfo):
        """Update cache with result"""
        self._cache[ip] = result
        
        # Simple LRU: if cache too large, remove oldest entry
        if len(self._cache) > self.cache_size:
            oldest_ip = next(iter(self._cache))
            del self._cache[oldest_ip]
    
    def get_cached_ips(self) -> Dict[str, VTIPInfo]:
        """Get all cached IP lookups"""
        return dict(self._cache)
    
    def clear_cache(self):
        """Clear all cached results"""
        self._cache.clear()
        logger.info("vt_cache_cleared")
    
    def stats(self) -> dict:
        """Get client statistics"""
        return {
            "enabled": self._enabled,
            "cache_size": len(self._cache),
            "api_key_configured": bool(self.api_key),
        }


# Global VT client instance
_vt_client: Optional[VirusTotalClient] = None


def get_vt_client(api_key: Optional[str] = None) -> VirusTotalClient:
    """Get or create global VT client"""
    global _vt_client
    if _vt_client is None:
        _vt_client = VirusTotalClient(api_key=api_key)
    return _vt_client

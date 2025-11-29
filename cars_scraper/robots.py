"""
Robots.txt checking and compliance utilities.
"""

import re
import logging
from urllib.parse import urlparse, urljoin
from typing import Optional, List
import requests

logger = logging.getLogger(__name__)


class RobotsChecker:
    """Check robots.txt compliance for scraping."""
    
    def __init__(self, base_url: str, user_agent: str = "*"):
        """
        Initialize robots.txt checker.
        
        Args:
            base_url: Base URL of the website
            user_agent: User agent string to check (default: "*")
        """
        self.base_url = base_url
        self.user_agent = user_agent
        self.parsed = urlparse(base_url)
        self.robots_url = f"{self.parsed.scheme}://{self.parsed.netloc}/robots.txt"
        self._rules: Optional[dict] = None
        self._checked = False
    
    def _fetch_robots_txt(self) -> Optional[str]:
        """Fetch robots.txt content."""
        try:
            response = requests.get(self.robots_url, timeout=5)
            if response.status_code == 200:
                return response.text
            elif response.status_code == 404:
                logger.info(f"No robots.txt found at {self.robots_url}")
                return None
            else:
                logger.warning(f"robots.txt returned status {response.status_code}")
                return None
        except requests.RequestException as e:
            logger.warning(f"Failed to fetch robots.txt: {e}")
            return None
    
    def _parse_robots_txt(self, content: str) -> dict:
        """Parse robots.txt content into rules."""
        rules = {}
        current_agents = []
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Match User-agent: line
            user_agent_match = re.match(r'User-agent:\s*(.+)', line, re.IGNORECASE)
            if user_agent_match:
                current_agents = [ua.strip().lower() for ua in user_agent_match.group(1).split(',')]
                continue
            
            # Match Allow/Disallow lines
            allow_match = re.match(r'Allow:\s*(.+)', line, re.IGNORECASE)
            disallow_match = re.match(r'Disallow:\s*(.+)', line, re.IGNORECASE)
            
            if allow_match or disallow_match:
                path = (allow_match or disallow_match).group(1).strip()
                is_allowed = allow_match is not None
                
                for agent in current_agents:
                    if agent not in rules:
                        rules[agent] = {'allow': [], 'disallow': []}
                    
                    if is_allowed:
                        rules[agent]['allow'].append(path)
                    else:
                        rules[agent]['disallow'].append(path)
        
        return rules
    
    def check(self) -> bool:
        """
        Check robots.txt and parse rules.
        
        Returns:
            True if robots.txt was successfully checked (even if not found)
        """
        if self._checked:
            return True
        
        content = self._fetch_robots_txt()
        if content is None:
            # No robots.txt found - assume allowed
            self._rules = {}
            self._checked = True
            return True
        
        self._rules = self._parse_robots_txt(content)
        self._checked = True
        return True
    
    def is_allowed(self, url: str) -> bool:
        """
        Check if a URL is allowed by robots.txt.
        
        Args:
            url: URL to check
        
        Returns:
            True if allowed, False if disallowed, True if robots.txt not checked/available
        """
        if not self._checked:
            self.check()
        
        if not self._rules:
            # No rules found - assume allowed
            return True
        
        # Find matching user agent rules (check specific, then wildcard)
        user_agents_to_check = [self.user_agent.lower(), "*"]
        parsed_url = urlparse(url)
        path = parsed_url.path
        
        for ua in user_agents_to_check:
            if ua not in self._rules:
                continue
            
            rules = self._rules[ua]
            disallowed = False
            
            # Check disallow rules first
            for disallow_path in rules.get('disallow', []):
                if self._path_matches(path, disallow_path):
                    disallowed = True
                    break
            
            # Check allow rules (allow overrides disallow)
            for allow_path in rules.get('allow', []):
                if self._path_matches(path, allow_path):
                    return True
            
            # If disallowed and no allow rule matches, it's disallowed
            if disallowed:
                return False
        
        # Default: allowed if no specific rule matches
        return True
    
    def _path_matches(self, path: str, pattern: str) -> bool:
        """
        Check if a path matches a robots.txt pattern.
        
        Args:
            path: URL path to check
            pattern: Pattern from robots.txt (may contain wildcards)
        
        Returns:
            True if path matches pattern
        """
        if not pattern:
            return False
        
        # Convert pattern to regex
        # * matches any sequence of characters
        # $ matches end of string
        pattern = pattern.replace('*', '.*')
        if not pattern.endswith('$'):
            pattern = pattern + '.*'
        
        try:
            return bool(re.match(pattern, path))
        except re.error:
            # Invalid regex, do simple prefix match
            return path.startswith(pattern.rstrip('*'))
    
    def get_disallowed_paths(self) -> List[str]:
        """
        Get list of disallowed paths for the user agent.
        
        Returns:
            List of disallowed path patterns
        """
        if not self._checked:
            self.check()
        
        disallowed = []
        user_agents_to_check = [self.user_agent.lower(), "*"]
        
        for ua in user_agents_to_check:
            if ua in self._rules:
                disallowed.extend(self._rules[ua].get('disallow', []))
        
        return list(set(disallowed))  # Remove duplicates


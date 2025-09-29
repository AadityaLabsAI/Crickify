#!/usr/bin/env python3
"""
Optimized HTTP Session Manager
=============================

Advanced session management with connection pooling, session reuse, 
and performance optimization for cricket data scraping.
"""

import asyncio
import aiohttp
import logging
import time
import threading
from typing import Dict, Optional, List, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import weakref
from contextlib import asynccontextmanager
from performance_cache import performance_cache

logger = logging.getLogger(__name__)

@dataclass
class SessionMetrics:
    """Metrics for session performance monitoring."""
    requests_count: int = 0
    success_count: int = 0
    error_count: int = 0
    total_response_time: float = 0.0
    active_connections: int = 0
    created_sessions: int = 0
    reused_sessions: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.requests_count == 0:
            return 0.0
        return (self.success_count / self.requests_count) * 100
    
    @property 
    def average_response_time(self) -> float:
        """Calculate average response time in milliseconds."""
        if self.success_count == 0:
            return 0.0
        return (self.total_response_time / self.success_count) * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'requests_count': self.requests_count,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'success_rate': self.success_rate,
            'average_response_time_ms': self.average_response_time,
            'active_connections': self.active_connections,
            'created_sessions': self.created_sessions,
            'reused_sessions': self.reused_sessions,
            'session_reuse_rate': (self.reused_sessions / max(1, self.created_sessions + self.reused_sessions)) * 100
        }

class OptimizedHTTPSession:
    """
    Optimized HTTP session with advanced connection management and monitoring.
    """
    
    def __init__(self, 
                 session_id: str,
                 connector_limit: int = 30,
                 connector_limit_per_host: int = 10,
                 timeout_total: int = 30,
                 timeout_connect: int = 10,
                 keepalive_timeout: int = 30,
                 enable_cleanup_closed: bool = True):
        """
        Initialize optimized HTTP session.
        
        Args:
            session_id: Unique identifier for this session
            connector_limit: Total connection pool size
            connector_limit_per_host: Max connections per host
            timeout_total: Total request timeout in seconds
            timeout_connect: Connection timeout in seconds
            keepalive_timeout: TCP keepalive timeout in seconds
            enable_cleanup_closed: Enable automatic cleanup of closed connections
        """
        self.session_id = session_id
        self.connector_limit = connector_limit
        self.connector_limit_per_host = connector_limit_per_host
        self.timeout_total = timeout_total
        self.timeout_connect = timeout_connect
        self.keepalive_timeout = keepalive_timeout
        self.enable_cleanup_closed = enable_cleanup_closed
        
        # Session objects
        self._session: Optional[aiohttp.ClientSession] = None
        self._connector: Optional[aiohttp.TCPConnector] = None
        self._lock = asyncio.Lock()
        
        # Monitoring
        self.metrics = SessionMetrics()
        self.created_at = time.time()
        self.last_used = time.time()
        
        # Request tracking
        self._active_requests = set()
        self._domain_last_request = {}
        
        # Headers for browser-like behavior
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
    
    async def _create_session(self) -> aiohttp.ClientSession:
        """Create a new HTTP session with optimized settings."""
        if self._session and not self._session.closed:
            return self._session
        
        # Create optimized TCP connector
        self._connector = aiohttp.TCPConnector(
            limit=self.connector_limit,
            limit_per_host=self.connector_limit_per_host,
            ttl_dns_cache=600,  # 10 minutes DNS cache
            use_dns_cache=True,
            keepalive_timeout=self.keepalive_timeout,
            enable_cleanup_closed=self.enable_cleanup_closed,
            force_close=False,  # Keep connections alive
            family=0,  # Allow both IPv4 and IPv6
        )
        
        # Create session with optimized timeout and connector
        timeout = aiohttp.ClientTimeout(
            total=self.timeout_total,
            connect=self.timeout_connect,
            sock_read=15,
            sock_connect=self.timeout_connect
        )
        
        self._session = aiohttp.ClientSession(
            connector=self._connector,
            timeout=timeout,
            headers=self.headers,
            cookie_jar=aiohttp.CookieJar(unsafe=True),  # Allow all cookies
            auto_decompress=True,
            trust_env=True
        )
        
        self.metrics.created_sessions += 1
        logger.debug(f"🔗 Created new HTTP session {self.session_id}")
        return self._session
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Get the HTTP session, creating it if necessary."""
        async with self._lock:
            if self._session and not self._session.closed:
                self.metrics.reused_sessions += 1
                self.last_used = time.time()
                return self._session
            else:
                return await self._create_session()
    
    async def request(self, 
                     method: str,
                     url: str,
                     rate_limit_delay: float = 1.0,
                     **kwargs) -> Optional[aiohttp.ClientResponse]:
        """
        Make an HTTP request with rate limiting and monitoring.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            rate_limit_delay: Delay between requests to same domain
            **kwargs: Additional request parameters
        """
        start_time = time.time()
        request_id = f"{method}_{url}_{id(self)}"
        
        # Rate limiting per domain
        domain = self._extract_domain(url)
        await self._apply_rate_limit(domain, rate_limit_delay)
        
        # Track active request
        self._active_requests.add(request_id)
        self.metrics.requests_count += 1
        
        try:
            session = await self.get_session()
            
            # Make request
            async with session.request(method, url, **kwargs) as response:
                response_time = time.time() - start_time
                self.metrics.total_response_time += response_time
                
                if response.status == 200:
                    self.metrics.success_count += 1
                    logger.debug(f"✅ {method} {url} - {response.status} ({response_time:.2f}s)")
                else:
                    self.metrics.error_count += 1
                    logger.warning(f"⚠️ {method} {url} - {response.status} ({response_time:.2f}s)")
                
                # Update performance cache metrics
                performance_cache.performance_metrics['response_times'][f'http_{method.lower()}'].append(response_time * 1000)
                
                return response
                
        except Exception as e:
            response_time = time.time() - start_time
            self.metrics.error_count += 1
            logger.error(f"❌ {method} {url} failed after {response_time:.2f}s: {e}")
            return None
        
        finally:
            self._active_requests.discard(request_id)
            self._domain_last_request[domain] = time.time()
    
    def get(self, url: str, **kwargs):
        """Convenience method for GET requests that returns an async context manager."""
        class _AsyncContextManager:
            def __init__(self, session, method, url, **kwargs):
                self.session = session
                self.method = method
                self.url = url
                self.kwargs = kwargs
                
            async def __aenter__(self):
                session_obj = await self.session.get_session()
                self._response = await session_obj.request(self.method, self.url, **self.kwargs)
                return self._response
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                # Properly close the response to prevent connection leaks
                if hasattr(self, '_response') and self._response:
                    try:
                        self._response.close()
                        # Ensure connection is returned to pool
                        await asyncio.sleep(0)  # Allow response to be properly released
                    except Exception as e:
                        logger.debug(f"Error closing response: {e}")
                    finally:
                        self._response = None
        
        return _AsyncContextManager(self, 'GET', url, **kwargs)
    
    def post(self, url: str, **kwargs):
        """Convenience method for POST requests that returns an async context manager."""
        class _AsyncContextManager:
            def __init__(self, session, method, url, **kwargs):
                self.session = session
                self.method = method
                self.url = url
                self.kwargs = kwargs
                
            async def __aenter__(self):
                session_obj = await self.session.get_session()
                self._response = await session_obj.request(self.method, self.url, **self.kwargs)
                return self._response
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                # Properly close the response to prevent connection leaks
                if hasattr(self, '_response') and self._response:
                    try:
                        self._response.close()
                        # Ensure connection is returned to pool
                        await asyncio.sleep(0)  # Allow response to be properly released
                    except Exception as e:
                        logger.debug(f"Error closing response: {e}")
                    finally:
                        self._response = None
        
        return _AsyncContextManager(self, 'POST', url, **kwargs)
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc
        except Exception:
            return "unknown"
    
    async def _apply_rate_limit(self, domain: str, delay: float):
        """Apply rate limiting for respectful scraping."""
        if domain in self._domain_last_request:
            elapsed = time.time() - self._domain_last_request[domain]
            if elapsed < delay:
                await asyncio.sleep(delay - elapsed)
    
    async def close(self):
        """Close the session and clean up resources."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug(f"🔒 Closed HTTP session {self.session_id}")
        
        if self._connector:
            await self._connector.close()
    
    def is_healthy(self) -> bool:
        """Check if session is healthy and should be kept."""
        if not self._session or self._session.closed:
            return False
        
        # Check if session hasn't been used for too long
        max_idle_time = 300  # 5 minutes
        if time.time() - self.last_used > max_idle_time:
            return False
        
        # Check success rate
        if self.metrics.requests_count > 10 and self.metrics.success_rate < 50:
            return False
        
        return True

class SessionManager:
    """
    Central HTTP session manager with connection pooling and optimization.
    """
    
    def __init__(self, 
                 max_sessions: int = 5,
                 session_timeout: float = 300.0,
                 cleanup_interval: float = 60.0):
        """
        Initialize session manager.
        
        Args:
            max_sessions: Maximum number of concurrent sessions
            session_timeout: Session timeout in seconds
            cleanup_interval: Cleanup interval in seconds
        """
        self.max_sessions = max_sessions
        self.session_timeout = session_timeout
        self.cleanup_interval = cleanup_interval
        
        # Session pool
        self._sessions: Dict[str, OptimizedHTTPSession] = {}
        self._session_assignments: Dict[str, str] = {}  # domain -> session_id
        self._lock = threading.RLock()
        
        # Monitoring
        self.total_metrics = SessionMetrics()
        
        # Background cleanup
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background cleanup task."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                self._cleanup_task = loop.create_task(self._cleanup_worker())
        except RuntimeError:
            pass
    
    async def _cleanup_worker(self):
        """Background worker for session cleanup."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_unhealthy_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Session cleanup error: {e}")
    
    async def _cleanup_unhealthy_sessions(self):
        """Remove unhealthy sessions."""
        with self._lock:
            unhealthy_sessions = [
                session_id for session_id, session in self._sessions.items()
                if not session.is_healthy()
            ]
        
        for session_id in unhealthy_sessions:
            await self._remove_session(session_id)
    
    async def _remove_session(self, session_id: str):
        """Remove a session and clean up."""
        with self._lock:
            if session_id not in self._sessions:
                return
                
            session = self._sessions[session_id]
            del self._sessions[session_id]
            
            # Remove domain assignments
            self._session_assignments = {
                domain: sid for domain, sid in self._session_assignments.items()
                if sid != session_id
            }
        
        await session.close()
        logger.info(f"🗑️ Removed unhealthy session {session_id}")
    
    def _get_session_for_domain(self, domain: str) -> Optional[str]:
        """Get assigned session ID for domain."""
        return self._session_assignments.get(domain)
    
    def _assign_session_to_domain(self, domain: str, session_id: str):
        """Assign a session to a domain."""
        self._session_assignments[domain] = session_id
    
    async def get_session_for_url(self, url: str) -> OptimizedHTTPSession:
        """Get an optimized session for the given URL."""
        domain = self._extract_domain(url)
        
        with self._lock:
            # Check if we have an existing session for this domain
            session_id = self._get_session_for_domain(domain)
            
            if session_id and session_id in self._sessions:
                session = self._sessions[session_id]
                if session.is_healthy():
                    return session
                else:
                    # Remove unhealthy session
                    asyncio.create_task(self._remove_session(session_id))
            
            # Create new session if we have capacity
            if len(self._sessions) < self.max_sessions:
                session_id = f"session_{domain}_{int(time.time())}"
                session = OptimizedHTTPSession(session_id)
                self._sessions[session_id] = session
                self._assign_session_to_domain(domain, session_id)
                logger.info(f"🆕 Created new session {session_id} for {domain}")
                return session
            
            # Reuse least recently used session
            oldest_session_id = min(
                self._sessions.keys(),
                key=lambda sid: self._sessions[sid].last_used
            )
            session = self._sessions[oldest_session_id]
            self._assign_session_to_domain(domain, oldest_session_id)
            logger.debug(f"♻️ Reusing session {oldest_session_id} for {domain}")
            return session
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc
        except Exception:
            return "unknown"
    
    @asynccontextmanager
    async def request_session(self, url: str):
        """Context manager for getting a session for requests."""
        session = await self.get_session_for_url(url)
        try:
            yield session
        finally:
            # Session stays alive for reuse
            pass
    
    async def make_request(self, 
                          method: str, 
                          url: str, 
                          rate_limit_delay: float = 1.0,
                          **kwargs) -> Optional[str]:
        """
        Make an HTTP request and return response text.
        
        Args:
            method: HTTP method
            url: Request URL
            rate_limit_delay: Rate limit delay in seconds
            **kwargs: Additional request parameters
        """
        async with self.request_session(url) as session:
            response = await session.request(method, url, rate_limit_delay, **kwargs)
            if response and response.status == 200:
                return await response.text()
            return None
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics for all sessions."""
        with self._lock:
            metrics = {
                'session_count': len(self._sessions),
                'active_sessions': sum(1 for s in self._sessions.values() if s.is_healthy()),
                'domain_assignments': len(self._session_assignments),
                'total_metrics': self.total_metrics.to_dict(),
                'sessions': {}
            }
            
            # Individual session metrics
            for session_id, session in self._sessions.items():
                metrics['sessions'][session_id] = {
                    'metrics': session.metrics.to_dict(),
                    'healthy': session.is_healthy(),
                    'created_at': session.created_at,
                    'last_used': session.last_used,
                    'age_seconds': time.time() - session.created_at
                }
            
            return metrics
    
    async def close_all_sessions(self):
        """Close all sessions and clean up."""
        with self._lock:
            session_ids = list(self._sessions.keys())
        
        for session_id in session_ids:
            await self._remove_session(session_id)
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        logger.info("🔒 All sessions closed")

# Global session manager instance
session_manager = SessionManager()

# Cleanup registration for graceful shutdown
import atexit
def _cleanup_sessions():
    """Cleanup sessions on exit."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(session_manager.close_all_sessions())
    except:
        pass

atexit.register(_cleanup_sessions)

# Utility functions for easy integration
async def get_url_content(url: str, rate_limit_delay: float = 1.0, **kwargs) -> Optional[str]:
    """Get content from URL using optimized session management."""
    return await session_manager.make_request('GET', url, rate_limit_delay, **kwargs)

async def post_url_content(url: str, rate_limit_delay: float = 1.0, **kwargs) -> Optional[str]:
    """Post to URL using optimized session management."""
    return await session_manager.make_request('POST', url, rate_limit_delay, **kwargs)
"""
CDN Manager
===========

CDN integration for static asset delivery and result distribution.

Mathematical Foundation (Knuth):
- Geographic distribution optimization
- Cache invalidation strategies
- Bandwidth optimization: O(1) edge delivery vs O(d) direct

Practical Implementation (Graham):
- Multi-CDN failover
- Smart routing based on latency
- Cost optimization across providers
"""

import hashlib
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class CDNEndpoint:
    """
    CDN endpoint configuration.

    Latency Analysis (Knuth):
    -------------------------
    Total latency = DNS + TCP + TLS + TTFB + Transfer
    CDN reduces: TTFB (geographically closer)
    """
    name: str
    base_url: str
    regions: List[str]
    priority: int = 0
    max_file_size_mb: int = 100


class CDNManager:
    """
    Manage CDN distribution for static assets and results.

    Distribution Strategy (Graham):
    -------------------------------
    - Static assets: Permanent cache with versioning
    - Results: Temporary cache with TTL
    - Large files: Chunked upload/download

    Example:
        >>> cdn = CDNManager()
        >>> cdn.upload_result('result.png', '/tmp/result.png')
        >>> url = cdn.get_url('result.png')
    """

    def __init__(
        self,
        enable_cdn: bool = True,
        primary_cdn: str = 'cloudflare',
        fallback_cdn: Optional[str] = None
    ):
        """
        Initialize CDN manager.

        Parameters:
        -----------
        enable_cdn : bool
            Enable CDN distribution
        primary_cdn : str
            Primary CDN provider
        fallback_cdn : str, optional
            Fallback CDN provider
        """
        self.enabled = enable_cdn
        self.primary_cdn = primary_cdn
        self.fallback_cdn = fallback_cdn

        # CDN endpoints (configured based on deployment)
        self.endpoints: Dict[str, CDNEndpoint] = {
            'cloudflare': CDNEndpoint(
                name='Cloudflare',
                base_url='https://cdn.example.com',
                regions=['global'],
                priority=1,
                max_file_size_mb=100
            ),
            'aws_cloudfront': CDNEndpoint(
                name='AWS CloudFront',
                base_url='https://d1234.cloudfront.net',
                regions=['us-east', 'us-west', 'eu-west', 'ap-southeast'],
                priority=2,
                max_file_size_mb=20480  # 20 GB
            ),
            'local': CDNEndpoint(
                name='Local Storage',
                base_url='http://localhost:8000/static',
                regions=['local'],
                priority=100,  # Lowest priority (fallback)
                max_file_size_mb=1000
            )
        }

        # Upload statistics
        self.upload_count = 0
        self.total_bytes_uploaded = 0

        logger.info(f"CDN Manager initialized: primary={primary_cdn}, enabled={enable_cdn}")

    def upload_file(
        self,
        file_path: str,
        cdn_path: str,
        content_type: str = 'image/png',
        cache_control: str = 'public, max-age=3600',
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Upload file to CDN.

        Complexity: O(n) for file transfer where n = file size

        Parameters:
        -----------
        file_path : str
            Local file path
        cdn_path : str
            CDN destination path
        content_type : str
            MIME type
        cache_control : str
            Cache control header
        metadata : dict, optional
            Additional metadata

        Returns:
        --------
        bool
            True if successful
        """
        if not self.enabled:
            logger.debug("CDN disabled, skipping upload")
            return False

        file_path = Path(file_path)
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False

        file_size_mb = file_path.stat().st_size / (1024 * 1024)

        # Select appropriate CDN based on file size
        endpoint = self._select_endpoint(file_size_mb)

        logger.info(
            f"Uploading to CDN ({endpoint.name}): {cdn_path} "
            f"({file_size_mb:.2f} MB)"
        )

        try:
            # In production, this would use actual CDN SDK
            # For now, simulate upload
            self._simulate_upload(file_path, cdn_path, endpoint)

            self.upload_count += 1
            self.total_bytes_uploaded += file_path.stat().st_size

            logger.info(f"CDN upload successful: {cdn_path}")
            return True

        except Exception as e:
            logger.error(f"CDN upload failed: {e}")

            # Try fallback CDN
            if self.fallback_cdn and self.fallback_cdn != endpoint.name:
                logger.info(f"Trying fallback CDN: {self.fallback_cdn}")
                return self._upload_to_fallback(file_path, cdn_path)

            return False

    def _select_endpoint(self, file_size_mb: float) -> CDNEndpoint:
        """
        Select optimal CDN endpoint.

        Graham's Selection Algorithm:
        ----------------------------
        1. Filter by file size capacity
        2. Sort by priority
        3. Select first available

        Parameters:
        -----------
        file_size_mb : float
            File size in MB

        Returns:
        --------
        CDNEndpoint
            Selected endpoint
        """
        # Get primary endpoint
        if self.primary_cdn in self.endpoints:
            endpoint = self.endpoints[self.primary_cdn]
            if file_size_mb <= endpoint.max_file_size_mb:
                return endpoint

        # Find suitable endpoint
        suitable = [
            ep for ep in self.endpoints.values()
            if file_size_mb <= ep.max_file_size_mb
        ]

        if not suitable:
            logger.warning("No CDN endpoint can handle file size, using local")
            return self.endpoints['local']

        # Sort by priority and return best
        suitable.sort(key=lambda x: x.priority)
        return suitable[0]

    def _simulate_upload(self, file_path: Path, cdn_path: str, endpoint: CDNEndpoint):
        """Simulate CDN upload (replace with actual SDK in production)."""
        # In production, use actual CDN SDK:
        # - Cloudflare: cloudflare SDK
        # - AWS CloudFront: boto3
        # - Azure CDN: azure-storage-blob
        pass

    def _upload_to_fallback(self, file_path: Path, cdn_path: str) -> bool:
        """Upload to fallback CDN."""
        if not self.fallback_cdn or self.fallback_cdn not in self.endpoints:
            return False

        endpoint = self.endpoints[self.fallback_cdn]

        try:
            self._simulate_upload(file_path, cdn_path, endpoint)
            logger.info(f"Fallback CDN upload successful: {cdn_path}")
            return True
        except Exception as e:
            logger.error(f"Fallback CDN upload failed: {e}")
            return False

    def get_url(
        self,
        cdn_path: str,
        signed: bool = False,
        expires_in: int = 3600
    ) -> str:
        """
        Get CDN URL for file.

        Parameters:
        -----------
        cdn_path : str
            CDN file path
        signed : bool
            Generate signed URL
        expires_in : int
            Expiration time in seconds (for signed URLs)

        Returns:
        --------
        str
            CDN URL
        """
        if not self.enabled:
            return f"/local/{cdn_path}"

        endpoint = self.endpoints.get(self.primary_cdn, self.endpoints['local'])
        base_url = endpoint.base_url.rstrip('/')

        if signed:
            # Generate signed URL (simplified)
            expires = int((datetime.now() + timedelta(seconds=expires_in)).timestamp())
            signature = self._generate_signature(cdn_path, expires)
            return f"{base_url}/{cdn_path}?expires={expires}&signature={signature}"

        return f"{base_url}/{cdn_path}"

    def _generate_signature(self, path: str, expires: int) -> str:
        """Generate URL signature for signed URLs."""
        # In production, use actual signing key
        secret_key = "change-this-in-production"
        data = f"{path}{expires}{secret_key}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def invalidate_cache(self, paths: List[str]) -> bool:
        """
        Invalidate CDN cache for specified paths.

        Cache Invalidation (Knuth):
        ---------------------------
        "There are only two hard things in Computer Science:
        cache invalidation and naming things."

        Parameters:
        -----------
        paths : list
            List of paths to invalidate

        Returns:
        --------
        bool
            True if successful
        """
        if not self.enabled:
            return False

        logger.info(f"Invalidating CDN cache for {len(paths)} paths")

        try:
            # In production, use CDN API for cache invalidation
            # Cloudflare: purge by URL
            # CloudFront: create invalidation
            for path in paths:
                logger.debug(f"Invalidating: {path}")

            return True

        except Exception as e:
            logger.error(f"Cache invalidation failed: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get CDN usage statistics."""
        total_mb_uploaded = self.total_bytes_uploaded / (1024 * 1024)

        return {
            'enabled': self.enabled,
            'primary_cdn': self.primary_cdn,
            'fallback_cdn': self.fallback_cdn,
            'upload_count': self.upload_count,
            'total_mb_uploaded': total_mb_uploaded,
            'avg_mb_per_upload': total_mb_uploaded / self.upload_count if self.upload_count > 0 else 0
        }

    def estimate_bandwidth_savings(
        self,
        requests_per_day: int,
        avg_file_size_mb: float,
        origin_bandwidth_cost_per_gb: float = 0.09,
        cdn_bandwidth_cost_per_gb: float = 0.01
    ) -> Dict[str, float]:
        """
        Estimate cost savings from CDN usage.

        Cost Analysis (Graham):
        ----------------------
        Savings = (Origin_Cost - CDN_Cost) * Traffic
        ROI = Savings / CDN_Setup_Cost

        Parameters:
        -----------
        requests_per_day : int
            Daily requests
        avg_file_size_mb : float
            Average file size
        origin_bandwidth_cost_per_gb : float
            Cost per GB from origin
        cdn_bandwidth_cost_per_gb : float
            Cost per GB from CDN

        Returns:
        --------
        dict
            Cost analysis
        """
        # Calculate monthly traffic
        daily_traffic_gb = (requests_per_day * avg_file_size_mb) / 1024
        monthly_traffic_gb = daily_traffic_gb * 30

        # Calculate costs
        origin_cost = monthly_traffic_gb * origin_bandwidth_cost_per_gb
        cdn_cost = monthly_traffic_gb * cdn_bandwidth_cost_per_gb

        # Savings
        monthly_savings = origin_cost - cdn_cost
        annual_savings = monthly_savings * 12

        return {
            'monthly_traffic_gb': monthly_traffic_gb,
            'origin_cost_monthly': origin_cost,
            'cdn_cost_monthly': cdn_cost,
            'monthly_savings': monthly_savings,
            'annual_savings': annual_savings,
            'savings_percentage': (monthly_savings / origin_cost * 100) if origin_cost > 0 else 0
        }

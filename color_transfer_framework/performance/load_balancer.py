"""
Load Balancer Configuration
============================

Load balancing strategies and configuration for distributed deployment.

Mathematical Foundation (Knuth):
- Optimal load distribution: minimize max(load_i) for all i
- Round-robin: O(1) selection, uniform distribution
- Weighted round-robin: accounts for heterogeneous servers
- Least connections: O(log n) with heap, dynamic optimization

Practical Implementation (Graham):
- Health checking and failover
- Session affinity strategies
- Geographic routing
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import random
from collections import deque
import time

logger = logging.getLogger(__name__)


class LoadBalancingStrategy(Enum):
    """Load balancing algorithms."""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    RANDOM = "random"
    IP_HASH = "ip_hash"


@dataclass
class Server:
    """
    Backend server configuration.

    Capacity Analysis (Knuth):
    --------------------------
    - capacity: max concurrent connections
    - weight: relative capacity (for weighted algorithms)
    - current_connections: active connections
    - utilization = current / capacity
    """
    host: str
    port: int
    weight: int = 1
    capacity: int = 100
    current_connections: int = 0
    healthy: bool = True
    region: str = "default"

    @property
    def utilization(self) -> float:
        """Current utilization ratio."""
        return self.current_connections / self.capacity if self.capacity > 0 else 1.0

    @property
    def available_capacity(self) -> int:
        """Available connection slots."""
        return max(0, self.capacity - self.current_connections)


class LoadBalancerConfig:
    """
    Load balancer configuration and routing logic.

    Complexity Analysis:
    -------------------
    - Round Robin: O(1) selection
    - Weighted RR: O(1) amortized
    - Least Connections: O(n) naive, O(log n) with heap
    - Random: O(1) selection
    - IP Hash: O(1) hash lookup

    Example:
        >>> lb = LoadBalancerConfig(strategy='least_connections')
        >>> lb.add_server('192.168.1.10', 8000, weight=2)
        >>> lb.add_server('192.168.1.11', 8000, weight=1)
        >>> server = lb.select_server(client_ip='10.0.0.1')
    """

    def __init__(
        self,
        strategy: str = 'round_robin',
        health_check_interval: int = 30,
        enable_sticky_sessions: bool = False
    ):
        """
        Initialize load balancer.

        Parameters:
        -----------
        strategy : str
            Load balancing strategy
        health_check_interval : int
            Health check interval in seconds
        enable_sticky_sessions : bool
            Enable session affinity
        """
        self.strategy = LoadBalancingStrategy(strategy)
        self.health_check_interval = health_check_interval
        self.enable_sticky_sessions = enable_sticky_sessions

        # Server pool
        self.servers: List[Server] = []

        # Round-robin state
        self.rr_index = 0

        # Weighted round-robin state
        self.wrr_queue: deque = deque()

        # Session affinity map
        self.session_map: Dict[str, Server] = {}

        # Statistics
        self.total_requests = 0
        self.request_counts: Dict[str, int] = {}

        logger.info(f"Load balancer initialized: strategy={strategy}")

    def add_server(
        self,
        host: str,
        port: int,
        weight: int = 1,
        capacity: int = 100,
        region: str = "default"
    ):
        """
        Add backend server.

        Parameters:
        -----------
        host : str
            Server hostname/IP
        port : int
            Server port
        weight : int
            Server weight (for weighted strategies)
        capacity : int
            Max concurrent connections
        region : str
            Geographic region
        """
        server = Server(
            host=host,
            port=port,
            weight=weight,
            capacity=capacity,
            region=region
        )

        self.servers.append(server)
        self.request_counts[f"{host}:{port}"] = 0

        # Update weighted round-robin queue
        if self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            self._rebuild_wrr_queue()

        logger.info(f"Added server: {host}:{port} (weight={weight}, capacity={capacity})")

    def select_server(
        self,
        client_ip: Optional[str] = None
    ) -> Optional[Server]:
        """
        Select backend server using configured strategy.

        Selection Algorithm Analysis (Knuth):
        -------------------------------------
        Round Robin:
          - Time: O(1)
          - Distribution: Uniform
          - Properties: Simple, fair, no state required

        Weighted Round Robin:
          - Time: O(1) amortized
          - Distribution: Proportional to weights
          - Properties: Accounts for heterogeneous capacity

        Least Connections:
          - Time: O(n) this implementation, O(log n) with heap
          - Distribution: Dynamic based on load
          - Properties: Optimal for variable request duration

        Parameters:
        -----------
        client_ip : str, optional
            Client IP address (for sticky sessions, IP hash)

        Returns:
        --------
        Server or None
            Selected server
        """
        # Check sticky sessions
        if self.enable_sticky_sessions and client_ip in self.session_map:
            server = self.session_map[client_ip]
            if server.healthy and server.available_capacity > 0:
                return server

        # Get healthy servers
        healthy_servers = [s for s in self.servers if s.healthy]

        if not healthy_servers:
            logger.error("No healthy servers available")
            return None

        # Select based on strategy
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            server = self._select_round_robin(healthy_servers)

        elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            server = self._select_weighted_round_robin(healthy_servers)

        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            server = self._select_least_connections(healthy_servers)

        elif self.strategy == LoadBalancingStrategy.RANDOM:
            server = random.choice(healthy_servers)

        elif self.strategy == LoadBalancingStrategy.IP_HASH:
            server = self._select_ip_hash(healthy_servers, client_ip)

        else:
            server = healthy_servers[0]

        # Update session map
        if self.enable_sticky_sessions and client_ip:
            self.session_map[client_ip] = server

        # Track statistics
        self.total_requests += 1
        server_key = f"{server.host}:{server.port}"
        self.request_counts[server_key] = self.request_counts.get(server_key, 0) + 1

        return server

    def _select_round_robin(self, servers: List[Server]) -> Server:
        """
        Round-robin selection.

        Knuth's Analysis:
        ----------------
        Perfect load distribution for identical request durations.
        For n servers: server i receives ⌊requests/n⌋ or ⌈requests/n⌉ requests.
        """
        server = servers[self.rr_index % len(servers)]
        self.rr_index += 1
        return server

    def _select_weighted_round_robin(self, servers: List[Server]) -> Server:
        """
        Weighted round-robin selection.

        Graham's Implementation:
        -----------------------
        Build queue with repetition proportional to weights.
        Example: weights=[2,1] → queue=[s1, s1, s2]
        """
        if not self.wrr_queue:
            self._rebuild_wrr_queue()

        if self.wrr_queue:
            server = self.wrr_queue.popleft()
            self.wrr_queue.append(server)  # Rotate
            return server

        # Fallback to round-robin
        return self._select_round_robin(servers)

    def _rebuild_wrr_queue(self):
        """Rebuild weighted round-robin queue."""
        self.wrr_queue = deque()

        for server in self.servers:
            if server.healthy:
                # Add server weight times to queue
                for _ in range(server.weight):
                    self.wrr_queue.append(server)

    def _select_least_connections(self, servers: List[Server]) -> Server:
        """
        Least connections selection.

        Knuth's Optimality:
        ------------------
        Minimizes max load: argmin_i(connections_i)
        Optimal for variable request durations.

        Time: O(n) - linear scan to find minimum
        Can be improved to O(log n) with min-heap.
        """
        # Find server with fewest connections and available capacity
        best_server = min(
            servers,
            key=lambda s: (s.current_connections, -s.available_capacity)
        )

        return best_server

    def _select_ip_hash(
        self,
        servers: List[Server],
        client_ip: Optional[str]
    ) -> Server:
        """
        IP hash-based selection.

        Consistent hashing ensures same client → same server.
        """
        if not client_ip:
            return self._select_round_robin(servers)

        # Simple hash-based selection
        hash_value = hash(client_ip)
        index = hash_value % len(servers)

        return servers[index]

    def mark_connection(self, server: Server, delta: int = 1):
        """
        Update server connection count.

        Parameters:
        -----------
        server : Server
            Target server
        delta : int
            Connection count change (+1 for new, -1 for closed)
        """
        server.current_connections = max(0, server.current_connections + delta)

    def health_check(self) -> Dict[str, bool]:
        """
        Perform health check on all servers.

        Returns:
        --------
        dict
            Server health status
        """
        health_status = {}

        for server in self.servers:
            try:
                # In production, perform actual health check:
                # - HTTP GET /health
                # - TCP connect test
                # - Ping test

                # For now, simulate
                # server.healthy = self._check_server_health(server)

                health_status[f"{server.host}:{server.port}"] = server.healthy

            except Exception as e:
                logger.error(f"Health check failed for {server.host}:{server.port}: {e}")
                server.healthy = False
                health_status[f"{server.host}:{server.port}"] = False

        return health_status

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get load balancer statistics.

        Statistical Analysis (Knuth):
        -----------------------------
        - Distribution uniformity: coefficient of variation
        - Utilization: sum(connections)/sum(capacity)
        - Imbalance ratio: max(load)/avg(load)
        """
        if not self.servers:
            return {}

        total_capacity = sum(s.capacity for s in self.servers)
        total_connections = sum(s.current_connections for s in self.servers)
        avg_utilization = total_connections / total_capacity if total_capacity > 0 else 0

        # Load distribution analysis
        request_counts = list(self.request_counts.values())
        if request_counts:
            max_requests = max(request_counts)
            min_requests = min(request_counts)
            avg_requests = sum(request_counts) / len(request_counts)

            # Coefficient of variation (measure of uniformity)
            import numpy as np
            cv = np.std(request_counts) / avg_requests if avg_requests > 0 else 0
        else:
            max_requests = min_requests = avg_requests = cv = 0

        return {
            'strategy': self.strategy.value,
            'total_servers': len(self.servers),
            'healthy_servers': sum(1 for s in self.servers if s.healthy),
            'total_requests': self.total_requests,
            'total_capacity': total_capacity,
            'total_connections': total_connections,
            'avg_utilization': avg_utilization,
            'max_requests_per_server': max_requests,
            'min_requests_per_server': min_requests,
            'avg_requests_per_server': avg_requests,
            'load_distribution_cv': cv,  # Lower is more uniform
            'request_distribution': self.request_counts
        }

    def analyze_load_distribution(self) -> Dict[str, float]:
        """
        Analyze load distribution quality.

        Knuth's Metrics:
        ---------------
        - Uniformity: How evenly distributed
        - Fairness: min/max ratio
        - Efficiency: utilization without overload

        Returns:
        --------
        dict
            Distribution quality metrics
        """
        stats = self.get_statistics()

        max_req = stats['max_requests_per_server']
        min_req = stats['min_requests_per_server']
        avg_req = stats['avg_requests_per_server']

        # Fairness index (0 = perfectly unfair, 1 = perfectly fair)
        fairness = min_req / max_req if max_req > 0 else 1.0

        # Imbalance ratio (1 = perfect balance, higher = more imbalanced)
        imbalance = max_req / avg_req if avg_req > 0 else 1.0

        return {
            'fairness_index': fairness,
            'imbalance_ratio': imbalance,
            'distribution_cv': stats['load_distribution_cv'],
            'quality_score': fairness / imbalance if imbalance > 0 else 0
        }

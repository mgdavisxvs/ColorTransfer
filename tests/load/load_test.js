// k6 Load Testing Script - Knuth's Performance Verification
//
// Tests system behavior with mathematical precision:
// - Throughput measurement (req/s)
// - Latency distribution (p50, p95, p99)
// - Error rate analysis
// - Resource utilization
//
// Mathematical Models (Knuth):
// - Little's Law: L = λW
// - Response time distribution analysis
// - Throughput vs concurrency curves
//
// Run: k6 run load_test.js

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { htmlReport } from "https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js";

// Custom metrics (Graham's observability)
const transferRate = new Rate('transfer_success_rate');
const transferDuration = new Trend('transfer_duration');
const transferCount = new Counter('transfer_count');

// Test images (base64 encoded)
const smallImageB64 = generateTestImageBase64(100, 100);

function generateTestImageBase64(width, height) {
    // Generate a simple test pattern
    // In production, use actual base64 encoded PNG
    return 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';
}

// Load test configuration (Knuth's test scenarios)
export const options = {
    // Scenario 1: Smoke Test
    scenarios: {
        smoke_test: {
            executor: 'constant-vus',
            vus: 1,
            duration: '1m',
            tags: { test_type: 'smoke' },
        },

        // Scenario 2: Load Test (Normal Operation)
        load_test: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '2m', target: 50 },   // Ramp up
                { duration: '5m', target: 50 },   // Steady state
                { duration: '2m', target: 100 },  // Increased load
                { duration: '5m', target: 100 },  // Steady state
                { duration: '2m', target: 0 },    // Ramp down
            ],
            gracefulRampDown: '30s',
            tags: { test_type: 'load' },
            startTime: '1m', // Start after smoke test
        },

        // Scenario 3: Stress Test (Find Limits)
        stress_test: {
            executor: 'ramping-arrival-rate',
            startRate: 10,
            timeUnit: '1s',
            preAllocatedVUs: 100,
            maxVUs: 500,
            stages: [
                { duration: '2m', target: 50 },   // Warm up
                { duration: '5m', target: 100 },  // Normal load
                { duration: '5m', target: 200 },  // High load
                { duration: '5m', target: 300 },  // Very high load
                { duration: '2m', target: 0 },    // Cool down
            ],
            tags: { test_type: 'stress' },
            startTime: '18m', // Start after load test
        },

        // Scenario 4: Spike Test (Sudden Load)
        spike_test: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '10s', target: 500 },  // Spike
                { duration: '1m', target: 500 },   // Sustain
                { duration: '10s', target: 0 },    // Drop
            ],
            tags: { test_type: 'spike' },
            startTime: '37m', // Start after stress test
        },
    },

    // Thresholds (Knuth's acceptance criteria)
    thresholds: {
        // HTTP failures should be < 1%
        'http_req_failed': ['rate<0.01'],

        // 95% of requests should be < 1000ms
        'http_req_duration': ['p(95)<1000'],

        // Transfer success rate > 95%
        'transfer_success_rate': ['rate>0.95'],

        // Transfer duration p95 < 2000ms
        'transfer_duration': ['p(95)<2000'],

        // Error rate < 5%
        'checks': ['rate>0.95'],
    },
};

// Base URL
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
    // Knuth's weighted task distribution
    const rand = Math.random();

    if (rand < 0.2) {
        // 20%: View home page
        testHomePage();
    } else if (rand < 0.4) {
        // 20%: View algorithms
        testAlgorithms();
    } else if (rand < 0.7) {
        // 30%: Perform transfer
        testTransfer();
    } else if (rand < 0.85) {
        // 15%: Check health
        testHealth();
    } else {
        // 15%: Check metrics
        testMetrics();
    }

    // Think time: 1-5 seconds (Graham's realistic behavior)
    sleep(Math.random() * 4 + 1);
}

function testHomePage() {
    const res = http.get(`${BASE_URL}/`);

    check(res, {
        'home page status is 200': (r) => r.status === 200,
        'home page has title': (r) => r.body.includes('Color Transfer'),
    });
}

function testAlgorithms() {
    const res = http.get(`${BASE_URL}/api/v1/algorithms`);

    check(res, {
        'algorithms status is 200': (r) => r.status === 200,
        'algorithms response is JSON': (r) => r.headers['Content-Type'].includes('application/json'),
        'algorithms list not empty': (r) => JSON.parse(r.body).algorithms.length > 0,
    });
}

function testTransfer() {
    const algorithms = ['reinhard_lab', 'reinhard_lch', 'rgb_direct', 'histogram_match'];
    const algorithm = algorithms[Math.floor(Math.random() * algorithms.length)];

    const payload = JSON.stringify({
        source_image: smallImageB64,
        target_image: smallImageB64,
        config: {
            algorithm: algorithm,
            blend_factor: Math.random() * 0.5 + 0.5,
            clip_output: true,
            preserve_luminance: false,
            use_gpu: false,
        },
    });

    const params = {
        headers: {
            'Content-Type': 'application/json',
        },
        timeout: '30s',
        tags: { algorithm: algorithm },
    };

    const startTime = Date.now();
    const res = http.post(`${BASE_URL}/api/v1/transfer`, payload, params);
    const duration = Date.now() - startTime;

    const success = check(res, {
        'transfer status is 200 or 429': (r) => r.status === 200 || r.status === 429,
        'transfer has result_image': (r) => r.status === 200 ? JSON.parse(r.body).result_image !== undefined : true,
        'transfer has metrics': (r) => r.status === 200 ? JSON.parse(r.body).metrics !== undefined : true,
    });

    // Record metrics
    if (res.status === 200) {
        transferRate.add(1);
        transferDuration.add(duration);
        transferCount.add(1);
    } else {
        transferRate.add(0);
    }
}

function testHealth() {
    const res = http.get(`${BASE_URL}/health/live`);

    check(res, {
        'health status is 200': (r) => r.status === 200,
        'health response is JSON': (r) => r.headers['Content-Type'].includes('application/json'),
    });
}

function testMetrics() {
    const res = http.get(`${BASE_URL}/metrics`);

    check(res, {
        'metrics status is 200': (r) => r.status === 200,
        'metrics response is JSON': (r) => r.headers['Content-Type'].includes('application/json'),
    });
}

// Generate HTML report at end
export function handleSummary(data) {
    return {
        "summary.html": htmlReport(data),
        "summary.json": JSON.stringify(data),
    };
}

/*
Knuth's Performance Analysis Guide:
===================================

Running the tests:

1. Smoke Test Only:
   k6 run --env BASE_URL=http://localhost:8000 load_test.js --include-scenario-in-tags smoke_test

2. Load Test Only:
   k6 run --env BASE_URL=http://localhost:8000 load_test.js --include-scenario-in-tags load_test

3. All Tests:
   k6 run --env BASE_URL=http://localhost:8000 load_test.js

4. Custom Test:
   k6 run --env BASE_URL=http://localhost:8000 --vus 100 --duration 5m load_test.js

Interpreting Results:

Throughput:
- http_reqs: Total requests/second
- Target: > 100 req/s for normal load
- Target: > 500 req/s for API endpoints

Latency (p95):
- API endpoints: < 100ms
- Transfer operations: < 1000ms
- Health checks: < 10ms

Error Rate:
- http_req_failed: < 1%
- checks: > 95% passing

Resource Utilization:
- Monitor CPU: Should stay < 80%
- Monitor Memory: Should not grow unbounded
- Monitor Network: Check bandwidth usage

Breaking Points:
- Throughput ceiling: When latency spikes
- Error threshold: When error rate > 5%
- Resource exhaustion: CPU/Memory maxed

Mathematical Analysis:

Little's Law: L = λW
- If throughput λ = 100 req/s
- And latency W = 0.1s
- Then concurrent requests L = 10

Response Time Distribution:
- p50 (median): Typical performance
- p95: Near-worst case (1 in 20)
- p99: Worst case (1 in 100)
- max: Absolute worst (outlier)

Amdahl's Law:
- Speedup = 1 / ((1-P) + P/N)
- If 90% parallelizable, 4 workers:
- Speedup = 1 / (0.1 + 0.9/4) = 3.08x

Graham's Recommendations:

1. Start with smoke test (1 user)
2. Run load test (100 users)
3. Analyze results, optimize
4. Run stress test (500 users)
5. Find breaking point
6. Document and set SLAs

Performance Baselines:
- Normal load (50-100 users): p95 < 500ms
- High load (100-200 users): p95 < 1000ms
- Stress load (200-500 users): p95 < 2000ms
- Spike load (500+ users): Graceful degradation

Optimization Targets:
- Reduce p95 latency by 20%
- Increase throughput by 50%
- Decrease error rate to < 0.1%
- Support 2x more concurrent users
*/

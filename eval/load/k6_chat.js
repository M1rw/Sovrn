import http from 'k6/http';
import { check, sleep } from 'k6';

const baseUrl = __ENV.SOVRN_BASE_URL || 'http://localhost:8000';
const vus = Number(__ENV.K6_VUS || 10);
const duration = __ENV.K6_DURATION || '1m';

export const options = {
  vus,
  duration,
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<2500', 'p(99)<5000'],
    checks: ['rate>0.99'],
  },
};

function buildPayload() {
  return JSON.stringify({
    messages: [
      {
        role: 'system',
        content: 'You are a concise assistant for website planning.',
      },
      {
        role: 'user',
        content: 'Create a short plan for a modern SaaS landing page with pricing and FAQ.',
      },
    ],
    temperature: 0.4,
    max_tokens: 256,
  });
}

export default function () {
  const response = http.post(`${baseUrl}/api/v1/ai/chat`, buildPayload(), {
    headers: {
      'Content-Type': 'application/json',
      'X-Correlation-ID': `k6-chat-${__VU}-${__ITER}`,
      'X-Client-Session-ID': `k6-vu-${__VU}`,
    },
    tags: {
      route: 'ai_chat',
      scenario: 'chat_interactive',
    },
  });

  check(response, {
    'chat status is 200': (r) => r.status === 200,
    'chat returns body': (r) => (r.body || '').length > 0,
    'chat includes request id': (r) => !!r.headers['X-Request-Id'] || !!r.headers['X-Request-ID'],
  });

  sleep(0.2);
}

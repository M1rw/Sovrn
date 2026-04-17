import http from 'k6/http';
import { check, sleep } from 'k6';

const baseUrl = __ENV.SOVRN_BASE_URL || 'http://localhost:8000';
const token = __ENV.SOVRN_TOKEN || '';
const locale = __ENV.SOVRN_LOCALE || 'en';
const vus = Number(__ENV.K6_VUS || 2);
const duration = __ENV.K6_DURATION || '2m';

if (!token) {
  throw new Error('SOVRN_TOKEN is required for generation flow load test');
}

export const options = {
  vus,
  duration,
  thresholds: {
    http_req_failed: ['rate<0.03'],
    http_req_duration: ['p(95)<7000'],
    checks: ['rate>0.95'],
  },
};

function authHeaders(tag) {
  return {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
    'X-Correlation-ID': `k6-generation-${tag}-${__VU}-${__ITER}`,
    'X-Client-Session-ID': `k6-vu-${__VU}`,
  };
}

function createProject() {
  const payload = JSON.stringify({
    name: `Load Test Project ${__VU}-${__ITER}`,
    description: 'Synthetic load test project',
    locale,
  });

  const response = http.post(`${baseUrl}/api/v1/projects`, payload, {
    headers: authHeaders('create-project'),
    tags: { route: 'projects_create', scenario: 'generation_flow' },
  });

  check(response, {
    'project create status is 201': (r) => r.status === 201,
  });

  if (response.status !== 201) {
    return null;
  }

  return response.json('id');
}

function queueGeneration(projectId) {
  const payload = JSON.stringify({
    brief: 'Generate a modern SaaS website with hero, features, pricing, and contact sections.',
    locale,
    settings: { style: 'modern' },
  });

  const response = http.post(`${baseUrl}/api/v1/projects/${projectId}/generate`, payload, {
    headers: authHeaders('queue-job'),
    tags: { route: 'projects_generate', scenario: 'generation_flow' },
  });

  check(response, {
    'generation queue status is 201': (r) => r.status === 201,
  });

  if (response.status !== 201) {
    return null;
  }

  return response.json('id');
}

function pollJob(jobId) {
  const maxPolls = Number(__ENV.K6_JOB_MAX_POLLS || 20);
  const pollIntervalMs = Number(__ENV.K6_JOB_POLL_INTERVAL_MS || 1500);

  for (let i = 0; i < maxPolls; i += 1) {
    const response = http.get(`${baseUrl}/api/v1/jobs/${jobId}`, {
      headers: authHeaders('poll-job'),
      tags: { route: 'jobs_get', scenario: 'generation_flow' },
    });

    check(response, {
      'job status endpoint is 200': (r) => r.status === 200,
    });

    if (response.status !== 200) {
      return false;
    }

    const status = response.json('status');
    if (status === 'completed' || status === 'failed' || status === 'cancelled') {
      return true;
    }

    sleep(pollIntervalMs / 1000);
  }

  return false;
}

export default function () {
  const projectId = createProject();
  if (!projectId) {
    return;
  }

  const jobId = queueGeneration(projectId);
  if (!jobId) {
    return;
  }

  const polled = pollJob(jobId);
  check({ polled }, {
    'job reached terminal state within polling budget': (r) => r.polled === true,
  });

  sleep(0.2);
}

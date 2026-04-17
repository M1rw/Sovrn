import json
import os
import re
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

jobs = {}


class MockHandler(BaseHTTPRequestHandler):
    server_version = 'SovrnMock/1.0'

    def log_message(self, format, *args):
        return

    def _send(self, status_code, payload):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Request-Id', str(uuid.uuid4()))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get('Content-Length', '0'))
        if length:
            _ = self.rfile.read(length)

        if self.path == '/api/v1/ai/chat':
            self._send(
                200,
                {
                    'content': 'Mock chat response',
                    'provider': 'mock',
                    'model': 'mock-1',
                    'success': True,
                    'latency_ms': 5,
                },
            )
            return

        if self.path == '/api/v1/projects':
            project_id = str(uuid.uuid4())
            self._send(201, {'id': project_id, 'status': 'created'})
            return

        match_generate = re.match(r'^/api/v1/projects/([^/]+)/generate$', self.path)
        if match_generate:
            job_id = str(uuid.uuid4())
            jobs[job_id] = 0
            self._send(201, {'id': job_id, 'status': 'queued'})
            return

        self._send(404, {'detail': 'Not found'})

    def do_GET(self):
        if self.path in ('/health', '/ready'):
            self._send(200, {'status': 'ok'})
            return

        match_job = re.match(r'^/api/v1/jobs/([^/]+)$', self.path)
        if match_job:
            job_id = match_job.group(1)
            if job_id not in jobs:
                self._send(404, {'detail': 'Job not found'})
                return

            jobs[job_id] += 1
            status = 'running' if jobs[job_id] < 2 else 'completed'
            self._send(200, {'id': job_id, 'status': status})
            return

        self._send(404, {'detail': 'Not found'})


def main():
    host = os.environ.get('MOCK_HOST', '127.0.0.1')
    port = int(os.environ.get('MOCK_PORT', '8000'))
    server = ThreadingHTTPServer((host, port), MockHandler)
    print(f'Mock API listening on http://{host}:{port}')
    server.serve_forever()


if __name__ == '__main__':
    main()

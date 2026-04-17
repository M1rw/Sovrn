import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse

jobs = {}
project_generations = {}
preview_sessions = {}


def _artifact_endpoint(project_id: str, generation_id: str, entrypoint: str) -> str:
    return (
        f"/api/v1/projects/{project_id}/preview-artifact"
        f"?generation_id={generation_id}&entrypoint={quote(entrypoint, safe='/')}"
    )


def _ensure_generation(project_id: str) -> str:
    generation_id = project_generations.get(project_id)
    if generation_id is None:
        generation_id = str(uuid.uuid4())
        project_generations[project_id] = generation_id
    return generation_id


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

    def _send_sse(self, status_code, body_text: str):
        body = body_text.encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Request-Id', str(uuid.uuid4()))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self):
        length = int(self.headers.get('Content-Length', '0'))
        if length <= 0:
            return {}

        payload = self.rfile.read(length).decode('utf-8')
        if not payload.strip():
            return {}

        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return {}

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_json_body()

        if path == '/api/v1/ai/chat':
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

        if path == '/api/v1/projects':
            project_id = str(uuid.uuid4())
            generation_id = _ensure_generation(project_id)
            self._send(
                201,
                {
                    'id': project_id,
                    'status': 'created',
                    'generations': [
                        {
                            'id': generation_id,
                            'version': 1,
                        }
                    ],
                },
            )
            return

        match_generate = re.match(r'^/api/v1/projects/([^/]+)/generate$', path)
        if match_generate:
            job_id = str(uuid.uuid4())
            jobs[job_id] = 0
            _ensure_generation(match_generate.group(1))
            self._send(201, {'id': job_id, 'status': 'queued'})
            return

        match_preview_session = re.match(r'^/api/v1/projects/([^/]+)/preview-session$', path)
        if match_preview_session:
            project_id = match_preview_session.group(1)
            generation_id = str(body.get('generation_id') or _ensure_generation(project_id))
            entrypoint = str(body.get('entrypoint') or 'index.html').strip() or 'index.html'
            ttl_seconds = int(body.get('ttl_seconds') or 600)
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=max(ttl_seconds, 1))
            token = f"preview-{uuid.uuid4()}"
            preview_sessions[token] = {
                'project_id': project_id,
                'generation_id': generation_id,
                'entrypoint': entrypoint,
                'expires_at': expires_at,
            }

            self._send(
                200,
                {
                    'token': token,
                    'token_type': 'preview_session',
                    'expires_at': expires_at.isoformat(),
                    'project_id': project_id,
                    'generation_id': generation_id,
                    'entrypoint': entrypoint,
                    'artifact_endpoint': _artifact_endpoint(project_id, generation_id, entrypoint),
                },
            )
            return

        match_verify_session = re.match(r'^/api/v1/projects/([^/]+)/preview-session/verify$', path)
        if match_verify_session:
            project_id = match_verify_session.group(1)
            token = str(body.get('token') or '')
            if not token:
                self._send(401, {'detail': 'Invalid preview session token'})
                return

            session_data = preview_sessions.get(token)
            if session_data is None:
                self._send(401, {'detail': 'Invalid preview session token'})
                return

            if session_data['project_id'] != project_id:
                self._send(403, {'detail': 'Preview session token is not valid for project'})
                return

            requested_generation_id = str(body.get('generation_id') or session_data['generation_id'])
            requested_entrypoint = str(body.get('entrypoint') or session_data['entrypoint']).strip() or session_data['entrypoint']

            if requested_generation_id != session_data['generation_id']:
                self._send(403, {'detail': 'Preview session token is not valid for generation'})
                return

            if requested_entrypoint != session_data['entrypoint']:
                self._send(403, {'detail': 'Preview session token is not valid for entrypoint'})
                return

            self._send(
                200,
                {
                    'valid': True,
                    'token_type': 'preview_session',
                    'project_id': project_id,
                    'generation_id': requested_generation_id,
                    'entrypoint': requested_entrypoint,
                    'expires_at': session_data['expires_at'].isoformat(),
                    'artifact_endpoint': _artifact_endpoint(project_id, requested_generation_id, requested_entrypoint),
                },
            )
            return

        self._send(404, {'detail': 'Not found'})

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path in ('/health', '/ready'):
            self._send(200, {'status': 'ok'})
            return

        match_project = re.match(r'^/api/v1/projects/([^/]+)$', path)
        if match_project:
            project_id = match_project.group(1)
            generation_id = _ensure_generation(project_id)
            self._send(
                200,
                {
                    'id': project_id,
                    'status': 'ready',
                    'generations': [
                        {
                            'id': generation_id,
                            'version': 1,
                        }
                    ],
                },
            )
            return

        match_preview_artifact = re.match(r'^/api/v1/projects/([^/]+)/preview-artifact$', path)
        if match_preview_artifact:
            project_id = match_preview_artifact.group(1)
            generation_id = str(query.get('generation_id', [_ensure_generation(project_id)])[0])
            entrypoint = str(query.get('entrypoint', ['index.html'])[0]).strip() or 'index.html'
            preview_html = f"<html><body><h1>Mock Preview</h1><p>project={project_id}</p></body></html>"
            files = [
                {
                    'path': entrypoint,
                    'content': preview_html,
                    'language': 'html',
                    'size_bytes': len(preview_html.encode('utf-8')),
                }
            ]
            self._send(
                200,
                {
                    'project_id': project_id,
                    'generation_id': generation_id,
                    'generation_version': 1,
                    'entrypoint': entrypoint,
                    'preview_html': preview_html,
                    'files': files,
                    'source': 'site_generation',
                },
            )
            return

        match_preview_events = re.match(r'^/api/v1/projects/([^/]+)/preview-events$', path)
        if match_preview_events:
            project_id = match_preview_events.group(1)
            generation_id = str(query.get('generation_id', [_ensure_generation(project_id)])[0])
            entrypoint = str(query.get('entrypoint', ['index.html'])[0]).strip() or 'index.html'

            preview_token = str(query.get('preview_token', [''])[0])
            if preview_token:
                session_data = preview_sessions.get(preview_token)
                if session_data is None:
                    self._send(401, {'detail': 'Invalid preview session token'})
                    return
                if session_data['project_id'] != project_id:
                    self._send(403, {'detail': 'Preview session token is not valid for project'})
                    return

            preview_html = f"<html><body><h1>Mock Stream Update</h1><p>project={project_id}</p></body></html>"
            payload = {
                'project_id': project_id,
                'generation_id': generation_id,
                'generation_version': 1,
                'entrypoint': entrypoint,
                'preview_html': preview_html,
                'files': [
                    {
                        'path': entrypoint,
                        'content': preview_html,
                        'language': 'html',
                        'size_bytes': len(preview_html.encode('utf-8')),
                    }
                ],
                'artifact_endpoint': _artifact_endpoint(project_id, generation_id, entrypoint),
            }
            heartbeat = {
                'project_id': project_id,
                'generation_id': generation_id,
                'generation_version': 1,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }

            body = (
                "retry: 2000\n\n"
                f"event: preview.updated\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"
                f"event: heartbeat\ndata: {json.dumps(heartbeat, separators=(',', ':'))}\n\n"
            )
            self._send_sse(200, body)
            return

        match_job = re.match(r'^/api/v1/jobs/([^/]+)$', path)
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

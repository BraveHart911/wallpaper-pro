from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
from test_library import app, PNG




class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == '/redirect.png':
            self.send_response(302)
            self.send_header('Location', '/image.png')
            self.end_headers()
            return
        if self.path == '/missing.png':
            self.send_error(404)
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'<html>not media</html>' if self.path == '/fake.png' else PNG)


class DownloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = 'http://127.0.0.1:' + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_direct_and_redirect_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ['image.png', 'redirect.png']:
                media = app.import_media(self.url + '/' + name, Path(tmp))
                self.assertEqual(Path(media['path']).read_bytes(), PNG)

    def test_cli_requires_stdin_for_web_links(self):
        url = self.url + '/image.png?token=test%2Btoken&part=1'
        command = [sys.executable, app.__file__, 'import']
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, XDG_CONFIG_HOME=tmp, XDG_DATA_HOME=tmp)
            rejected = subprocess.run(command + [url], capture_output=True, env=env, timeout=10)
            self.assertEqual(rejected.returncode, 2)
            self.assertIn(b'--stdin', rejected.stderr)
            self.assertNotIn(url.encode(), rejected.stderr)

            imported = subprocess.run(command + ['--stdin'], input=url.encode(),
                                      capture_output=True, env=env, timeout=30, check=True)
            media = next(item for item in json.loads(imported.stdout)['library'] if item['source'] == url)
            self.assertEqual(Path(media['path']).read_bytes(), PNG)

    def test_failure_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ['missing.png', 'fake.png']:
                with self.assertRaises((OSError, ValueError)):
                    app.import_media(self.url + '/' + name, Path(tmp))
                self.assertEqual(list((Path(tmp) / 'library').iterdir()), [])

    def test_size_limit_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(app, 'MAX_BYTES', 8):
            with self.assertRaisesRegex(ValueError, 'limit'):
                app.import_media(self.url + '/image.png', Path(tmp))
            self.assertEqual(list((Path(tmp) / 'library').iterdir()), [])

import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import tempfile
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
from test_library import app

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')


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

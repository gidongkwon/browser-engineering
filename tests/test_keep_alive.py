import socket
import threading
from typing import List, Tuple, Generator

import pytest

import os
import sys

# Ensure project root on sys.path for direct module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import url as url_mod  # noqa: E402
from url import URL  # noqa: E402


class MiniServer:
    def __init__(self, host: str = "127.0.0.1"):
        self.host = host
        self._lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Allow quick reuse in CI
        self._lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._lsock.bind((self.host, 0))
        self.port = self._lsock.getsockname()[1]
        self._lsock.listen(1)
        self._lsock.settimeout(5)
        self.requests: List[bytes] = []
        self.handshakes: int = 0
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._stop = threading.Event()

        # Configure two deterministic responses
        self.body1_text = "€"  # multi-byte UTF-8 (3 bytes)
        self.body1_bytes = self.body1_text.encode("utf-8")
        self.resp1 = (
            b"HTTP/1.1 200 OK\r\n"
            + "Date: test\r\n".encode()
            + "Server: test\r\n".encode()
            + "Content-Type: text/plain; charset=utf-8\r\n".encode()
            + f"Content-Length: {len(self.body1_bytes)}\r\n".encode()
            + b"\r\n"
            + self.body1_bytes
        )

        self.body2_text = "second"
        self.body2_bytes = self.body2_text.encode("utf-8")
        self.resp2 = (
            b"HTTP/1.1 200 OK\r\n"
            + "Date: test\r\n".encode()
            + "Server: test\r\n".encode()
            + "Content-Type: text/plain; charset=utf-8\r\n".encode()
            + f"Content-Length: {len(self.body2_bytes)}\r\n".encode()
            + b"\r\n"
            + self.body2_bytes
        )

    def start(self) -> None:
        self._thread.start()

    def close(self) -> None:
        self._stop.set()
        try:
            self._lsock.close()
        finally:
            # Let the thread exit gracefully
            self._thread.join(timeout=2)

    def _read_request(self, csock: socket.socket) -> bytes:
        data = bytearray()
        # Read until end of headers CRLFCRLF
        try:
            while b"\r\n\r\n" not in data:
                chunk = csock.recv(4096)
                if not chunk:
                    break
                data.extend(chunk)
        except (socket.timeout, TimeoutError):
            # Timed out waiting for a request on this connection
            pass
        return bytes(data)

    def _serve(self) -> None:
        # Serve exactly two requests, possibly across one or two connections
        while len(self.requests) < 2 and not self._stop.is_set():
            try:
                csock, _ = self._lsock.accept()
            except OSError:
                return
            self.handshakes += 1
            with csock:
                csock.settimeout(2)
                while len(self.requests) < 2 and not self._stop.is_set():
                    req = self._read_request(csock)
                    if not req:
                        break
                    self.requests.append(req)
                    if len(self.requests) == 1:
                        csock.sendall(self.resp1)
                    else:
                        csock.sendall(self.resp2)


@pytest.fixture
def server() -> Generator[Tuple[MiniServer, str], None, None]:
    srv = MiniServer()
    srv.start()
    try:
        origin = f"http://127.0.0.1:{srv.port}"
        yield srv, origin
    finally:
        srv.close()


def test_keep_alive_reuse_and_content_length(server):
    srv, origin = server

    # Ensure a clean pool for this origin
    url_mod.connection_pool.pop(origin, None)

    # First request: expect multi-byte body handled via Content-Length bytes
    first = URL(f"{origin}/first").request()
    assert first == srv.body1_text

    # Socket should be kept open and stored in pool
    assert origin in url_mod.connection_pool
    sock1 = url_mod.connection_pool[origin]
    assert isinstance(sock1, socket.socket)
    assert sock1.fileno() != -1

    # Second request should reuse the same socket
    second = URL(f"{origin}/second").request()
    assert second == srv.body2_text
    sock2 = url_mod.connection_pool[origin]
    assert sock1 is sock2

    # Server should have seen exactly two requests on the same connection
    # and the client should have sent Connection: keep-alive
    assert len(srv.requests) == 2
    raw1 = srv.requests[0].decode("iso-8859-1", errors="replace")
    raw2 = srv.requests[1].decode("iso-8859-1", errors="replace")
    assert "Connection: keep-alive" in raw1
    assert "Connection: keep-alive" in raw2
    assert "Connection: close" not in raw1
    assert "Connection: close" not in raw2

    # Exactly one TCP handshake (one accepted connection)
    assert srv.handshakes == 1

    # Cleanup pool socket for this test
    try:
        sock1.close()
    finally:
        url_mod.connection_pool.pop(origin, None)

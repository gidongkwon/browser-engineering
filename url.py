import socket
import ssl
from consts import entities


class URL:
    def __init__(self, url: str):
        self.scheme, url = url.split(":", 1)

        # https://datatracker.ietf.org/doc/html/rfc3986
        has_authority = url.startswith("//")
        if has_authority:
            url = url[2:]

            assert self.scheme in ["http", "https", "file"]

            if "/" not in url:
                url = url + "/"
            self.host, url = url.split("/", 1)
            self.path = "/" + url
            self.port: int | None = None

            if self.scheme == "http":
                self.port = 80
            elif self.scheme == "https":
                self.port = 443

            if ":" in self.host:
                self.host, port = self.host.split(":", 1)
                self.port = int(port)
        else:
            assert self.scheme in ["data", "view-source"]
            self.path = url

    def request(self) -> str:
        if self.scheme == "file":
            with open(self.path, "r") as file:
                return file.read()

        if self.scheme == "data":
            mediatype, data = self.path.split(",", 1)
            return data

        if self.scheme == "view-source":
            source_url = URL(self.path)
            response = source_url.request()
            for entity, target in entities.items():
                response = response.replace(target, entity)
            return response

        s = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )

        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)

        s.connect((self.host, self.port))

        default_headers = {"Host": self.host, "Connection": "close"}

        request = f"GET {self.path} HTTP/1.1\r\n"
        for header, content in default_headers.items():
            request += f"{header}: {content}\r\n"
        request += "\r\n"
        s.send(request.encode("utf-8"))

        response = s.makefile("r", encoding="utf-8", newline="\r\n")
        statusline = response.readline()
        version, status, explanation = statusline.split(" ", 2)

        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n":
                break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()

        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers

        content = response.read()
        s.close()

        return content

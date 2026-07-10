"""Serve the phone-ready Study Flow app on the local network."""

from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from functools import partial
import socket
import webbrowser


APP_DIR = Path(__file__).parent / "mobile_pwa"


def local_ip() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
        except OSError:
            return "localhost"


def main() -> None:
    port = 4173
    handler = partial(SimpleHTTPRequestHandler, directory=str(APP_DIR))
    server = ThreadingHTTPServer(("0.0.0.0", port), handler)
    print("Study Flow is running.")
    print(f"This computer: http://localhost:{port}")
    print(f"Phone on the same Wi-Fi: http://{local_ip()}:{port}")
    print("Press Ctrl+C to stop the server.")
    webbrowser.open(f"http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

import sys
import argparse
import socketserver
import traceback

from .fs import LocalFileSystem, RemoteFileSystem
from .jsonrpc import JSONRPC2Connection, ReadWriter, TCPReadWriter
from .log import log
from .coalashim import run_coala_json_mode

# TODO(renfred) non-global config.
remote_fs = False


class Module:
    def __init__(self, name, path, is_package=False):
        self.name = name
        self.path = path
        self.is_package = is_package

    def __repr__(self):
        return "PythonModule({}, {})".format(self.name, self.path)


class DummyFile:
    def __init__(self, contents):
        self.contents = contents

    def read(self):
        return self.contents

    def close(self):
        pass


class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


class LangserverTCPTransport(socketserver.StreamRequestHandler):
    def handle(self):
        s = LangServer(conn=TCPReadWriter(self.rfile, self.wfile))
        try:
            s.listen()
        except Exception as e:
            tb = traceback.format_exc()
            log("ERROR: {} {}".format(e, tb))


def path_from_uri(uri):
    if not uri.startswith("file://"):
        return uri
    _, path = uri.split("file://", 1)
    return path


class LangServer(JSONRPC2Connection):
    def __init__(self, conn=None):
        super().__init__(conn=conn)
        self.root_path = None
        self.symbol_cache = None
        if remote_fs:
            self.fs = RemoteFileSystem(self)
        else:
            self.fs = LocalFileSystem()

    def handle(self, _id, request):
        """Handle the request from language client."""
        log("REQUEST: ", request)
        resp = None

        if request["method"] == "initialize":
            resp = self.serve_initialize(request)
        elif request["method"] == "textDocument/didchange":
            resp = self.serve_change(request)

        if resp is not None:
            self.write_response(request["id"], resp)

    def serve_initialize(self, request):
        """Serve for the initialization request."""
        params = request["params"]
        self.root_path = path_from_uri(params["rootPath"])
        return {
            "capabilities": {}
        }

    def serve_change(self, request):
        log("REQUEST: ", request)
        params = request["params"]
        return None


def main():
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--mode", default="stdio", help="communication (stdio|tcp)")
    # TODO use this
    parser.add_argument("--fs", default="local", help="file system (local|remote)")
    parser.add_argument("--addr", default=2087, help="server listen (tcp)", type=int)
    parser.add_argument("--remote", default=0, help="temp, enable remote fs",
                        type=int)  # TODO(renfred) remove

    args = parser.parse_args()

    global remote_fs
    remote_fs = bool(args.remote)

    if args.mode == "stdio":
        log("Reading on stdin, writing on stdout")
        s = LangServer(conn=ReadWriter(sys.stdin, sys.stdout))
        s.listen()
    elif args.mode == "tcp":
        host, addr = "0.0.0.0", args.addr
        log("Accepting TCP connections on {}:{}".format(host, addr))
        ThreadingTCPServer.allow_reuse_address = True
        s = ThreadingTCPServer((host, addr), LangserverTCPTransport)
        try:
            s.serve_forever()
        finally:
            s.shutdown()


if __name__ == "__main__":
    main()

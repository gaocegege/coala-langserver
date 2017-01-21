import sys
import argparse
import socketserver
import traceback

from .fs import LocalFileSystem, RemoteFileSystem
from .jsonrpc import JSONRPC2Connection, ReadWriter, TCPReadWriter
from .log import log
from .coalashim import run_coala_with_specific_file
from .uri import path_from_uri
from .diagnostic import output_to_diagnostics

# TODO(renfred) non-global config.
remote_fs = False


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


class LangServer(JSONRPC2Connection):
    """Language server for coala base on JSON RPC."""

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
        elif request["method"] == "textDocument/didChange":
            resp = self.serve_change(request)
        elif request["method"] == "textDocument/didSave":
            resp = self.serve_did_save(request)
        elif request["method"] == "workspace/didChangeWatchedFiles":
            resp = self.serve_did_change_watched_files(request)

        if resp is not None:
            self.write_response(request["id"], resp)

    def serve_initialize(self, request):
        """Serve for the initialization request."""
        params = request["params"]
        # Notice that the root_path could be None.
        if "rootUri" in params:
            self.root_path = path_from_uri(params["rootUri"])
        elif "rootPath" in params:
            self.root_path = path_from_uri(params["rootPath"])
        return {
            "capabilities": {}
        }

    def serve_did_save(self, request):
        """Serve for did_change request."""
        params = request["params"]
        uri = params["textDocument"]["uri"]
        path = path_from_uri(uri)
        path, diagnostics = output_to_diagnostics(
            run_coala_with_specific_file(self.root_path, path))
        self.send_diagnostics(path, diagnostics)
        return None

    def serve_change(self, request):
        """Serve for the request of documentation changed."""
        params = request["params"]
        uri = params["textDocument"]["uri"]
        path = path_from_uri(uri)
        path, diagnostics = output_to_diagnostics(
            run_coala_with_specific_file(self.root_path, path))
        self.send_diagnostics(path, diagnostics)
        return None

    def serve_did_change_watched_files(self, request):
        """Serve for thr workspace/didChangeWatchedFiles request."""
        changes = request["changes"]
        for fileEvent in changes:
            uri = fileEvent["uri"]
            path = path_from_uri(uri)
            path, diagnostics = output_to_diagnostics(
                run_coala_with_specific_file(self.root_path, path))
            self.send_diagnostics(path, diagnostics)

    def send_diagnostics(self, path,  diagnostics):
        if remote_fs is True:
            log("TODO: Support remote file system.")
        params = {
            # TODO: replace file with appropriate protocol.
            "uri": "file://{0}".format(path),
            "diagnostics": diagnostics,
        }
        self.send_notification("textDocument/publishDiagnostics", params)


def main():
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--mode", default="stdio", help="communication (stdio|tcp)")
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

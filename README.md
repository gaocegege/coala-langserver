# Coala language server

**UNMAINTAINED: MOVE TO [github.com/coala/coala-vs-code](https://github.com/coala/coala-vs-code)**

This is a language server for Coala that adheres to the [Language Server Protocol (LSP)](https://github.com/Microsoft/language-server-protocol/blob/master/protocol.md). Python versions 3.x are supported.

**Note: this language server is currently in the early stages of active development and not all features are yet supported.**

## Getting started

You'll need python version 3.5 or greater.

1. `pip3 install -r requirements.txt`
1. `python3 langserver-python.py --mode=tcp --addr=2087`

To try it in [Visual Studio Code](https://code.visualstudio.com), install the [vscode-client](https://github.com/sourcegraph/langserver/tree/master/vscode-client) extension and then open up a file.

## Feature preview

![](./docs/images/demo.gif)

## Reference

* [python-langserver](https://github.com/sourcegraph/python-langserver)

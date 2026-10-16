"""Invoke the installed pen.dev desktop MCP server over its stdio interface."""
import json
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

SERVER = r"C:\Program Files\Pen\resources\app.asar.unpacked\out\mcp-server-windows-x64.exe"
request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
process = subprocess.Popen([SERVER, "--app", "desktop", "--agent", "codexCLI"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
messages = queue.Queue()
def read():
    for line in process.stdout:
        try:
            messages.put(json.loads(line))
        except ValueError:
            pass
threading.Thread(target=read, daemon=True).start()
def send(value):
    process.stdin.write(json.dumps(value) + "\n")
    process.stdin.flush()
def receive(identifier, timeout=55):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = messages.get(timeout=max(0.1, deadline-time.monotonic()))
        if response.get("id") == identifier:
            return response
    raise TimeoutError("pen.dev desktop MCP response timed out")
try:
    send({"jsonrpc":"2.0", "id":1, "method":"initialize", "params":{"protocolVersion":"2024-11-05", "capabilities":{}, "clientInfo":{"name":"codex-fornada-design", "version":"1.0"}}})
    receive(1)
    send({"jsonrpc":"2.0", "method":"notifications/initialized"})
    send({"jsonrpc":"2.0", "id":2, **request})
    response = receive(2)
    output = Path(sys.argv[1]).with_suffix(".response.json")
    output.write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
    for block in response.get("result", {}).get("content", []):
        if block.get("type") == "text":
            print(block["text"])
    if "error" in response:
        print(json.dumps(response["error"]))
    print(f"Response: {output}")
finally:
    process.terminate()

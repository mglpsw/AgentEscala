#!/usr/bin/env python3
import json
import os
import sys
import urllib.request
import ssl

API_URL = os.environ.get("HOMELAB_API_URL", "https://api.ks-sm.net:9443")
TOKEN = os.environ.get("HOMELAB_API_TOKEN", "")

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


def request(method, endpoint, body=None):
    url = f"{API_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}

    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, context=ssl_ctx) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)}


TOOLS = [
    {"name": "health"},
    {"name": "providers"},
    {"name": "chat"},
]


def handle(tool, args):
    if tool == "health":
        return request("GET", "/health")

    if tool == "providers":
        return request("GET", "/v1/providers/status")

    if tool == "chat":
        return request("POST", "/v1/chat/ingest", {
            "message": args.get("mensagem", "")
        })

    return {"error": "unknown tool"}


def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break

        try:
            msg = json.loads(line)
            tool = msg.get("tool")
            args = msg.get("args", {})
            result = handle(tool, args)

            print(json.dumps(result), flush=True)
        except:
            pass


if __name__ == "__main__":
    main()

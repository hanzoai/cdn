#!/usr/bin/env python3
"""Generate hanzo/market/*.json from a desktop app's bundled store data.

Usage:
  scripts/gen-market.py /path/to/app/src/lib   # dir with store-responses.json + composio/

cdn.hanzo.ai/market/* is served from hanzo/market/* (R2 pub/hanzo/market/*).
The shape mirrors what the desktop store-client parses, so the CDN can replace
the backend entirely (and the app bundles these same files as offline fallback).
"""
import json, os, shutil, sys

src = sys.argv[1] if len(sys.argv) > 1 else "."
out = os.path.join(os.path.dirname(__file__), "..", "hanzo", "market")
os.makedirs(os.path.join(out, "tools"), exist_ok=True)

d = json.load(open(os.path.join(src, "store-responses.json")))
json.dump(d["agents"], open(f"{out}/agents.json", "w"), indent=2)
json.dump(d["tools"], open(f"{out}/tools.json", "w"), indent=2)
json.dump(d["categories"], open(f"{out}/categories.json", "w"), indent=2)
json.dump(d["featured_collections"], open(f"{out}/featured.json", "w"), indent=2)
json.dump(d.get("user_purchases", []), open(f"{out}/purchases.json", "w"), indent=2)
for k, v in d.get("tool_details", {}).items():
    json.dump(v, open(f"{out}/tools/{k}.json", "w"), indent=2)

composio = os.path.join(src, "composio", "composio-registry.json")
if os.path.exists(composio):
    shutil.copy(composio, f"{out}/plugins.json")

man = {
    "version": "1",
    "networks": ["did:hanzo", "did:lux", "did:zoo"],
    "counts": {
        "agents": d["agents"]["total"], "tools": d["tools"]["total"],
        "categories": len(d["categories"]), "featured": len(d["featured_collections"]),
        "tool_details": len(d.get("tool_details", {})),
    },
    "endpoints": [
        "/market/agents.json", "/market/tools.json", "/market/categories.json",
        "/market/featured.json", "/market/purchases.json", "/market/plugins.json",
        "/market/tools/{id}.json",
    ],
}
json.dump(man, open(f"{out}/index.json", "w"), indent=2)
print("wrote", out)

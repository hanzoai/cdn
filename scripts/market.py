#!/usr/bin/env python3
"""Build and verify the Market catalog served at cdn.hanzo.ai/market/*.

The Market is backend-less: every read is a static file on the CDN, and each
desktop app bundles a trimmed copy of the same shape as an offline fallback.
This script is the ONE place that produces both, so the CDN, the bundles and the
CI gate can never disagree about the schema or the version digest.

    scripts/market.py gen --from ../store            # -> hanzo/market/*
    scripts/market.py gen --from ../store \
        --bundle ../desktop/apps/hanzo-desktop/src/lib/market-catalog.json
    scripts/market.py check                          # CI gate, needs no inputs

`--from` is a checkout of the curated flatfile catalog (hanzoai/store): one JSON
per item under data/agents/ and data/tools/. `--bundle` writes an app's offline
fallback; repeat it once per app.

Layout (cdn.hanzo.ai/market/<f>  <-  hanzo/market/<f>  <-  R2 pub/hanzo/market/<f>):

    index.json       manifest: schema, version, counts, files
    agents.json      {"products": [...], "total", "page", "limit", "totalPages"}
    tools.json       same shape
    categories.json  [{"id","name","description","icon","item_count"}]
    featured.json    [{"id","name","description","items","icon"}]
    tools/<id>.json  per-tool detail
    plugins.json     composio plugin registry (preserved across regeneration)
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "hanzo", "market")

# Bumped only on a breaking change to the document shapes below. A client that
# does not recognise the schema should keep using its bundled fallback.
SCHEMA = 1

# Icons in the upstream flatfiles are EXPIRED presigned R2 URLs that also embed
# an AWS credential + signature in the query string. They 403 on fetch and have
# no place in a world-readable CDN file, so they are dropped and each app falls
# back to its own placeholder.
PRESIGNED = re.compile(r"X-Amz-(Signature|Credential)=", re.I)


def clean_url(url):
    if not isinstance(url, str) or not url or PRESIGNED.search(url):
        return ""
    return url


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


TOOLS_REPO = "github.com/hanzoai/tools"


def router_key(item):
    """npm-style @namespace/name — the id the desktop app installs by."""
    home = item.get("homepage") or ""
    if home.startswith("@"):
        return home
    if ":::" in home:  # legacy local:::__official_shinkai:::audio_insight
        return "@hanzo/" + home.split(":::")[-1].replace("_", "-")
    return "@hanzo/" + item["id"]


def repository(item):
    """Where the code lives. A few upstream items carry a legacy `local:::…` DID
    in this field, which is an identity, not a repository — the app deep-links
    it, so it has to be a real repo."""
    repo = item.get("repository") or ""
    return TOOLS_REPO if not repo or ":::" in repo else repo


def product(item):
    """The one canonical Market product shape: a superset of what any single app
    renders, so every app maps from the same document."""
    cat = item.get("category") or "Other"
    kind = item.get("type") or "Tool"
    return {
        "id": item["id"],
        "name": item["name"],
        "description": item.get("description", ""),
        "author": item.get("author", ""),
        "version": item.get("version", "0.0.0"),
        "license": item.get("license", ""),
        "downloads": item.get("downloads", 0),
        "icon_url": clean_url(item.get("icon")),
        "router_key": router_key(item),
        "repository": repository(item),
        "path": item.get("path")
        or "/{}/{}".format("agents" if kind == "Agent" else "tools", item["id"]),
        "type": kind,
        "tags": item.get("tags") or [],
        "category": {"id": slug(cat), "name": cat, "description": "", "examples": ""},
    }


def page(products):
    return {
        "products": products,
        "total": len(products),
        "page": 1,
        "limit": len(products),
        "totalPages": 1,
    }


def detail(p, item):
    return dict(
        p,
        screenshots=[s for s in map(clean_url, item.get("screenshots") or []) if s],
        readme=item.get("readme", ""),
        changelog=item.get("changelog", ""),
        install_command=item.get("installCommand", ""),
        mcp_config=item.get("mcpConfig") or {},
        operating_system=item.get("operatingSystem") or [],
        runner=item.get("runner", "any"),
        price=item.get("price", 0),
        created_at=item.get("createdAt", ""),
        updated_at=item.get("updatedAt", ""),
    )


def read_dir(path):
    if not os.path.isdir(path):
        return []
    items = []
    for name in sorted(os.listdir(path)):
        if name.endswith(".json"):
            with open(os.path.join(path, name)) as fh:
                items.append(json.load(fh))
    return items


def categories(items):
    counts = {}
    for it in items:
        name = it.get("category") or "Other"
        counts[name] = counts.get(name, 0) + 1
    return [
        {"id": slug(n), "name": n, "description": "", "icon": "", "item_count": counts[n]}
        for n in sorted(counts)
    ]


def featured(agents, tools, flagged):
    """Collections derived from the catalog itself — no hand-maintained list of
    ids to drift out of sync with the items it points at."""

    def top(xs, n):
        return [p["id"] for p in sorted(xs, key=lambda p: -p["downloads"])[:n]]

    return [
        {
            "id": "editors-choice",
            "name": "Editor's Choice",
            "description": "Hand-picked by the Hanzo team",
            "items": flagged[:6] or top(agents, 3),
            "icon": "star",
        },
        {
            "id": "top-agents",
            "name": "Top Agents",
            "description": "Most installed agents",
            "items": top(agents, 6),
            "icon": "sparkles",
        },
        {
            "id": "top-tools",
            "name": "Top Tools",
            "description": "Most installed tools",
            "items": top(tools, 6),
            "icon": "wrench",
        },
    ]


def dump(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
        fh.write("\n")


def version_of(docs):
    """Content digest over every served document. The manifest version changes if
    and only if what the CDN serves changes, so a deploy is verifiable and a
    client can tell two catalogs apart without diffing them."""
    h = hashlib.sha256()
    for name in sorted(docs):
        h.update(name.encode())
        h.update(json.dumps(docs[name], sort_keys=True, separators=(",", ":")).encode())
    return h.hexdigest()[:16]


def build(src):
    raw_agents = read_dir(os.path.join(src, "data", "agents"))
    raw_tools = read_dir(os.path.join(src, "data", "tools"))
    if not raw_agents and not raw_tools:
        sys.exit(f"no catalog under {src}/data/{{agents,tools}}")

    agents = [product(i) for i in raw_agents]
    tools = [product(i) for i in raw_tools]
    flagged = [
        p["id"]
        for p, i in zip(agents + tools, raw_agents + raw_tools)
        if i.get("featured")
    ]

    docs = {
        "agents.json": page(agents),
        "tools.json": page(tools),
        "categories.json": categories(raw_agents + raw_tools),
        "featured.json": featured(agents, tools, flagged),
    }
    for p, i in zip(tools, raw_tools):
        docs[f"tools/{p['id']}.json"] = detail(p, i)
    return docs


def manifest_for(docs):
    return {
        "schema": SCHEMA,
        "version": version_of(docs),
        "counts": {
            "agents": docs["agents.json"]["total"],
            "tools": docs["tools.json"]["total"],
            "categories": len(docs["categories.json"]),
            "featured": len(docs["featured.json"]),
            "tool_details": sum(1 for k in docs if k.startswith("tools/")),
        },
        "files": {
            "agents": "agents.json",
            "tools": "tools.json",
            "categories": "categories.json",
            "featured": "featured.json",
            "plugins": "plugins.json",
            "tool_detail": "tools/{id}.json",
        },
    }


def bundle_for(docs, manifest):
    """An app's offline fallback: the browsable catalog, minus the per-tool
    detail documents and the 1.2 MB plugin registry, which are fetched on
    demand and are not worth carrying in every binary."""
    return {
        "schema": manifest["schema"],
        "version": manifest["version"],
        "agents": docs["agents.json"],
        "tools": docs["tools.json"],
        "categories": docs["categories.json"],
        "featured": docs["featured.json"],
    }


def gen(args):
    docs = build(args.src)

    # plugins.json is a pass-through registry, not derived from the catalog, so
    # it is preserved across regeneration rather than rebuilt.
    plugins = os.path.join(OUT, "plugins.json")
    keep = open(plugins, "rb").read() if os.path.exists(plugins) else None

    shutil.rmtree(OUT, ignore_errors=True)
    for name, doc in docs.items():
        dump(os.path.join(OUT, name), doc)
    if keep is not None:
        with open(plugins, "wb") as fh:
            fh.write(keep)

    manifest = manifest_for(docs)
    dump(os.path.join(OUT, "index.json"), manifest)
    for path in args.bundle:
        dump(path, bundle_for(docs, manifest))
        print("bundle", path)
    print("market", manifest["version"], manifest["counts"])


def check(_args):
    """Verify the committed catalog is internally consistent — no network, no
    checkout of anything else. This is the CI gate: it proves the files the CDN
    will serve are valid JSON, that the manifest describes them accurately, and
    that the version digest is the one the content actually hashes to."""
    fail = []

    def load(name):
        path = os.path.join(OUT, name)
        if not os.path.exists(path):
            fail.append(f"missing {name}")
            return None
        try:
            with open(path) as fh:
                return json.load(fh)
        except json.JSONDecodeError as exc:
            fail.append(f"invalid JSON in {name}: {exc}")
            return None

    manifest = load("index.json")
    if manifest is None:
        sys.exit("market/index.json is missing or unreadable")
    if manifest.get("schema") != SCHEMA:
        fail.append(f"schema {manifest.get('schema')} != {SCHEMA}")

    docs = {}
    for name in ("agents.json", "tools.json", "categories.json", "featured.json"):
        doc = load(name)
        if doc is not None:
            docs[name] = doc

    ids = set()
    for name in ("agents.json", "tools.json"):
        doc = docs.get(name)
        if doc is None:
            continue
        if doc["total"] != len(doc["products"]):
            fail.append(f"{name}: total {doc['total']} != {len(doc['products'])} products")
        for p in doc["products"]:
            missing = [k for k in ("id", "name", "router_key", "category") if not p.get(k)]
            if missing:
                fail.append(f"{name}: {p.get('id', '?')} missing {missing}")
            if p["id"] in ids:
                fail.append(f"duplicate id {p['id']}")
            ids.add(p["id"])

    # Every tool must have its detail document, since the app deep-links to it.
    for p in (docs.get("tools.json") or {"products": []})["products"]:
        doc = load(f"tools/{p['id']}.json")
        if doc is not None:
            docs[f"tools/{p['id']}.json"] = doc

    # Featured collections must point at items that exist.
    for coll in docs.get("featured.json") or []:
        for item in coll["items"]:
            if item not in ids:
                fail.append(f"featured/{coll['id']} references unknown id {item}")

    if len(docs) == 4 + len((docs.get("tools.json") or {"products": []})["products"]):
        digest = version_of(docs)
        if digest != manifest.get("version"):
            fail.append(f"version {manifest.get('version')} != content digest {digest}")
        for key, want in manifest["counts"].items():
            got = {
                "agents": len(docs["agents.json"]["products"]),
                "tools": len(docs["tools.json"]["products"]),
                "categories": len(docs["categories.json"]),
                "featured": len(docs["featured.json"]),
                "tool_details": sum(1 for k in docs if k.startswith("tools/")),
            }[key]
            if got != want:
                fail.append(f"counts.{key} says {want}, found {got}")

    if fail:
        for f in fail:
            print("FAIL", f, file=sys.stderr)
        sys.exit(f"{len(fail)} problem(s) in hanzo/market")
    print(f"ok  schema {manifest['schema']}  version {manifest['version']}  {manifest['counts']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gen", help="rebuild hanzo/market from a catalog checkout")
    g.add_argument("--from", dest="src", required=True, help="hanzoai/store checkout")
    g.add_argument("--bundle", action="append", default=[], help="app fallback path")
    g.set_defaults(fn=gen)

    c = sub.add_parser("check", help="verify the committed catalog (CI gate)")
    c.set_defaults(fn=check)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()

"""Smoke-test CLI for the Measure Studio API client.

    python -m app.sources

Hits the API to verify auth + endpoints. Prints connected accounts and post
groups so you can copy the right `id` into `config/campaigns.yaml` under
`measure_studio_group_id`.

Add `--group <id>` to also pull a sample of posts from that group.

Add `--posts <id>` to dump the first 3 posts as NormalizedPost rows so you
can sanity-check the field mapping before flipping refresh.py to API mode.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from app.sources.measure_studio_api import (
    MeasureStudioClient,
    MeasureStudioUnavailable,
)


def main() -> int:
    p = argparse.ArgumentParser(description="Measure Studio API smoke test")
    p.add_argument("--group", type=int, help="Post group ID to preview")
    p.add_argument("--posts", type=int, help="Post group ID to dump NormalizedPost rows for")
    p.add_argument("--limit", type=int, default=3, help="Max posts to dump (default 3)")
    args = p.parse_args()

    try:
        client = MeasureStudioClient.from_env()
    except MeasureStudioUnavailable as e:
        print(f"✗ {e}")
        return 1

    print(f"→ Base URL: {client.base_url}")
    print(f"→ Token:    {client.token[:8]}…{client.token[-4:]}\n")

    # Accounts
    try:
        accounts = client.list_accounts()
    except MeasureStudioUnavailable as e:
        print(f"✗ list_accounts failed: {e}")
        return 1
    print(f"Accounts ({len(accounts)}):")
    for a in accounts[:15]:
        plat = a.get("account_type") or a.get("platform") or "?"
        name = a.get("display_name", "?")
        aid = a.get("id", "?")
        slug = a.get("slug_name", "")
        print(f"  [{aid}] {plat:18s} {name}  ({slug})")
    print()

    # Groups
    try:
        groups = client.list_groups()
    except MeasureStudioUnavailable as e:
        print(f"✗ list_groups failed: {e}")
        return 1
    print(f"Groups ({len(groups)}):")
    for g in groups:
        gid = g.get("id", "?")
        name = g.get("name", "?")
        count = g.get("post_count", 0)
        print(f"  [{gid:>6}] {name:50s} ({count} posts)")
    print()

    # Optional: peek into one group
    if args.group:
        print(f"\n--- Sampling group {args.group} ---")
        for i, post in enumerate(client.search_posts(group_ids=[args.group])):
            s = post.get("stats") or {}
            print(f"  {post.get('account_type','?'):14s} {post.get('status','?'):8s} "
                  f"impr_paid={s.get('impressions_paid','-')} eng_total={s.get('engagements_total','-')} "
                  f"spend=${s.get('spend','-')}  "
                  f"{(post.get('title') or post.get('description') or '')[:55]}")
            if i + 1 >= args.limit:
                break

    # Optional: dump NormalizedPost rows
    if args.posts:
        print(f"\n--- NormalizedPost dump (group {args.posts}, first {args.limit}) ---")
        rows = client.fetch_group(args.posts)[: args.limit]
        for r in rows:
            d = asdict(r)
            # Strip noisy fields
            d.pop("raw", None)
            print(json.dumps(d, indent=2, default=str))

    return 0


if __name__ == "__main__":
    sys.exit(main())

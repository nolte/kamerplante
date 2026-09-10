#!/usr/bin/env python3
"""Refuse a Kamerplanter image reference in the RELEASE chart without a digest.

Issue #987: the released chart referenced `ghcr.io/nolte/kamerplanter-*:latest`.
A tag that is rewritten by every publish cannot be rolled back to — "go back to
the previous image" resolves to whatever is current — so the documented recovery
path was inert in exactly the situation it exists for. The release job
(`publish-helm-charts` in docker-publish.yml) now rewrites every such reference
to `tag: <version>@sha256:<digest>` through scripts/ci/pin_chart_image_digests.sh
before the chart is packaged, and this check runs right after that step, on the
rewritten file, as the independent proof that nothing escaped.

It runs at RELEASE time and nowhere else, on purpose. Until 2026-09-10 the
develop tree carried `latest@sha256:…` pins too, kept current by a Renovate
rule, and this check sat in the required `static` gate to keep them there. That
develop-side pin fed a chart no deployment consumes — ArgoCD tracks a released
chart version, and docs/deployment/ci-cd.md says out loud that nothing points
at the `-dev` channel — while the Renovate branch carrying the next digest was
rebased by every publish and never merged (#1326). The develop values reference
`latest` again, the release pins, and the guard follows the pin.

Two things are checked:

  1. every Kamerplanter image reference carries `@sha256:<64 hex>`
  2. all references to the SAME repository within one file carry the SAME
     digest — the backend image appears three times (api, celery-worker,
     celery-beat), so a half-applied rewrite would ship two builds of one
     application against one database schema

Third-party images (arangodb, timescale/timescaledb) are deliberately out of
scope: they sit on upstream version tags that Renovate ages, and folding them in
here would silently widen a delivery change into a supply-chain policy change.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CHART_GLOB = "helm/**/values*.yaml"

# The images this repository builds and publishes. Everything else is upstream.
OWNED_PREFIX = "ghcr.io/nolte/kamerplanter-"

# pin_chart_image_digests.sh addresses `..image.repository` / `..image.tag`
# pairs by YAML path; the same shape is matched here so the guard and the
# rewrite see the same references.
IMAGE_KEY_RE = re.compile(r"image$", re.IGNORECASE)

# `<version>@sha256:<64 hex>` — the shape pin_chart_image_digests.sh writes.
PINNED_TAG_RE = re.compile(r"^[\w][\w.\-]*@sha256:[0-9a-f]{64}$")


def _walk(node: Any, path: str = "") -> list[tuple[str, str, str]]:
    """Yield (yaml-path, repository, tag) for every image spec found."""
    found: list[tuple[str, str, str]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            child = f"{path}.{key}" if path else str(key)
            if (
                IMAGE_KEY_RE.search(str(key))
                and isinstance(value, dict)
                and "repository" in value
            ):
                repository = str(value.get("repository", ""))
                tag = str(value.get("tag", value.get("version", "")))
                found.append((child, repository, tag))
                # An image spec has no nested image specs; do not descend.
                continue
            found.extend(_walk(value, child))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            found.extend(_walk(item, f"{path}[{index}]"))
    return found


def main() -> int:
    problems: list[str] = []
    checked = 0

    files = sorted(REPO_ROOT.glob(CHART_GLOB))
    if not files:
        print(
            "::error::No chart values files matched "
            f"{CHART_GLOB} — the guard would pass by examining nothing.",
            file=sys.stderr,
        )
        return 1

    for values_file in files:
        try:
            documents = list(yaml.safe_load_all(values_file.read_text()))
        except yaml.YAMLError as exc:
            problems.append(f"{values_file.relative_to(REPO_ROOT)}: unparseable YAML: {exc}")
            continue

        digests_seen: dict[str, dict[str, list[str]]] = {}
        for document in documents:
            for yaml_path, repository, tag in _walk(document):
                if not repository.startswith(OWNED_PREFIX):
                    continue
                checked += 1
                where = f"{values_file.relative_to(REPO_ROOT)}:{yaml_path}"
                if not PINNED_TAG_RE.match(tag):
                    problems.append(
                        f"{where}\n"
                        f"    {repository}:{tag}\n"
                        "    is not pinned. Use `tag: <version>@sha256:<digest>`; resolve the\n"
                        "    digest with `docker buildx imagetools inspect "
                        f"{repository}:<version>`."
                    )
                    continue
                digest = tag.split("@", 1)[1]
                digests_seen.setdefault(repository, {}).setdefault(digest, []).append(where)

        for repository, by_digest in digests_seen.items():
            if len(by_digest) > 1:
                detail = "\n".join(
                    f"      {digest} <- {', '.join(places)}"
                    for digest, places in sorted(by_digest.items())
                )
                problems.append(
                    f"{values_file.relative_to(REPO_ROOT)}: {repository} is pinned to "
                    f"{len(by_digest)} different digests in one file:\n{detail}\n"
                    "    A half-applied bump ships two builds of one application."
                )

    if problems:
        print(
            "::error::Kamerplanter image references must be digest-pinned (#987):",
            file=sys.stderr,
        )
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1

    print(f"{checked} Kamerplanter image references, all digest-pinned.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

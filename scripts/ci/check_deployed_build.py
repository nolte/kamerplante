#!/usr/bin/env python3
"""Ask a running instance whether it serves the build its chart version pins.

Issue #1236 — the LAST hop of the delivery chain, and the only one nothing
measures. A merge reaches a cluster in four hops::

    merge -> docker-publish (GHCR) -> release (chart pins the digest) -> ArgoCD sync

Hop 3 used to be a Renovate pull request carrying the digest into the develop
tree, watched by a freshness lane; both were removed on 2026-09-10 because no
deployment consumed that tree (see below), and the release job pins the digest
itself. That hop-3 check was **green throughout the 2026-08-17 incident, and
correctly so** — the chart pinned a perfectly good build. Nobody measured hop
4: does the *pod* run those bytes? It did not, for days, and it surfaced only
when an operator re-triggered a bug a merged fix had already removed.

This script asks the instance itself, comparing two values that are the same
40-character git SHA by construction:

  (a) ``org.opencontainers.image.revision`` on the deployed image, written by
      ``docker/metadata-action`` from ``github.sha``; and
  (b) ``build_revision`` from ``GET <instance>/api/health``, baked into the image
      by ``src/backend/Dockerfile`` (``ARG``/``ENV BUILD_REVISION``) from
      ``docker-publish.yml`` (``build-args: BUILD_REVISION=${{ github.sha }}``).

Both come from the same expression in the same build, so they are compared in
full. There is no truncation rule anywhere, deliberately: a truncation rule is a
thing to get wrong. Measured on 2026-09-01 against the reference deployment, the
two sides agree exactly — image ``sha256:f1059661…`` annotates
``07502fd7510dc32de2bbfdd6fd178ec2041e56a9`` and bakes
``BUILD_REVISION=07502fd7510dc32de2bbfdd6fd178ec2041e56a9``.

WHY THIS IS NOT A GITHUB ACTIONS WORKFLOW (#1236, measured 2026-09-01)
----------------------------------------------------------------------
A predecessor of this script was a scheduled workflow reading
``vars.DEPLOYED_INSTANCE_URL``. That shape was refuted on two independent counts
and the workflow is deliberately absent:

1. **A GitHub-hosted runner cannot reach the instance.** The reference
   deployment answers on ``https://kamerplanter.just-a-lab.duckdns.org``, whose
   A record — from ``8.8.8.8``, ``1.1.1.1`` and ``9.9.9.9`` alike — is
   ``192.168.178.166``, an RFC1918 address. The repository has no self-hosted
   runners (``gh api …/actions/runners`` → ``total_count: 0``). A hosted runner
   would time out; a runner that *did* own ``192.168.178.0/24`` would silently
   measure some other machine. The second failure mode is worse than the first.
2. **The repository's own chart pin is the wrong operand.** Production tracks a
   *published chart version* (ArgoCD ``targetRevision: 0.2.1`` against
   ``oci://ghcr.io/nolte/charts/kamerplanter``), not the ``develop`` channel that
   ``helm/kamerplanter/values.yaml`` carries. On 2026-09-01 the repository chart
   pinned ``sha256:e2b0aec4…`` (revision ``37cbc06f…``, channel ``develop``)
   while the released chart 0.2.1 pinned ``sha256:f1059661…`` (revision
   ``07502fd7…``) and the pod ran exactly that. A check comparing the repository
   chart against production would have reported permanent "drift" for what is
   ordinary release lag — a lane ``release-lag.yml`` already watches — while hop
   4 was in fact clean.

So the expected build is named by ``--chart-version``: the chart version the
deployment actually targets. This runs where the instance is reachable — an
operator workstation (``task verify:deployed-build``) or a job inside the
cluster — and never assumes CI can see the far end.

THE ORDERING / IDENTITY ANCHOR
------------------------------
A check that reads two operands at two moments can report a mismatch that was
already resolved, or a match that no longer holds. Here the two sides are
deliberately asymmetric:

* **The expected side has no read-time at all.** ``--chart-version`` names a
  released, immutable chart; the image digest inside it is content-addressed and
  the revision annotation is a property of those bytes. Reading it earlier or
  later yields the same answer, so it contributes no window. The resolved chart
  manifest digest is recorded in the report so the measurement is reproducible
  from the report alone. A *pre-release* version (``0.2.1-dev``) is the one
  exception — that OCI tag is rewritten by every ``helm/**`` merge — and is
  reported as a caveat rather than silently treated as immutable.
* **The instance side is a fact about one instant**, and only that instant. A
  ``drift`` verdict can therefore be stale-positive (fixed between the read and
  the reader); it cannot be a false negative about the instant it names.

There is a second, sharper anchor problem that a single request cannot see: a
Deployment mid-rollout has **old and new pods behind the same Service**, so one
``GET /api/health`` samples whichever replica the Service happened to pick. A
one-shot check is therefore non-deterministic exactly when the system is in
transition — it reports ``match`` or ``drift`` by luck of the draw. This script
samples ``--samples`` times (default 3) and treats the *set* of revisions it saw
as the measurement:

* one distinct revision -> the ordinary comparison;
* several, one of which is expected -> ``rolling`` **while the expected image is
  younger than the grace window**: some replicas already serve it, others do
  not, which is what a rollout looks like. Past that window a still-split
  Service is ``drift`` on the replicas that never rolled — a rollout does not
  take a day, and letting ``rolling`` swallow it would give this check a
  permanent blind spot in a partial hop-4 failure;
* several, none expected -> ``drift``, and every observed revision is reported.

Sampling widens the window; it does not close it. Against a single-replica
Deployment every sample necessarily hits the same pod, and a Service can route
several samples to one replica by chance. Stated here rather than silently
assumed.

THE INSTANCE HAS THREE ANSWERS, NOT TWO
---------------------------------------
``build_revision`` is disclosed only when the instance sets
``HEALTH_EXPOSE_BUILD_REVISION``. The three well-formed replies mean three
different things and must never be collapsed:

``no build_revision key at all``
    The instance was configured not to disclose its build. **Nothing is wrong
    with the deployment** — but this check cannot run against it. Raises
    :class:`BuildRevisionNotDisclosedError`: loud, and with a message naming the
    setting rather than anything resembling drift.
``"unknown"``
    The instance is willing to disclose, but no build stamped a revision into
    the image (a dev image, or a build without the ``BUILD_REVISION`` build-arg).
    The measurement is undetermined: loud, and no verdict.
``a 40-character hex SHA``
    The real answer. The only reply that reaches :func:`decide`.

WHY "NOT DISCLOSED" IS LOUD AND NOT A GREEN WARNING
---------------------------------------------------
Running this check **is** the statement "I want hop 4 answered". If the far end
declines to answer, the check is not running — and NFR-018 §2's thesis is that a
check which cannot report a failure is indistinguishable from one that is not
running. A green result saying "not disclosed" is exactly that shape.

Until 2026-09-01 that made the check inert against the reference deployment,
which is the trap #1236 predicted. ``helm/kamerplanter/values.yaml`` now carries
``HEALTH_EXPOSE_BUILD_REVISION: "true"`` as a chart default, so the setting
arrives with the chart and needs no action in the GitOps repository. Verified by
rendering the released chart 0.2.1 with the production ``Application``'s own
``valuesObject``: the chart default and every operator override survive the same
Helm merge. The disclosure trade — the mapping *this host runs that commit*
yields the exact patch distance to ``develop`` — is the one this repository's own
documentation already recommends taking for an auditable production instance.

FAIL LOUD (NFR-018 §2)
----------------------
An unreachable instance, a reply that is not a Kamerplanter health payload, an
undisclosed or ``"unknown"`` revision, a revision that is not a full SHA, a chart
version that cannot be resolved, a missing revision annotation, a missing
``created`` timestamp or an unparseable manifest is NOT "no drift". It raises,
:func:`run` prints ``::error::`` and exits :data:`EXIT_UNDETERMINED` **without
writing the report**, so a consumer that acts on the report cannot mistake an
undetermined check for a clean one.

Exit codes are the alert here, because — unlike the three shipped watchers —
there is no workflow step to carry it into an issue: :data:`EXIT_OK` for
``match``/``within_grace``/``rolling``, :data:`EXIT_DRIFT` for the incident,
:data:`EXIT_UNDETERMINED` for anything undetermined, :data:`EXIT_USAGE` for a
bad invocation.

The registry plumbing below is deliberately self-contained (it used to
duplicate the since-removed ``check_digest_freshness.py`` rather than import it):
this script answers one question of the registry on its own schedule, and no
sibling lane can silently alter it.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import io
import json
import os
import re
import sys
import tarfile
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import yaml

REGISTRY_HOST = "ghcr.io"

#: The published chart production tracks (ArgoCD ``repoURL``), without the host.
CHART_REPOSITORY = "nolte/charts/kamerplanter"

#: The image whose build identity ``/api/health`` reports. The frontend serves no
#: health payload, so hop 4 is measured on the backend and only on the backend.
BACKEND_REPOSITORY = "ghcr.io/nolte/kamerplanter-backend"

HEALTH_PATH = "/api/health"

#: Every outbound call carries this explicitly; an unbounded default would let a
#: black-holed instance hang the check instead of failing it.
HTTP_TIMEOUT_SECONDS = 30

#: A pin written minutes ago has not had time to roll out. Anchored on the
#: expected image's ``created``, the same one-sided bound hop 3 uses.
DEFAULT_GRACE_HOURS = 24.0

#: Enough samples to notice a split Service without tripping the endpoint's
#: ``60/minute`` per-IP limit (``settings.rate_limit_health``).
DEFAULT_SAMPLES = 3

REVISION_ANNOTATION = "org.opencontainers.image.revision"
CREATED_ANNOTATION = "org.opencontainers.image.created"

#: The build-arg/env pair in ``src/backend/Dockerfile`` that carries (b).
BUILD_REVISION_ENV = "BUILD_REVISION"

#: The setting that decides whether the instance discloses (b) at all.
DISCLOSURE_SETTING = "HEALTH_EXPOSE_BUILD_REVISION"

#: The one word no build can produce, so "I do not know which build this is"
#: cannot be mistaken for an answer.
UNKNOWN_BUILD_REVISION = "unknown"

#: ``<channel>@sha256:<64 hex>`` — the shape check_chart_image_digests.py enforces.
PINNED_TAG_RE = re.compile(r"^(?P<channel>[\w][\w.\-]*)@(?P<digest>sha256:[0-9a-f]{64})$")

DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

#: Compared in full, always. See the module docstring.
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")

#: Recognises an abbreviated SHA *only* to say so in the error message. Nothing
#: downstream ever compares against it.
ABBREVIATED_SHA_RE = re.compile(r"^[0-9a-f]{7,39}$")

MANIFEST_ACCEPT = ", ".join(
    [
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.docker.distribution.manifest.v2+json",
    ]
)

VERDICT_MATCH = "match"
VERDICT_WITHIN_GRACE = "within_grace"
VERDICT_ROLLING = "rolling"
VERDICT_DRIFT = "drift"

EXIT_OK = 0
EXIT_UNDETERMINED = 1
EXIT_USAGE = 2
EXIT_DRIFT = 3

#: ``urllib.request.urlopen``-shaped; the single injection seam for every read.
Opener = Callable[..., Any]


class DeployedBuildError(RuntimeError):
    """A condition under which the verdict could not be determined — fail loud."""


class BuildRevisionNotDisclosedError(DeployedBuildError):
    """The instance answered but carries no ``build_revision`` key.

    Deliberately its own type: this says **nothing** about whether the
    deployment is current, and its message must not read like drift.
    """


class BuildRevisionUnknownError(DeployedBuildError):
    """The instance discloses ``"unknown"`` — willing to answer, nothing to say."""


@dataclass(frozen=True)
class ExpectedBuild:
    """The build the deployment's chart version pins.

    Attributes:
        repository: Fully qualified image repository.
        digest: The pinned image digest, content-addressed and immutable.
        channel: The label in front of the ``@`` in the chart's ``tag``.
        revision: ``org.opencontainers.image.revision``, a full 40-char SHA.
        created: ``org.opencontainers.image.created``, the grace-window anchor.
        stamped: Whether the image bakes ``BUILD_REVISION`` into its config. When
            it does not, no deployment of these bytes could ever answer, which
            turns a baffling ``"unknown"`` from the instance into an actionable one.
    """

    repository: str
    digest: str
    channel: str
    revision: str
    created: datetime
    stamped: bool


@dataclass(frozen=True)
class Verdict:
    """The determined outcome and the sentence that explains it."""

    name: str
    headline: str
    detail: str = ""

    @property
    def is_alert(self) -> bool:
        """Whether this verdict is the incident hop 4 exists to surface."""
        return self.name == VERDICT_DRIFT


class Registry:
    """The slice of the OCI distribution API this check speaks.

    One instance per repository path, because the pull token is scoped per
    repository. Every request carries an explicit timeout.
    """

    def __init__(self, path: str, *, open_url: Opener = urllib.request.urlopen) -> None:
        """Bind the reader to one repository.

        Args:
            path: Repository path without the registry host, e.g.
                ``nolte/kamerplanter-backend``.
            open_url: Injection seam for ``urllib.request.urlopen``.
        """
        self.path = path
        self._open_url = open_url
        self._token: str | None = None

    def token(self) -> str:
        """Exchange a pull token, reusing it for the life of this reader.

        Anonymous reads suffice for the public packages; the CI/PAT token is
        basic-authed in when present so this keeps working for a private one —
        the same exchange ``scripts/ci/pin_chart_image_digests.sh`` performs.

        Returns:
            The bearer token for ``self.path``.

        Raises:
            DeployedBuildError: When the exchange fails or returns nothing.
        """
        if self._token is not None:
            return self._token
        url = f"https://{REGISTRY_HOST}/token?scope=repository:{self.path}:pull&service={REGISTRY_HOST}"
        request = urllib.request.Request(url)
        gh_token = os.environ.get("GHCR_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if gh_token:
            basic = base64.b64encode(f"x-access-token:{gh_token}".encode()).decode()
            request.add_header("Authorization", f"Basic {basic}")
        try:
            with self._open_url(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                token = json.load(response).get("token", "")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise DeployedBuildError(f"pull-token exchange failed for {self.path}: {exc}") from exc
        if not token:
            raise DeployedBuildError(f"registry returned no pull token for {self.path}")
        self._token = token
        return token

    def manifest(self, reference: str) -> dict:
        """Fetch a manifest, index or chart manifest by tag or digest.

        Args:
            reference: A tag or a ``sha256:`` digest.

        Returns:
            The decoded manifest.

        Raises:
            DeployedBuildError: On any transport, status or decode failure.
        """
        url = f"https://{REGISTRY_HOST}/v2/{self.path}/manifests/{urllib.parse.quote(reference, safe=':')}"
        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bearer {self.token()}")
        request.add_header("Accept", MANIFEST_ACCEPT)
        try:
            with self._open_url(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            raise DeployedBuildError(f"{self.path}:{reference} manifest request failed: HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise DeployedBuildError(f"{self.path}:{reference} manifest request failed: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise DeployedBuildError(f"{self.path}:{reference} manifest is not JSON: {exc}") from exc

    def blob(self, digest: str) -> bytes:
        """Fetch a blob by digest, following the registry's CDN redirect.

        Args:
            digest: The blob's ``sha256:`` digest.

        Returns:
            The raw blob bytes.

        Raises:
            DeployedBuildError: On any transport or status failure.
        """
        url = f"https://{REGISTRY_HOST}/v2/{self.path}/blobs/{digest}"
        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bearer {self.token()}")
        try:
            with self._open_url(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            raise DeployedBuildError(f"{self.path} blob {digest} failed: HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise DeployedBuildError(f"{self.path} blob {digest} unreadable: {exc}") from exc

    def blob_json(self, digest: str) -> dict:
        """Fetch a blob and decode it as JSON.

        Args:
            digest: The blob's ``sha256:`` digest.

        Returns:
            The decoded blob.

        Raises:
            DeployedBuildError: When the blob is unreadable or not JSON.
        """
        try:
            return json.loads(self.blob(digest))
        except json.JSONDecodeError as exc:
            raise DeployedBuildError(f"{self.path} config blob {digest} is not JSON: {exc}") from exc


def parse_timestamp(value: str) -> datetime:
    """Parse an RFC3339 timestamp into an aware UTC datetime.

    Args:
        value: The timestamp as the registry writes it.

    Returns:
        A timezone-aware datetime.

    Raises:
        DeployedBuildError: When the value cannot be parsed.
    """
    normalised = value.replace("Z", "+00:00")
    # Defend against >6 fractional digits, which fromisoformat rejects and GHCR
    # emits (measured: "2026-08-18T21:39:13.986017119Z", nine digits).
    normalised = re.sub(r"(\.\d{6})\d+", r"\1", normalised)
    try:
        parsed = datetime.fromisoformat(normalised)
    except ValueError as exc:
        raise DeployedBuildError(f"unparseable timestamp {value!r}: {exc}") from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _platform_manifest(index: dict) -> dict | None:
    """Pick the real platform entry from an image index.

    buildx attaches an attestation manifest with ``platform: unknown/unknown``;
    selecting it would read a config blob that carries no image metadata at all.

    Args:
        index: A decoded image index.

    Returns:
        The chosen platform entry, or None when the argument is not an index.
    """
    entries = index.get("manifests")
    if not entries:
        return None
    concrete = [
        entry
        for entry in entries
        if entry.get("platform", {}).get("os") not in (None, "unknown")
        and entry.get("platform", {}).get("architecture") not in (None, "unknown")
    ]
    if not concrete:
        raise DeployedBuildError("image index carries no usable platform manifest")
    return next(
        (
            entry
            for entry in concrete
            if entry["platform"].get("os") == "linux" and entry["platform"].get("architecture") == "amd64"
        ),
        concrete[0],
    )


def _image_config(registry: Registry, manifest: dict) -> dict:
    """Descend index -> platform manifest -> config blob.

    Args:
        registry: Reader bound to the image's repository.
        manifest: The manifest fetched for the pinned digest.

    Returns:
        The decoded image config blob.

    Raises:
        DeployedBuildError: When no config digest can be reached.
    """
    chosen = _platform_manifest(manifest)
    if chosen is not None:
        return _image_config(registry, registry.manifest(chosen["digest"]))
    config_digest = manifest.get("config", {}).get("digest")
    if not config_digest:
        raise DeployedBuildError(f"{registry.path}: image manifest has no config digest")
    return registry.blob_json(config_digest)


def _stamped_revision(config: dict) -> str | None:
    """Read ``BUILD_REVISION`` out of an image config's baked environment.

    This is the value the *running process* will report, read from the bytes
    rather than from the annotation beside them — so a build that annotated a
    revision but forgot the build-arg is visible as such.

    Args:
        config: A decoded image config blob.

    Returns:
        The baked value, or None when the image bakes none.
    """
    for entry in config.get("config", {}).get("Env", []) or []:
        name, separator, value = str(entry).partition("=")
        if separator and name == BUILD_REVISION_ENV:
            return value.strip()
    return None


def read_expected_build(registry: Registry, repository: str, channel: str, digest: str) -> ExpectedBuild:
    """Resolve what the pinned image says about itself.

    Args:
        registry: Reader bound to *repository*.
        repository: Fully qualified image repository.
        channel: The chart pin's channel label.
        digest: The pinned, content-addressed digest.

    Returns:
        The resolved expected build.

    Raises:
        DeployedBuildError: When the image carries no revision annotation, no
            ``created`` timestamp, a revision that is not a full SHA, or two
            self-descriptions that disagree.
    """
    manifest = registry.manifest(digest)
    annotations = manifest.get("annotations") or {}
    config = _image_config(registry, manifest)

    revision = str(annotations.get(REVISION_ANNOTATION) or "").strip()
    if not revision:
        raise DeployedBuildError(
            f"{repository}@{digest} carries no {REVISION_ANNOTATION} annotation, so there is nothing "
            "to compare the instance against. A build published without docker/metadata-action's "
            "revision label cannot be checked this way."
        )
    if not FULL_SHA_RE.match(revision):
        raise DeployedBuildError(
            f"{repository}@{digest} annotates {REVISION_ANNOTATION}={revision!r}, which is not a full "
            "40-character SHA. This check compares in full and has no truncation rule."
        )

    created_raw = str(annotations.get(CREATED_ANNOTATION) or config.get("created") or "")
    if not created_raw:
        raise DeployedBuildError(
            f"{repository}@{digest} carries no {CREATED_ANNOTATION} and its config has no `created` — "
            "the grace window has no anchor, so the verdict is undetermined rather than assumed."
        )

    baked = _stamped_revision(config)
    if baked and baked != revision:
        # Two descriptions of the same bytes disagreeing is not a small thing:
        # it means the annotation and the running process would report different
        # commits, and the comparison below would be against the wrong one.
        raise DeployedBuildError(
            f"{repository}@{digest} describes itself two ways: {REVISION_ANNOTATION}={revision} but "
            f"{BUILD_REVISION_ENV}={baked}. The image cannot be used as a reference until they agree."
        )

    return ExpectedBuild(
        repository=repository,
        digest=digest,
        channel=channel,
        revision=revision,
        created=parse_timestamp(created_raw),
        stamped=bool(baked),
    )


def chart_backend_pin(registry: Registry, version: str) -> tuple[str, str, str]:
    """Read the backend image pin out of a published chart version.

    The chart layer is a gzipped tar; it is read into memory and only its
    ``values.yaml`` is parsed. Nothing is written to disk and nothing is
    extracted by a path the archive controls.

    Args:
        registry: Reader bound to :data:`CHART_REPOSITORY`.
        version: The chart version the deployment targets.

    Returns:
        ``(chart_manifest_digest, channel, image_digest)``. The chart manifest
        digest is returned so the report pins the measurement exactly.

    Raises:
        DeployedBuildError: When the chart, its layer, its ``values.yaml`` or the
            backend pin inside it cannot be resolved unambiguously.
    """
    manifest = registry.manifest(version)
    layers = manifest.get("layers") or []
    if len(layers) != 1:
        raise DeployedBuildError(
            f"chart {CHART_REPOSITORY}:{version} has {len(layers)} layer(s); a Helm chart artefact has "
            "exactly one, so this is not a chart this check can read."
        )
    chart_digest = str(layers[0].get("digest") or "")
    if not DIGEST_RE.match(chart_digest):
        raise DeployedBuildError(f"chart {CHART_REPOSITORY}:{version} layer has no usable digest")

    try:
        raw = gzip.decompress(registry.blob(chart_digest))
    except (OSError, EOFError) as exc:
        raise DeployedBuildError(f"chart {CHART_REPOSITORY}:{version} layer is not gzip: {exc}") from exc

    values_text: str | None = None
    try:
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            for member in archive:
                # Exactly the top-level values.yaml — never a subchart's, which
                # would silently answer a different question.
                if not member.isfile() or member.name.count("/") != 1 or not member.name.endswith("/values.yaml"):
                    continue
                handle = archive.extractfile(member)
                if handle is None:  # pragma: no cover — isfile() already excludes this
                    continue
                values_text = handle.read().decode("utf-8")
                break
    except (tarfile.TarError, UnicodeDecodeError) as exc:
        raise DeployedBuildError(f"chart {CHART_REPOSITORY}:{version} archive is unreadable: {exc}") from exc

    if values_text is None:
        raise DeployedBuildError(f"chart {CHART_REPOSITORY}:{version} contains no top-level values.yaml")

    try:
        values = yaml.safe_load(values_text)
    except yaml.YAMLError as exc:
        raise DeployedBuildError(f"chart {CHART_REPOSITORY}:{version} values.yaml is not valid YAML: {exc}") from exc

    pins = sorted({tag for tag in _backend_tags(values)})
    if not pins:
        raise DeployedBuildError(
            f"chart {CHART_REPOSITORY}:{version} pins no {BACKEND_REPOSITORY} image — refusing to report "
            "a verdict against nothing."
        )
    if len(pins) > 1:
        raise DeployedBuildError(
            f"chart {CHART_REPOSITORY}:{version} pins {BACKEND_REPOSITORY} to {len(pins)} different tags "
            f"({', '.join(pins)}); there is no single expected build to compare against."
        )

    match = PINNED_TAG_RE.match(pins[0])
    if not match:
        raise DeployedBuildError(
            f"chart {CHART_REPOSITORY}:{version} pins {BACKEND_REPOSITORY} as {pins[0]!r}, which is not "
            "`<channel>@sha256:<digest>`. An unpinned deployment cannot be checked this way."
        )
    return chart_digest, match.group("channel"), match.group("digest")


def _backend_tags(node: Any) -> list[str]:
    """Collect every ``tag`` sitting beside a backend ``repository``.

    Walks the whole values tree rather than hard-coding controller paths: the
    backend image appears under three controllers (backend, celery-worker,
    celery-beat) and a fourth would otherwise be missed silently.

    Args:
        node: Any node of the parsed values document.

    Returns:
        Every tag string found beside a backend repository.
    """
    found: list[str] = []
    if isinstance(node, dict):
        if node.get("repository") == BACKEND_REPOSITORY and isinstance(node.get("tag"), str):
            found.append(node["tag"])
        for value in node.values():
            found.extend(_backend_tags(value))
    elif isinstance(node, list):
        for value in node:
            found.extend(_backend_tags(value))
    return found


def health_url(instance_url: str) -> str:
    """Build the health URL for an instance base URL.

    Args:
        instance_url: Base URL of the deployed instance.

    Returns:
        The absolute health endpoint URL.

    Raises:
        DeployedBuildError: When the value is empty or not an http(s) URL, so a
            misconfiguration is reported as itself rather than as a confusing
            connection error later.
    """
    candidate = instance_url.strip()
    if not candidate:
        raise DeployedBuildError("no instance URL given — there is nothing to ask")
    parsed = urllib.parse.urlsplit(candidate)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise DeployedBuildError(f"instance URL {instance_url!r} is not an absolute http(s) URL (e.g. https://host)")
    return f"{candidate.rstrip('/')}{HEALTH_PATH}"


def read_instance_revision(instance_url: str, *, open_url: Opener = urllib.request.urlopen) -> str:
    """Ask the running instance which build it serves.

    Args:
        instance_url: Base URL of the deployed instance.
        open_url: Injection seam for ``urllib.request.urlopen``.

    Returns:
        The full 40-character git SHA the instance reports.

    Raises:
        BuildRevisionNotDisclosedError: When the payload carries no
            ``build_revision`` key. This says nothing about whether the
            deployment is current.
        BuildRevisionUnknownError: When the instance discloses ``"unknown"``.
        DeployedBuildError: When the instance is unreachable, does not answer
            with a Kamerplanter health payload, or reports a revision that
            cannot be compared in full.
    """
    url = health_url(instance_url)
    request = urllib.request.Request(url)
    request.add_header("Accept", "application/json")
    try:
        with open_url(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        raise DeployedBuildError(f"{url} answered HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise DeployedBuildError(f"{url} is unreachable: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise DeployedBuildError(f"{url} did not answer with JSON: {exc}") from exc

    if not isinstance(payload, dict) or "status" not in payload:
        raise DeployedBuildError(
            f"{url} did not answer with a Kamerplanter health payload (no `status` field) — the "
            "configured URL probably does not point at this application"
        )

    if "build_revision" not in payload:
        raise BuildRevisionNotDisclosedError(
            f"{url} answered, but discloses no build_revision — the instance runs with "
            f"{DISCLOSURE_SETTING} off. This is NOT drift: the deployment may be perfectly current, "
            "and nothing here says otherwise. This check simply cannot run against that instance. "
            f"Set {DISCLOSURE_SETTING}=true on it — helm/kamerplanter/values.yaml now carries that as "
            "a chart default, so an instance deployed from a chart released after 2026-09-01 discloses "
            "it without further action; an older chart, a docker-compose deployment or an explicit "
            "override needs the variable set — or stop running this check against that instance."
        )

    raw = payload.get("build_revision")
    if not isinstance(raw, str):
        raise DeployedBuildError(f"{url} reported a non-string build_revision: {raw!r}")
    revision = raw.strip()

    if revision == UNKNOWN_BUILD_REVISION:
        raise BuildRevisionUnknownError(
            f'{url} discloses build_revision "{UNKNOWN_BUILD_REVISION}" — the instance is willing to '
            "say which build it runs, but no build stamped one in (a dev image, or an image built "
            f"without the {BUILD_REVISION_ENV} build-arg). The measurement is undetermined."
        )
    if not FULL_SHA_RE.match(revision):
        detail = (
            "an abbreviated revision, which cannot be compared against the image annotation without a "
            "truncation rule this check deliberately does not have"
            if ABBREVIATED_SHA_RE.match(revision)
            else "neither a git SHA nor the documented fallback"
        )
        raise DeployedBuildError(f"{url} reported build_revision {revision!r}: {detail}.")
    return revision


def sample_instance_revisions(
    instance_url: str,
    *,
    samples: int,
    open_url: Opener = urllib.request.urlopen,
) -> list[str]:
    """Read the instance several times so a split Service is visible.

    A Deployment mid-rollout serves old and new pods behind one Service, and a
    single read samples whichever replica was picked. Every sample must succeed:
    a partial read would narrow the observed set for a reason unrelated to the
    deployment, which is the shape that turns an undetermined check into a
    confident wrong one.

    Args:
        instance_url: Base URL of the deployed instance.
        samples: How many reads to take; at least one.
        open_url: Injection seam for ``urllib.request.urlopen``.

    Returns:
        The revisions observed, in the order they were read.

    Raises:
        DeployedBuildError: Propagated from any single read.
    """
    if samples < 1:
        raise DeployedBuildError(f"--samples must be at least 1, got {samples}")
    return [read_instance_revision(instance_url, open_url=open_url) for _ in range(samples)]


def decide(expected: ExpectedBuild, observed: list[str], *, now: datetime, grace_hours: float) -> Verdict:
    """Turn the expected build and what the instance served into one verdict.

    Args:
        expected: The build the chart version pins.
        observed: Revisions read from the instance, in read order.
        now: Measurement time.
        grace_hours: How long after the expected image was built a mismatch is
            still an in-progress rollout rather than an alert.

    Returns:
        The verdict.

    Raises:
        DeployedBuildError: When *observed* is empty — a verdict on no
            observation would be a clean result reported against nothing.
    """
    if not observed:
        raise DeployedBuildError("no revision was read from the instance; refusing to decide on nothing")

    distinct = sorted(set(observed))
    age_hours = (now - expected.created).total_seconds() / 3600.0

    if distinct == [expected.revision]:
        return Verdict(
            VERDICT_MATCH,
            f"the instance serves {expected.revision}, which is what chart pin {expected.digest} is.",
        )

    if expected.revision in distinct:
        # A split Service is the shape of a rollout — but only for as long as a
        # rollout plausibly takes. Beyond the grace window a Deployment that is
        # STILL half-rolled is not in progress, it is stuck, and the replicas
        # that never rolled are drift. Letting `rolling` swallow that would give
        # the check a permanent blind spot in exactly the failure it exists to
        # catch: a partial hop-4 failure would report "not an alert" forever.
        if age_hours < grace_hours:
            return Verdict(
                VERDICT_ROLLING,
                f"{len(distinct)} different builds answered across {len(observed)} sample(s); "
                f"{expected.revision} is among them.",
                "Some replicas already serve the expected build and others do not — the shape of a "
                f"rollout in progress. Observed: {', '.join(distinct)}. The expected image is "
                f"{age_hours:.1f}h old (< {grace_hours:.0f}h), so this is not yet alertable; re-run "
                "once the rollout settles.",
            )
        return Verdict(
            VERDICT_DRIFT,
            f"the instance is still split {age_hours / 24:.1f} day(s) after {expected.revision} was "
            f"built: {', '.join(distinct)} all answered.",
            "A rollout does not take this long. Some replicas serve the expected build and some serve "
            "an older one, which is hop 4 failing on part of the Deployment — a stuck ReplicaSet or a "
            "pod that never rescheduled. `kubectl get pods -o wide` plus the imageID of each pod names "
            "the ones that did not roll.",
        )

    if age_hours < grace_hours:
        return Verdict(
            VERDICT_WITHIN_GRACE,
            f"the instance serves {', '.join(distinct)} and not {expected.revision}, but the expected "
            f"image is {age_hours:.1f}h old (< {grace_hours:.0f}h).",
            "A pin written this recently has not had time to roll out; alerting on it would fire after every publish.",
        )

    return Verdict(
        VERDICT_DRIFT,
        f"the instance serves {', '.join(distinct)}; chart pin {expected.digest} is "
        f"{expected.revision}, built {age_hours / 24:.1f} day(s) ago.",
        "This is hop 4 failing: the chart pins a build the running instance does not serve. The grace "
        "window is anchored on the expected image's build time, which is an UPPER bound on how long the "
        "deployment has been behind — it cannot have been behind before the build existed.",
    )


def build_report(
    expected: ExpectedBuild,
    observed: list[str],
    verdict: Verdict,
    *,
    instance_url: str,
    chart_version: str | None,
    chart_digest: str | None,
    grace_hours: float,
    now: datetime,
) -> dict:
    """Assemble the machine-readable report.

    Args:
        expected: The build the chart version pins.
        observed: Revisions read from the instance.
        verdict: The determined verdict.
        instance_url: Base URL that was asked.
        chart_version: The chart version that named the expected build, or None
            when the digest was given directly.
        chart_digest: Manifest digest of that chart, so the measurement is
            reproducible from the report alone even for a moving channel tag.
        grace_hours: The window that was applied.
        now: Measurement time.

    Returns:
        The report, shaped like the sibling watchers' ``*-report.json``. ``chart``
        is ``null`` rather than a sentinel string when no chart named the
        expected build: a consumer must be able to tell "not applicable" from a
        value, which is the same three-answer discipline this check applies to
        the instance.
    """
    chart = (
        None
        if chart_version is None
        else {
            "repository": f"{REGISTRY_HOST}/{CHART_REPOSITORY}",
            "version": chart_version,
            "manifest_digest": chart_digest,
            "prerelease": "-" in chart_version,
        }
    )
    return {
        "verdict": verdict.name,
        "headline": verdict.headline,
        "detail": verdict.detail,
        "measured_at": now.isoformat(),
        "instance_url": instance_url,
        "instance_revisions": observed,
        "chart": chart,
        "expected": {
            "repository": expected.repository,
            "channel": expected.channel,
            "digest": expected.digest,
            "revision": expected.revision,
            "created": expected.created.isoformat(),
            "age_hours": round((now - expected.created).total_seconds() / 3600.0, 1),
            "stamped": expected.stamped,
        },
        "grace_hours": grace_hours,
    }


def _parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Returns:
        The parser. The expected-build source is a required, mutually exclusive
        group: there is no default, because a default operand is precisely how
        the predecessor came to compare production against the wrong channel.
    """
    parser = argparse.ArgumentParser(
        prog="check_deployed_build.py",
        description="Check whether a running instance serves the build its chart version pins (#1236).",
    )
    parser.add_argument(
        "--instance-url",
        required=True,
        help="Base URL of the deployed instance, e.g. https://kamerplanter.example.org",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--chart-version",
        help=(
            "Chart version the deployment targets (ArgoCD `targetRevision`). The backend image pin is "
            "read out of that published chart — the operand production actually deploys."
        ),
    )
    source.add_argument(
        "--image-digest",
        help=(
            f"A {BACKEND_REPOSITORY} digest to compare against directly, for a deployment that is not "
            "driven by a published chart version."
        ),
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=DEFAULT_SAMPLES,
        help=f"How many times to read the health endpoint (default {DEFAULT_SAMPLES}).",
    )
    parser.add_argument(
        "--grace-hours",
        type=float,
        default=DEFAULT_GRACE_HOURS,
        help=f"Grace window in hours, anchored on the expected image's build time (default {DEFAULT_GRACE_HOURS:.0f}).",
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        help="Write the report here. Written only when the verdict is determined.",
    )
    return parser


def main(
    argv: list[str] | None = None,
    *,
    open_url: Opener = urllib.request.urlopen,
    now: datetime | None = None,
) -> int:
    """Run the check and, on a determined verdict, write the report.

    Args:
        argv: Command line without the program name.
        open_url: Injection seam for every network read.
        now: Measurement time, defaulting to the current UTC time.

    Returns:
        :data:`EXIT_OK` for match/within_grace/rolling, :data:`EXIT_DRIFT` for
        the incident.

    Raises:
        DeployedBuildError: On anything that leaves the verdict undetermined.
    """
    args = _parser().parse_args(sys.argv[1:] if argv is None else argv)
    moment = now or datetime.now(UTC)

    # Validated before any network call so a bad URL is reported as itself.
    health_url(args.instance_url)

    backend = Registry(BACKEND_REPOSITORY[len(f"{REGISTRY_HOST}/") :], open_url=open_url)
    if args.chart_version:
        chart = Registry(CHART_REPOSITORY, open_url=open_url)
        chart_digest, channel, image_digest = chart_backend_pin(chart, args.chart_version)
        chart_version: str | None = args.chart_version
    else:
        if not DIGEST_RE.match(args.image_digest or ""):
            raise DeployedBuildError(f"--image-digest {args.image_digest!r} is not `sha256:<64 hex>`")
        # No chart named this build, so there is no channel label to report. The
        # empty string would read as "a channel called ''"; None reads as absent.
        chart_digest, channel, image_digest = None, "", args.image_digest
        chart_version = None

    # The expected build is resolved BEFORE the instance is read, so an
    # "unknown" from the instance can be explained rather than merely reported:
    # if the pinned bytes bake no revision either, no deployment of them could
    # have answered, which is the difference between an actionable red and a
    # baffling one.
    expected = read_expected_build(backend, BACKEND_REPOSITORY, channel, image_digest)

    try:
        observed = sample_instance_revisions(args.instance_url, samples=args.samples, open_url=open_url)
    except BuildRevisionUnknownError as exc:
        if not expected.stamped:
            raise BuildRevisionUnknownError(
                f"{exc} The expected image {image_digest} bakes no {BUILD_REVISION_ENV} either, so no "
                "deployment of those bytes can answer this yet — a stamped image has to be published "
                "and pinned first."
            ) from exc
        raise

    verdict = decide(expected, observed, now=moment, grace_hours=args.grace_hours)
    report = build_report(
        expected,
        observed,
        verdict,
        instance_url=args.instance_url,
        chart_version=chart_version,
        chart_digest=chart_digest,
        grace_hours=args.grace_hours,
        now=moment,
    )
    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)

    if args.chart_version and "-" in args.chart_version:
        print(
            f"note: {args.chart_version} is a pre-release chart channel, which is rewritten by every "
            f"helm/** merge. The measurement is pinned to chart manifest {chart_digest} in the report."
        )
    print(f"Expected: {expected.repository}@{expected.digest}")
    print(f"          revision {expected.revision}, built {expected.created.isoformat()}")
    print(f"Instance: {health_url(args.instance_url)} -> {', '.join(observed)}")
    print(f"Verdict:  {verdict.name} — {verdict.headline}")
    if verdict.detail:
        print(f"          {verdict.detail}")
    return EXIT_DRIFT if verdict.is_alert else EXIT_OK


def run(argv: list[str] | None = None, **kwargs: Any) -> int:
    """Wrap :func:`main` in the fail-loud contract.

    Args:
        argv: Command line without the program name.
        **kwargs: Forwarded to :func:`main`.

    Returns:
        :data:`EXIT_UNDETERMINED` when the verdict could not be determined —
        loud, and with no report written, so a consumer acting on the report
        cannot mistake an undetermined check for a clean one.
    """
    try:
        return main(argv, **kwargs)
    except DeployedBuildError as exc:
        print(f"::error::deployed build check could not be determined: {exc}", file=sys.stderr)
        return EXIT_UNDETERMINED
    except SystemExit as exc:  # argparse's own usage failure
        return EXIT_USAGE if exc.code not in (0, None) else EXIT_OK


if __name__ == "__main__":
    raise SystemExit(run())

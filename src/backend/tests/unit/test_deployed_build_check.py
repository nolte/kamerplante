"""Tests for the deployed-build check (``scripts/ci/check_deployed_build.py``).

**What this guards.** Hop 4 of the delivery chain — *does the running pod serve
the bytes its chart version pins?* — is the only hop nothing measured, and the
one the 2026-08-17 incident failed on while the hop-3 digest guard stayed green
and correct (#1236).

**The defect this file is shaped against.** An earlier, unreviewed version of
the script took its expected build from ``helm/kamerplanter/values.yaml`` — this
repository's ``develop`` channel — and compared it against production, which
tracks a *published chart version*. Measured on 2026-09-01 the two were
``sha256:e2b0aec4…`` (revision ``37cbc06f…``) and ``sha256:f1059661…`` (revision
``07502fd7…``): the check would have reported permanent "drift" for ordinary
release lag while hop 4 was in fact clean. :class:`TestTheOperandIsTheDeployedChart`
is the absence guard for that; it fails the moment the script learns to read the
repository chart again.

**What is under test.** The decision logic and the resolution paths, driven
against a constructed in-memory registry and health endpoint — never against
ghcr.io and never against a real instance. A test that reached either would
answer a question about today's deployment state rather than about the check,
and would go red on the next publish.

**The doubles are deliberately not more permissive than the real things.**
:class:`FakeRegistry` demands a bearer token on every ``/v2/`` request, 404s an
unknown tag or digest, carries the buildx attestation entry
(``platform: unknown/unknown``) that GHCR really serves so the platform filter is
exercised rather than assumed away, and serves the chart layer as **real gzip'd
tar bytes** so ``gzip``/``tarfile``/``yaml`` run for real. The recurring failure
in this repository is a double that accepts input the real thing rejects, which
turns a positive test into a certificate of nothing.

**Why here.** The script lives outside the backend package (it is a repository
tool, not application code), but ``pytest tests/unit/`` is the tier that runs in
CI, so the test lives here and loads the script by path. Traces to #1236 (no TC-ID: a repository
tool is not a user-facing case).
"""

from __future__ import annotations

import ast
import gzip
import hashlib
import importlib.util
import io
import json
import re
import sys
import tarfile
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tests.support.repo_scripts import find_repo_root

REGISTRY_HOST = "ghcr.io"
BACKEND_PATH = "nolte/kamerplanter-backend"
CHART_PATH = "nolte/charts/kamerplanter"
BACKEND_IMAGE = f"{REGISTRY_HOST}/{BACKEND_PATH}"

#: The 2026-09-01 measurement, in full. Both sides of the comparison are real
#: values read off ghcr.io, so the fixtures cannot drift into a shape the
#: registry never produces.
RELEASE_DIGEST = "sha256:f1059661be0fa6e8f258ed9c6a0b7f076c9e91f94ff8f39efec7da1d2aad801f"
RELEASE_REVISION = "07502fd7510dc32de2bbfdd6fd178ec2041e56a9"
RELEASE_CREATED = "2026-08-19T13:38:36.647Z"
DEVELOP_DIGEST = "sha256:e2b0aec41662febf6e5baa4dba29ddb1f5572bf5fa9feca9c244f255c2413c98"
DEVELOP_REVISION = "37cbc06fcf0c7d69c07f7abbd3d485cb241070da"

INSTANCE_URL = "https://instance.invalid"
HEALTH_URL = f"{INSTANCE_URL}/api/health"


def _load_script() -> ModuleType:
    """Execute ``scripts/ci/check_deployed_build.py`` and return it as a module.

    ``tests.support.repo_scripts.load_repo_script`` only reaches
    ``scripts/<stem>.py``; this one lives under ``scripts/ci/``. Its repo-root
    marker walk is reused rather than re-implemented, so a moved test file still
    finds the checkout.

    Returns:
        The executed module.
    """
    repo_root = find_repo_root(Path(__file__).resolve())
    if repo_root is None:  # pragma: no cover — only outside a full checkout
        pytest.skip("checkout root not found; scripts/ci/ is unreachable", allow_module_level=True)

    path = repo_root / "scripts" / "ci" / "check_deployed_build.py"
    if not path.is_file():  # pragma: no cover — only on a partial checkout
        pytest.skip(f"{path} does not exist", allow_module_level=True)

    spec = importlib.util.spec_from_file_location("_repo_script_check_deployed_build", path)
    if spec is None or spec.loader is None:  # pragma: no cover — defensive
        pytest.skip(f"{path} cannot be loaded as a Python module", allow_module_level=True)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


check = _load_script()


class _Response(io.BytesIO):
    """A urlopen-shaped response: a readable body plus response headers."""

    def __init__(self, body: bytes, headers: dict[str, str] | None = None) -> None:
        """Store the body and its headers.

        Args:
            body: The raw response body.
            headers: Response headers, if any.
        """
        super().__init__(body)
        self.headers = headers or {}


def _image_index(revision: str | None, created: str, *, config_digest: str = "sha256:" + "c" * 64) -> dict:
    """Build an OCI image index shaped like the ones GHCR serves.

    Args:
        revision: Value for the revision annotation; None omits it.
        created: Value for the created annotation.
        config_digest: Digest of the platform manifest's config blob.

    Returns:
        The index document.
    """
    annotations = {check.CREATED_ANNOTATION: created}
    if revision is not None:
        annotations[check.REVISION_ANNOTATION] = revision
    return {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.index.v1+json",
        "manifests": [
            {
                "mediaType": "application/vnd.oci.image.manifest.v1+json",
                "digest": "sha256:" + "9" * 64,
                "platform": {"architecture": "amd64", "os": "linux"},
            },
            # buildx attaches this; selecting it would read a config blob that
            # carries no image metadata at all.
            {
                "mediaType": "application/vnd.oci.image.manifest.v1+json",
                "digest": "sha256:" + "a" * 64,
                "platform": {"architecture": "unknown", "os": "unknown"},
            },
        ],
        "annotations": annotations,
        "_config_digest": config_digest,
    }


def _chart_values(tag: str | None, *, repository: str = BACKEND_IMAGE) -> dict:
    """Build a chart ``values.yaml`` document with the backend pinned three ways.

    Mirrors the real chart, where the backend image appears under three
    controllers (backend, celery-worker, celery-beat).

    Args:
        tag: The pinned tag; None omits the backend entirely.
        repository: The repository to pin it under.

    Returns:
        The values document.
    """
    if tag is None:
        return {"controllers": {"frontend": {"containers": {"main": {"image": {"repository": "x", "tag": "y"}}}}}}
    image = {"repository": repository, "tag": tag}
    return {
        "controllers": {
            name: {"containers": {"main": {"image": dict(image)}}}
            for name in ("backend", "celery-worker", "celery-beat")
        }
    }


def _chart_tarball(members: dict[str, str]) -> bytes:
    """Package *members* into the gzip'd tar a Helm chart artefact really is.

    Args:
        members: Archive path -> file contents.

    Returns:
        The gzip'd tar bytes.
    """
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name, content in members.items():
            payload = content.encode("utf-8")
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    return gzip.compress(buffer.getvalue())


class FakeRegistry:
    """The slice of the OCI distribution API the script speaks, in memory.

    Never looser than ghcr.io: an unauthenticated ``/v2/`` request, an unknown
    tag and an unknown digest are all refused here exactly as they are refused
    there.
    """

    def __init__(self) -> None:
        """Start empty; callers register exactly what a case needs."""
        self.manifests: dict[tuple[str, str], Any] = {}
        self.blobs: dict[tuple[str, str], bytes] = {}
        self.token_refused: set[str] = set()
        self.requested: list[str] = []

    def add_image(self, path: str, digest: str, index: dict, *, env: list[str] | None = None) -> None:
        """Register an image index and the config blob its platform manifest names.

        Args:
            path: Repository path.
            digest: Digest the index is addressable by.
            index: The index document, as :func:`_image_index` builds it.
            env: ``Env`` entries for the config blob, or None for none.
        """
        config_digest = index.pop("_config_digest", "sha256:" + "c" * 64)
        platform_digest = index["manifests"][0]["digest"]
        self.manifests[(path, digest)] = index
        self.manifests[(path, platform_digest)] = {
            "schemaVersion": 2,
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "config": {"digest": config_digest},
            "layers": [],
        }
        self.blobs[(path, config_digest)] = json.dumps(
            {"created": index["annotations"].get(check.CREATED_ANNOTATION), "config": {"Env": env or []}}
        ).encode()

    def add_chart(self, version: str, layers: list[bytes]) -> str:
        """Register a Helm chart artefact under *version*.

        Args:
            version: The chart version, used as the manifest tag.
            layers: Raw layer payloads; a real chart has exactly one.

        Returns:
            The digest of the first layer, i.e. what the report should pin.
        """
        entries = []
        for payload in layers:
            # Content-addressed, exactly as a registry stores a blob. Numbering
            # them by position instead made two different charts share one blob
            # digest — a shape no registry can produce, and one that silently
            # made a falsification test pass for the wrong reason.
            digest = f"sha256:{hashlib.sha256(payload).hexdigest()}"
            self.blobs[(CHART_PATH, digest)] = payload
            entries.append({"mediaType": "application/vnd.cncf.helm.chart.content.v1.tar+gzip", "digest": digest})
        self.manifests[(CHART_PATH, version)] = {
            "schemaVersion": 2,
            "config": {"mediaType": "application/vnd.cncf.helm.config.v1+json"},
            "layers": entries,
        }
        return entries[0]["digest"] if entries else ""

    def handle(self, request: urllib.request.Request) -> _Response:
        """Answer a registry request or raise the error ghcr.io would raise.

        Args:
            request: The prepared request.

        Returns:
            The response.

        Raises:
            urllib.error.HTTPError: For an unauthenticated or unknown reference.
        """
        url = request.full_url
        self.requested.append(url)

        token_match = re.match(rf"https://{REGISTRY_HOST}/token\?scope=repository:(?P<path>[^:]+):pull", url)
        if token_match:
            path = token_match.group("path")
            if path in self.token_refused:
                raise urllib.error.HTTPError(url, 403, "Forbidden", {}, None)  # type: ignore[arg-type]
            return _Response(json.dumps({"token": f"token-for-{path}"}).encode())

        if request.get_header("Authorization") is None:
            raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, None)  # type: ignore[arg-type]

        manifest_match = re.match(rf"https://{REGISTRY_HOST}/v2/(?P<path>.+)/manifests/(?P<ref>.+)$", url)
        if manifest_match:
            key = (manifest_match.group("path"), manifest_match.group("ref"))
            if key not in self.manifests:
                raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)  # type: ignore[arg-type]
            body = self.manifests[key]
            payload = body if isinstance(body, bytes) else json.dumps(body).encode()
            return _Response(payload, {"docker-content-digest": key[1]})

        blob_match = re.match(rf"https://{REGISTRY_HOST}/v2/(?P<path>.+)/blobs/(?P<digest>.+)$", url)
        if blob_match:
            key = (blob_match.group("path"), blob_match.group("digest"))
            if key not in self.blobs:
                raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)  # type: ignore[arg-type]
            return _Response(self.blobs[key])

        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)  # type: ignore[arg-type]


class FakeOpener:
    """One ``urlopen``-shaped seam covering both the registry and the instance.

    Every call must carry an explicit timeout — the script's own rule, asserted
    here so a regression to an unbounded default fails a test rather than
    hanging a run.
    """

    def __init__(self, registry: FakeRegistry, health: Any) -> None:
        """Bind the two far ends.

        Args:
            registry: The registry double.
            health: The health payload; a dict is served as JSON, a list is
                served one element per call (so a split Service can be modelled),
                an Exception is raised, and raw bytes are served verbatim.
        """
        self.registry = registry
        self.health = health
        self.health_calls = 0

    def __call__(self, request: urllib.request.Request, timeout: float | None = None) -> _Response:
        """Answer a request.

        Args:
            request: The prepared request.
            timeout: The caller's timeout; must be set.

        Returns:
            The response.

        Raises:
            AssertionError: When the caller omitted its timeout.
            Exception: Whatever the health double is configured to raise.
        """
        assert timeout is not None, f"{request.full_url} was requested without an explicit timeout"
        if request.full_url.startswith(INSTANCE_URL):
            payload = self.health
            if isinstance(payload, list):
                payload = payload[min(self.health_calls, len(payload) - 1)]
            self.health_calls += 1
            if isinstance(payload, Exception):
                raise payload
            if isinstance(payload, bytes):
                return _Response(payload)
            return _Response(json.dumps(payload).encode())
        return self.registry.handle(request)


def _healthy(revision: str | None = RELEASE_REVISION, *, disclose: bool = True) -> dict:
    """Build a health payload in one of the three answer classes.

    Args:
        revision: The disclosed revision, or None for the literal ``"unknown"``.
        disclose: When False, the key is absent entirely.

    Returns:
        The payload.
    """
    payload: dict[str, Any] = {"status": "healthy", "version": "1.0.0", "mode": "light", "supported_majors": [1]}
    if disclose:
        payload["build_revision"] = revision if revision is not None else check.UNKNOWN_BUILD_REVISION
    return payload


@pytest.fixture
def registry() -> FakeRegistry:
    """A registry carrying the released chart 0.2.1 and the build it pins."""
    fake = FakeRegistry()
    fake.add_image(
        BACKEND_PATH,
        RELEASE_DIGEST,
        _image_index(RELEASE_REVISION, RELEASE_CREATED),
        env=[f"{check.BUILD_REVISION_ENV}={RELEASE_REVISION}"],
    )
    fake.add_chart(
        "0.2.1",
        [_chart_tarball({"kamerplanter/values.yaml": json.dumps(_chart_values(f"0.2.1@{RELEASE_DIGEST}"))})],
    )
    return fake


def _run(
    registry: FakeRegistry,
    health: Any,
    *,
    argv: list[str] | None = None,
    now: datetime | None = None,
) -> tuple[int, FakeOpener]:
    """Invoke the script's fail-loud entry point.

    Args:
        registry: The registry double.
        health: The health double.
        argv: Command line; defaults to the released-chart invocation.
        now: Measurement time.

    Returns:
        ``(exit_code, opener)``.
    """
    opener = FakeOpener(registry, health)
    code = check.run(
        argv if argv is not None else ["--instance-url", INSTANCE_URL, "--chart-version", "0.2.1"],
        open_url=opener,
        now=now or datetime(2026, 9, 1, tzinfo=UTC),
    )
    return code, opener


class TestTheOperandIsTheDeployedChart:
    """The expected build comes from the chart named on the command line.

    This is the absence guard for the defect that made the predecessor wrong:
    reading ``helm/kamerplanter/values.yaml`` compares production against the
    ``develop`` channel it does not deploy, which is permanent false drift.
    """

    def test_the_script_reads_no_local_file_at_all(self) -> None:
        """The only ``open`` in the script writes the report.

        A substring scan for the chart path would be defeated by any rename;
        this is the property that actually matters and cannot be worked around:
        with no read of the filesystem, the expected build cannot come from the
        checkout — only from the chart version the caller named. It fails the
        moment someone adds a read, whatever they call the file.
        """
        repo_root = find_repo_root(Path(__file__).resolve())
        assert repo_root is not None
        source = (repo_root / "scripts" / "ci" / "check_deployed_build.py").read_text(encoding="utf-8")
        opens = [
            node
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open"
        ]
        modes = [argument.value for node in opens for argument in node.args[1:2] if isinstance(argument, ast.Constant)]
        assert len(opens) == 1, f"expected exactly one open(); found {len(opens)}"
        assert modes == ["w"], f"the only open() must be the report write, got mode {modes}"

    def test_there_is_no_default_expected_build(self) -> None:
        """Omitting both operand flags is a usage error, never a guess."""
        code, _ = _run(FakeRegistry(), _healthy(), argv=["--instance-url", INSTANCE_URL])
        assert code == check.EXIT_USAGE

    def test_the_pin_is_read_from_the_named_chart_version(self, registry: FakeRegistry) -> None:
        """The chart artefact is fetched by the version that was asked for."""
        code, opener = _run(registry, _healthy())
        assert code == check.EXIT_OK
        assert any(f"/v2/{CHART_PATH}/manifests/0.2.1" in url for url in opener.registry.requested)

    def test_a_different_chart_version_yields_a_different_expected_build(self, registry: FakeRegistry) -> None:
        """Two chart versions pinning two builds do not answer the same way.

        The falsification for the operand: were the expected build taken from
        anywhere but the named chart, both invocations would agree.
        """
        registry.add_image(BACKEND_PATH, DEVELOP_DIGEST, _image_index(DEVELOP_REVISION, RELEASE_CREATED))
        registry.add_chart(
            "0.2.0",
            [_chart_tarball({"kamerplanter/values.yaml": json.dumps(_chart_values(f"0.2.0@{DEVELOP_DIGEST}"))})],
        )
        released, _ = _run(registry, _healthy())
        older, _ = _run(registry, _healthy(), argv=["--instance-url", INSTANCE_URL, "--chart-version", "0.2.0"])
        assert (released, older) == (check.EXIT_OK, check.EXIT_DRIFT)


class TestTheInstanceHasThreeAnswers:
    """The three well-formed replies are three outcomes, never collapsed."""

    def test_a_full_sha_reaches_the_comparison(self, registry: FakeRegistry) -> None:
        """The only reply that produces a verdict."""
        assert check.read_instance_revision(INSTANCE_URL, open_url=FakeOpener(registry, _healthy())) == RELEASE_REVISION

    def test_an_absent_key_is_its_own_error_naming_the_setting(self, registry: FakeRegistry) -> None:
        """Not disclosed is not drift, and the message must not read like it."""
        with pytest.raises(check.BuildRevisionNotDisclosedError) as excinfo:
            check.read_instance_revision(INSTANCE_URL, open_url=FakeOpener(registry, _healthy(disclose=False)))
        message = str(excinfo.value)
        assert check.DISCLOSURE_SETTING in message
        assert "NOT drift" in message

    def test_unknown_is_a_different_error_from_an_absent_key(self, registry: FakeRegistry) -> None:
        """Willing to answer but unstamped is its own state."""
        with pytest.raises(check.BuildRevisionUnknownError):
            check.read_instance_revision(INSTANCE_URL, open_url=FakeOpener(registry, _healthy(None)))

    def test_the_two_undetermined_states_are_distinguishable_by_type(self) -> None:
        """Neither is a subclass of the other, so a caller cannot merge them."""
        assert not issubclass(check.BuildRevisionNotDisclosedError, check.BuildRevisionUnknownError)
        assert not issubclass(check.BuildRevisionUnknownError, check.BuildRevisionNotDisclosedError)

    def test_an_abbreviated_revision_is_refused_rather_than_truncated(self, registry: FakeRegistry) -> None:
        """There is deliberately no truncation rule anywhere."""
        with pytest.raises(check.DeployedBuildError, match="truncation rule"):
            check.read_instance_revision(INSTANCE_URL, open_url=FakeOpener(registry, _healthy(RELEASE_REVISION[:7])))

    def test_a_non_string_revision_is_refused(self, registry: FakeRegistry) -> None:
        """A JSON number where a SHA belongs is undetermined, not a comparison."""
        payload = _healthy()
        payload["build_revision"] = 12345
        with pytest.raises(check.DeployedBuildError, match="non-string"):
            check.read_instance_revision(INSTANCE_URL, open_url=FakeOpener(registry, payload))

    def test_a_reply_without_status_is_not_a_kamerplanter_instance(self, registry: FakeRegistry) -> None:
        """A wrong URL is reported as a wrong URL, not as a missing field."""
        with pytest.raises(check.DeployedBuildError, match="does not point at this application"):
            check.read_instance_revision(INSTANCE_URL, open_url=FakeOpener(registry, {"ok": True}))

    def test_a_non_json_reply_is_refused(self, registry: FakeRegistry) -> None:
        """An HTML error page must not parse into a clean result."""
        with pytest.raises(check.DeployedBuildError, match="did not answer with JSON"):
            check.read_instance_revision(INSTANCE_URL, open_url=FakeOpener(registry, b"<html>nope</html>"))

    @pytest.mark.parametrize("suffix", ["", "/", "///"])
    def test_the_health_url_is_built_from_the_base_url(self, suffix: str) -> None:
        """Trailing slashes must not produce a double-slashed path."""
        assert check.health_url(f"{INSTANCE_URL}{suffix}") == HEALTH_URL

    @pytest.mark.parametrize("value", ["", "   ", "instance.invalid", "ftp://instance.invalid", "/api"])
    def test_a_url_that_is_not_absolute_http_is_refused(self, value: str) -> None:
        """A misconfiguration is reported as itself, before any network call."""
        with pytest.raises(check.DeployedBuildError):
            check.health_url(value)


class TestSamplingASplitService:
    """A Deployment mid-rollout answers differently per replica."""

    def test_agreeing_samples_are_one_observation(self, registry: FakeRegistry) -> None:
        """Three identical reads collapse to the ordinary comparison."""
        code, opener = _run(registry, _healthy())
        assert code == check.EXIT_OK
        assert opener.health_calls == check.DEFAULT_SAMPLES

    def test_a_split_service_that_includes_the_expected_build_is_rolling(self, registry: FakeRegistry) -> None:
        """Some replicas rolled and some did not — determined, and not an alert.

        The expected image is 2h old here, well inside the grace window, which
        is what makes a split a rollout rather than a fault.
        """
        health = [_healthy(DEVELOP_REVISION), _healthy(RELEASE_REVISION), _healthy(DEVELOP_REVISION)]
        code, _ = _run(
            registry,
            health,
            now=datetime(2026, 8, 19, 15, 38, 36, 647000, tzinfo=UTC),
        )
        assert code == check.EXIT_OK

    def test_a_split_that_outlives_the_grace_window_is_drift(self, registry: FakeRegistry) -> None:
        """A rollout does not take a day; a still-split Service is stuck.

        Without this escalation ``rolling`` would swallow a partial hop-4
        failure forever — the check would report "not an alert" for a
        Deployment whose stuck replicas serve an old build indefinitely, which
        is a permanent blind spot in the failure it exists to catch.
        """
        health = [_healthy(DEVELOP_REVISION), _healthy(RELEASE_REVISION), _healthy(DEVELOP_REVISION)]
        code, _ = _run(registry, health)
        assert code == check.EXIT_DRIFT

    def test_a_split_service_serving_only_stale_builds_is_drift(self, registry: FakeRegistry) -> None:
        """Two wrong answers are not less wrong than one."""
        other = "b" * 40
        health = [_healthy(DEVELOP_REVISION), _healthy(other), _healthy(DEVELOP_REVISION)]
        code, _ = _run(registry, health)
        assert code == check.EXIT_DRIFT

    def test_a_single_failing_sample_makes_the_whole_run_undetermined(self, registry: FakeRegistry) -> None:
        """A partial read would narrow the observed set for an unrelated reason.

        That is the shape that turns an undetermined check into a confident
        wrong one, so every sample must succeed.
        """
        health = [_healthy(RELEASE_REVISION), urllib.error.URLError("connection reset")]
        code, _ = _run(registry, health)
        assert code == check.EXIT_UNDETERMINED

    def test_zero_samples_is_refused(self) -> None:
        """A verdict on no observation would be a clean result against nothing."""
        with pytest.raises(check.DeployedBuildError, match="at least 1"):
            check.sample_instance_revisions(INSTANCE_URL, samples=0, open_url=FakeOpener(FakeRegistry(), _healthy()))

    def test_the_sample_count_is_configurable(self, registry: FakeRegistry) -> None:
        """``--samples`` reaches the reader."""
        _, opener = _run(
            registry,
            _healthy(),
            argv=["--instance-url", INSTANCE_URL, "--chart-version", "0.2.1", "--samples", "5"],
        )
        assert opener.health_calls == 5


class TestDecide:
    """The verdict boundaries, driven directly."""

    @staticmethod
    def _expected(created: datetime) -> Any:
        """Build an expected build created at *created*."""
        return check.ExpectedBuild(
            repository=BACKEND_IMAGE,
            digest=RELEASE_DIGEST,
            channel="0.2.1",
            revision=RELEASE_REVISION,
            created=created,
            stamped=True,
        )

    def test_equal_revisions_close_the_chain(self) -> None:
        """The instance serves the pinned build."""
        now = datetime(2026, 9, 1, tzinfo=UTC)
        verdict = check.decide(self._expected(now - timedelta(days=9)), [RELEASE_REVISION], now=now, grace_hours=24)
        assert (verdict.name, verdict.is_alert) == (check.VERDICT_MATCH, False)

    def test_a_mismatch_inside_the_window_is_not_alerted(self) -> None:
        """A pin written hours ago has not had time to roll out."""
        now = datetime(2026, 9, 1, tzinfo=UTC)
        verdict = check.decide(self._expected(now - timedelta(hours=2)), [DEVELOP_REVISION], now=now, grace_hours=24)
        assert (verdict.name, verdict.is_alert) == (check.VERDICT_WITHIN_GRACE, False)

    def test_the_boundary_belongs_to_drift(self) -> None:
        """Exactly at the window the grace is spent — the guard alerts early, never late."""
        now = datetime(2026, 9, 1, tzinfo=UTC)
        verdict = check.decide(self._expected(now - timedelta(hours=24)), [DEVELOP_REVISION], now=now, grace_hours=24)
        assert verdict.name == check.VERDICT_DRIFT

    def test_the_drift_verdict_names_both_revisions_in_full(self) -> None:
        """Neither side is abbreviated in the operator-facing sentence."""
        now = datetime(2026, 9, 1, tzinfo=UTC)
        verdict = check.decide(self._expected(now - timedelta(days=9)), [DEVELOP_REVISION], now=now, grace_hours=24)
        assert RELEASE_REVISION in verdict.headline
        assert DEVELOP_REVISION in verdict.headline

    def test_a_widened_window_suppresses_the_alert(self) -> None:
        """``--grace-hours`` reaches the decision."""
        now = datetime(2026, 9, 1, tzinfo=UTC)
        expected = self._expected(now - timedelta(days=9))
        assert check.decide(expected, [DEVELOP_REVISION], now=now, grace_hours=24 * 30).name == (
            check.VERDICT_WITHIN_GRACE
        )

    def test_deciding_on_no_observation_is_refused(self) -> None:
        """Refusing beats reporting clean against nothing."""
        now = datetime(2026, 9, 1, tzinfo=UTC)
        with pytest.raises(check.DeployedBuildError, match="nothing"):
            check.decide(self._expected(now), [], now=now, grace_hours=24)


class TestExpectedBuildResolution:
    """What the pinned image says about itself, and when it is unusable."""

    def test_the_revision_and_creation_time_come_off_the_index(self, registry: FakeRegistry) -> None:
        """The annotations GHCR really writes are the ones that are read."""
        reader = check.Registry(BACKEND_PATH, open_url=FakeOpener(registry, _healthy()))
        expected = check.read_expected_build(reader, BACKEND_IMAGE, "0.2.1", RELEASE_DIGEST)
        assert (expected.revision, expected.stamped) == (RELEASE_REVISION, True)
        assert expected.created == datetime(2026, 8, 19, 13, 38, 36, 647000, tzinfo=UTC)

    def test_an_unstamped_image_is_detected_as_such(self) -> None:
        """A build that annotated a revision but baked none is a real state.

        Measured on 2026-09-01: ``sha256:e2b0aec4…`` annotates
        ``37cbc06f…`` and carries no ``BUILD_REVISION`` in its config at all.
        """
        fake = FakeRegistry()
        fake.add_image(BACKEND_PATH, DEVELOP_DIGEST, _image_index(DEVELOP_REVISION, RELEASE_CREATED), env=[])
        reader = check.Registry(BACKEND_PATH, open_url=FakeOpener(fake, _healthy()))
        assert check.read_expected_build(reader, BACKEND_IMAGE, "develop", DEVELOP_DIGEST).stamped is False

    def test_an_image_that_contradicts_itself_is_refused(self) -> None:
        """Annotation and baked env naming different commits is not usable."""
        fake = FakeRegistry()
        fake.add_image(
            BACKEND_PATH,
            RELEASE_DIGEST,
            _image_index(RELEASE_REVISION, RELEASE_CREATED),
            env=[f"{check.BUILD_REVISION_ENV}={DEVELOP_REVISION}"],
        )
        reader = check.Registry(BACKEND_PATH, open_url=FakeOpener(fake, _healthy()))
        with pytest.raises(check.DeployedBuildError, match="two ways"):
            check.read_expected_build(reader, BACKEND_IMAGE, "0.2.1", RELEASE_DIGEST)

    def test_a_missing_revision_annotation_is_refused(self) -> None:
        """There is nothing to compare against, so there is no verdict."""
        fake = FakeRegistry()
        fake.add_image(BACKEND_PATH, RELEASE_DIGEST, _image_index(None, RELEASE_CREATED))
        reader = check.Registry(BACKEND_PATH, open_url=FakeOpener(fake, _healthy()))
        with pytest.raises(check.DeployedBuildError, match="no org.opencontainers.image.revision"):
            check.read_expected_build(reader, BACKEND_IMAGE, "0.2.1", RELEASE_DIGEST)

    def test_an_abbreviated_annotation_is_refused(self) -> None:
        """The no-truncation rule binds the registry side too."""
        fake = FakeRegistry()
        fake.add_image(BACKEND_PATH, RELEASE_DIGEST, _image_index(RELEASE_REVISION[:12], RELEASE_CREATED))
        reader = check.Registry(BACKEND_PATH, open_url=FakeOpener(fake, _healthy()))
        with pytest.raises(check.DeployedBuildError, match="not a full"):
            check.read_expected_build(reader, BACKEND_IMAGE, "0.2.1", RELEASE_DIGEST)

    def test_an_index_without_a_concrete_platform_is_refused(self) -> None:
        """An index carrying only the attestation entry has no image to read."""
        fake = FakeRegistry()
        index = _image_index(RELEASE_REVISION, RELEASE_CREATED)
        index["manifests"] = [index["manifests"][1]]
        fake.manifests[(BACKEND_PATH, RELEASE_DIGEST)] = index
        reader = check.Registry(BACKEND_PATH, open_url=FakeOpener(fake, _healthy()))
        with pytest.raises(check.DeployedBuildError, match="no usable platform manifest"):
            check.read_expected_build(reader, BACKEND_IMAGE, "0.2.1", RELEASE_DIGEST)

    def test_nine_fractional_digits_parse(self) -> None:
        """GHCR really emits them; ``fromisoformat`` really rejects them."""
        assert check.parse_timestamp("2026-08-18T21:39:13.986017119Z") == datetime(
            2026, 8, 18, 21, 39, 13, 986017, tzinfo=UTC
        )

    def test_a_naive_timestamp_is_read_as_utc(self) -> None:
        """A missing offset must not produce a naive datetime downstream."""
        assert check.parse_timestamp("2026-08-18T21:39:13").tzinfo is not None

    def test_an_unparseable_timestamp_is_refused(self) -> None:
        """The grace window has no anchor, so the verdict is undetermined."""
        with pytest.raises(check.DeployedBuildError, match="unparseable timestamp"):
            check.parse_timestamp("last Tuesday")


class TestChartResolution:
    """Reading the backend pin out of a published chart artefact."""

    def test_the_pin_and_the_layer_digest_are_returned(self, registry: FakeRegistry) -> None:
        """The layer digest is what pins the measurement in the report."""
        reader = check.Registry(CHART_PATH, open_url=FakeOpener(registry, _healthy()))
        chart_digest, channel, image_digest = check.chart_backend_pin(reader, "0.2.1")
        assert (channel, image_digest) == ("0.2.1", RELEASE_DIGEST)
        assert re.match(r"^sha256:[0-9a-f]{64}$", chart_digest)

    def test_a_chart_pinning_no_backend_is_refused(self) -> None:
        """Refusing beats reporting a verdict against nothing."""
        fake = FakeRegistry()
        fake.add_chart("9.9.9", [_chart_tarball({"kamerplanter/values.yaml": json.dumps(_chart_values(None))})])
        reader = check.Registry(CHART_PATH, open_url=FakeOpener(fake, _healthy()))
        with pytest.raises(check.DeployedBuildError, match="pins no"):
            check.chart_backend_pin(reader, "9.9.9")

    def test_a_backend_pinned_at_two_different_builds_is_refused(self) -> None:
        """There is no single expected build, so there is no comparison."""
        fake = FakeRegistry()
        values = _chart_values(f"0.2.1@{RELEASE_DIGEST}")
        values["controllers"]["celery-beat"]["containers"]["main"]["image"]["tag"] = f"0.2.1@{DEVELOP_DIGEST}"
        fake.add_chart("9.9.9", [_chart_tarball({"kamerplanter/values.yaml": json.dumps(values)})])
        reader = check.Registry(CHART_PATH, open_url=FakeOpener(fake, _healthy()))
        with pytest.raises(check.DeployedBuildError, match="different tags"):
            check.chart_backend_pin(reader, "9.9.9")

    def test_an_unpinned_backend_tag_is_refused(self) -> None:
        """A floating tag cannot identify the bytes a pod should be running."""
        fake = FakeRegistry()
        fake.add_chart("9.9.9", [_chart_tarball({"kamerplanter/values.yaml": json.dumps(_chart_values("latest"))})])
        reader = check.Registry(CHART_PATH, open_url=FakeOpener(fake, _healthy()))
        with pytest.raises(check.DeployedBuildError, match="not\n?.*`<channel>@sha256"):
            check.chart_backend_pin(reader, "9.9.9")

    def test_a_subcharts_values_file_is_not_mistaken_for_the_charts_own(self) -> None:
        """``charts/common/values.yaml`` answers a different question entirely."""
        fake = FakeRegistry()
        members = {
            "kamerplanter/charts/common/values.yaml": json.dumps(_chart_values(f"0.2.1@{DEVELOP_DIGEST}")),
            "kamerplanter/values.yaml": json.dumps(_chart_values(f"0.2.1@{RELEASE_DIGEST}")),
        }
        fake.add_chart("9.9.9", [_chart_tarball(members)])
        reader = check.Registry(CHART_PATH, open_url=FakeOpener(fake, _healthy()))
        assert check.chart_backend_pin(reader, "9.9.9")[2] == RELEASE_DIGEST

    def test_a_chart_without_a_values_file_is_refused(self) -> None:
        """An artefact this check cannot read is undetermined, not clean."""
        fake = FakeRegistry()
        fake.add_chart("9.9.9", [_chart_tarball({"kamerplanter/Chart.yaml": "name: kamerplanter"})])
        reader = check.Registry(CHART_PATH, open_url=FakeOpener(fake, _healthy()))
        with pytest.raises(check.DeployedBuildError, match="no top-level values.yaml"):
            check.chart_backend_pin(reader, "9.9.9")

    def test_a_multi_layer_artefact_is_refused(self) -> None:
        """A Helm chart has exactly one layer; anything else is not one."""
        fake = FakeRegistry()
        payload = _chart_tarball({"kamerplanter/values.yaml": json.dumps(_chart_values(f"0.2.1@{RELEASE_DIGEST}"))})
        fake.add_chart("9.9.9", [payload, payload])
        reader = check.Registry(CHART_PATH, open_url=FakeOpener(fake, _healthy()))
        with pytest.raises(check.DeployedBuildError, match="layer"):
            check.chart_backend_pin(reader, "9.9.9")

    def test_a_layer_that_is_not_gzip_is_refused(self) -> None:
        """Garbage must raise, not decode into a plausible-looking answer."""
        fake = FakeRegistry()
        fake.add_chart("9.9.9", [b"not gzip at all"])
        reader = check.Registry(CHART_PATH, open_url=FakeOpener(fake, _healthy()))
        with pytest.raises(check.DeployedBuildError, match="not gzip"):
            check.chart_backend_pin(reader, "9.9.9")

    def test_an_unknown_chart_version_is_refused(self, registry: FakeRegistry) -> None:
        """The registry 404s it, exactly as ghcr.io would."""
        reader = check.Registry(CHART_PATH, open_url=FakeOpener(registry, _healthy()))
        with pytest.raises(check.DeployedBuildError, match="HTTP 404"):
            check.chart_backend_pin(reader, "0.0.0")


class TestFailLoudNeverWritesAReport:
    """Undetermined is loud, and leaves no artefact a consumer could misread."""

    @pytest.mark.parametrize(
        ("health", "argv_tail"),
        [
            pytest.param(_healthy(disclose=False), None, id="not-disclosed"),
            pytest.param(_healthy(None), None, id="unknown"),
            pytest.param(_healthy(RELEASE_REVISION[:8]), None, id="abbreviated"),
            pytest.param(urllib.error.URLError("no route to host"), None, id="unreachable"),
            pytest.param({"ok": True}, None, id="not-a-kamerplanter-instance"),
            pytest.param(_healthy(), ["--chart-version", "0.0.0"], id="unknown-chart-version"),
        ],
    )
    def test_no_report_is_written(
        self,
        registry: FakeRegistry,
        tmp_path: Path,
        health: Any,
        argv_tail: list[str] | None,
    ) -> None:
        """Every undetermined path exits loud and writes nothing."""
        report = tmp_path / "report.json"
        argv = ["--instance-url", INSTANCE_URL, *(argv_tail or ["--chart-version", "0.2.1"]), "--json", str(report)]
        code, _ = _run(registry, health, argv=argv)
        assert code == check.EXIT_UNDETERMINED
        assert not report.exists()

    def test_a_refused_pull_token_is_undetermined(self, registry: FakeRegistry, tmp_path: Path) -> None:
        """A registry blip must not read as a clean deployment."""
        registry.token_refused.add(CHART_PATH)
        report = tmp_path / "report.json"
        code, _ = _run(
            registry,
            _healthy(),
            argv=["--instance-url", INSTANCE_URL, "--chart-version", "0.2.1", "--json", str(report)],
        )
        assert code == check.EXIT_UNDETERMINED
        assert not report.exists()

    def test_a_malformed_image_digest_is_undetermined(self, registry: FakeRegistry) -> None:
        """``--image-digest`` is validated before any network call."""
        code, _ = _run(registry, _healthy(), argv=["--instance-url", INSTANCE_URL, "--image-digest", "sha256:nope"])
        assert code == check.EXIT_UNDETERMINED

    def test_unknown_from_an_instance_running_unstamped_bytes_explains_itself(self, tmp_path: Path) -> None:
        """A baffling red becomes an actionable one.

        When the expected image bakes no revision either, no deployment of those
        bytes could have answered — which is a different instruction to the
        operator than "your instance is misconfigured".
        """
        fake = FakeRegistry()
        fake.add_image(BACKEND_PATH, DEVELOP_DIGEST, _image_index(DEVELOP_REVISION, RELEASE_CREATED), env=[])
        fake.add_chart(
            "0.1.0",
            [_chart_tarball({"kamerplanter/values.yaml": json.dumps(_chart_values(f"0.1.0@{DEVELOP_DIGEST}"))})],
        )
        opener = FakeOpener(fake, _healthy(None))
        with pytest.raises(check.BuildRevisionUnknownError, match="bakes no BUILD_REVISION either"):
            check.main(
                ["--instance-url", INSTANCE_URL, "--chart-version", "0.1.0"],
                open_url=opener,
                now=datetime(2026, 9, 1, tzinfo=UTC),
            )


class TestDeterminedRunsWriteTheReport:
    """A determined verdict leaves a machine-readable artefact."""

    def test_a_match_writes_a_non_alerting_report(self, registry: FakeRegistry, tmp_path: Path) -> None:
        """Exit 0, verdict ``match``, chart block populated."""
        report = tmp_path / "report.json"
        code, _ = _run(
            registry,
            _healthy(),
            argv=["--instance-url", INSTANCE_URL, "--chart-version", "0.2.1", "--json", str(report)],
        )
        assert code == check.EXIT_OK
        payload = json.loads(report.read_text(encoding="utf-8"))
        assert payload["verdict"] == check.VERDICT_MATCH
        assert payload["chart"]["version"] == "0.2.1"
        assert payload["expected"]["revision"] == RELEASE_REVISION
        assert payload["instance_revisions"] == [RELEASE_REVISION] * check.DEFAULT_SAMPLES

    def test_a_drift_report_carries_both_sides_and_exits_three(self, registry: FakeRegistry, tmp_path: Path) -> None:
        """The exit code is the alert; there is no workflow to carry one."""
        report = tmp_path / "report.json"
        code, _ = _run(
            registry,
            _healthy(DEVELOP_REVISION),
            argv=["--instance-url", INSTANCE_URL, "--chart-version", "0.2.1", "--json", str(report)],
        )
        assert code == check.EXIT_DRIFT
        payload = json.loads(report.read_text(encoding="utf-8"))
        assert payload["verdict"] == check.VERDICT_DRIFT
        assert payload["expected"]["revision"] == RELEASE_REVISION
        assert payload["instance_revisions"] == [DEVELOP_REVISION] * check.DEFAULT_SAMPLES

    def test_the_direct_digest_mode_reports_a_null_chart(self, registry: FakeRegistry, tmp_path: Path) -> None:
        """ "Not applicable" must be distinguishable from a value.

        The same three-answer discipline the check applies to the instance: a
        sentinel string like ``"(none)"`` would read as a chart version.
        """
        report = tmp_path / "report.json"
        code, _ = _run(
            registry,
            _healthy(),
            argv=["--instance-url", INSTANCE_URL, "--image-digest", RELEASE_DIGEST, "--json", str(report)],
        )
        assert code == check.EXIT_OK
        assert json.loads(report.read_text(encoding="utf-8"))["chart"] is None

    def test_a_prerelease_chart_version_is_flagged_in_the_report(self, tmp_path: Path) -> None:
        """``0.2.1-dev`` is rewritten by every helm merge, so it is not immutable."""
        fake = FakeRegistry()
        fake.add_image(
            BACKEND_PATH,
            RELEASE_DIGEST,
            _image_index(RELEASE_REVISION, RELEASE_CREATED),
            env=[f"{check.BUILD_REVISION_ENV}={RELEASE_REVISION}"],
        )
        fake.add_chart(
            "0.2.1-dev",
            [_chart_tarball({"kamerplanter/values.yaml": json.dumps(_chart_values(f"develop@{RELEASE_DIGEST}"))})],
        )
        report = tmp_path / "report.json"
        code, _ = _run(
            fake,
            _healthy(),
            argv=["--instance-url", INSTANCE_URL, "--chart-version", "0.2.1-dev", "--json", str(report)],
        )
        assert code == check.EXIT_OK
        chart = json.loads(report.read_text(encoding="utf-8"))["chart"]
        assert chart["prerelease"] is True
        # The manifest digest is what makes a moving tag's measurement reproducible.
        assert re.match(r"^sha256:[0-9a-f]{64}$", chart["manifest_digest"])

    def test_omitting_the_json_flag_writes_nothing(self, registry: FakeRegistry, tmp_path: Path) -> None:
        """The report is opt-in; the check must not litter the working directory."""
        code, _ = _run(registry, _healthy())
        assert code == check.EXIT_OK
        assert list(tmp_path.iterdir()) == []

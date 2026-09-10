"""The build identity is wired from the CI build to the endpoint — and nowhere else (#1210).

Structural tests. The "unit" is the *chain* that carries a git SHA from a GitHub
Actions build into `GET /api/health`, so the collaborators are the source texts
of the three files that make up that chain, read once and parsed — no Docker
daemon, no network, no running app.

Why structural rather than behavioural
--------------------------------------
The behavioural test would be "build the image, run it, curl the endpoint". That
needs a Docker build in the unit tier, and it is precisely the test that would
*not* have caught this class of defect anyway: every link here fails **silently
and green**. Drop the `build-args:` line and the image builds fine, starts fine,
serves fine — and reports `"unknown"` forever. Move the `ARG` above the pip layer
and every build still works, just slower. Nothing goes red on its own, which is
why the chain is pinned link by link.

The falsification these tests are built for
-------------------------------------------
Criterion 7 of the work package: *reverting only the `build-args:` line in
`docker-publish.yml` must make the endpoint stop reporting the real SHA.*
`TestTheWorkflowPassesTheRevisionIn` fails on exactly that edit, and on nothing
else. Its counterpart `TestTheDockerfileAcceptsTheRevision` fails if the image
stops accepting the value. Together they establish the property no runtime test
in this repository can: that the SHA comes from the *build*, not from a default
that would look identical in every assertion made against a running process.

The third class, `TestTheRevisionDoesNotLeakIntoTheContractVersion`, is an
absence guard over `app/main.py`. `settings.app_version` has six consumers — the
Sentry release, the startup log, the mDNS advertisement, `FastAPI(version=…)`,
the health payload and the Celery worker's release. Four of those are unreachable
from a TestClient (they run at import time or inside the lifespan), so "the build
SHA did not leak into the mDNS advertisement" is not checkable at runtime here.
It is checkable in the source, and that is what the AST scan does.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
import yaml

from tests.support.repo_scripts import find_repo_root

_EXPECTED_BUILD_ARG = "BUILD_REVISION=${{ github.sha }}"


def _repo_root() -> Path:
    """Locate the checkout root, failing loudly rather than skipping.

    A marker walk rather than ``parents[N]``: a hard-coded index silently breaks
    the moment this file moves, which has bitten this repository before. A *skip*
    would be worse than either — this module is the falsification lever for the
    whole feature, and a lever that quietly declines to pull is the vacuous green
    the project's own quality gate refuses to produce.
    """
    root = find_repo_root(Path(__file__).resolve())
    assert root is not None, "checkout root not found (no ancestor holds both Taskfile.yaml and scripts/)"
    return root


def _dockerfile_stages() -> dict[str, list[str]]:
    """Split ``src/backend/Dockerfile`` into stage name -> stripped instruction lines."""
    text = (_repo_root() / "src" / "backend" / "Dockerfile").read_text(encoding="utf-8")
    stages: dict[str, list[str]] = {}
    current: str | None = None
    for raw in text.splitlines():
        line = raw.strip()
        match = re.match(r"FROM\s+\S+(?:\s+AS\s+(\S+))?\s*$", line, re.IGNORECASE)
        if match:
            current = (match.group(1) or "").lower() or None
            if current is not None:
                stages[current] = []
            continue
        if current is not None:
            stages[current].append(line)
    return stages


def _index_of(lines: list[str], predicate) -> int:
    """Return the index of the first matching line, or -1."""
    for index, line in enumerate(lines):
        if predicate(line):
            return index
    return -1


def _backend_build_step() -> dict:
    """Return the `docker/build-push-action` step of the `build-backend` job."""
    workflow = _repo_root() / ".github" / "workflows" / "docker-publish.yml"
    document = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    job = document["jobs"]["build-backend"]
    steps = [step for step in job["steps"] if str(step.get("uses", "")).startswith("docker/build-push-action")]
    assert len(steps) == 1, f"expected exactly one build-push-action step in build-backend, found {len(steps)}"
    return steps[0]


def _main_module_ast() -> tuple[ast.Module, str]:
    source = (_repo_root() / "src" / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    return ast.parse(source), source


def _calls_to(tree: ast.Module, name: str) -> list[ast.Call]:
    calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        called = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else None
        if called == name:
            calls.append(node)
    return calls


def _keyword(call: ast.Call, name: str) -> str:
    for keyword in call.keywords:
        if keyword.arg == name:
            return ast.unparse(keyword.value)
    raise AssertionError(f"call has no `{name}=` keyword: {ast.unparse(call)[:120]}")


class TestTheDockerfileAcceptsTheRevision:
    """The image must be able to receive a revision, and default to none."""

    def test_the_prod_stage_declares_the_build_arg(self) -> None:
        prod = _dockerfile_stages()["prod"]

        assert _index_of(prod, lambda line: line.startswith("ARG BUILD_REVISION")) != -1, (
            "the prod stage declares no ARG BUILD_REVISION, so `--build-arg BUILD_REVISION=…` "
            "is silently ignored and the image can never identify itself"
        )

    def test_the_build_arg_becomes_an_environment_variable(self) -> None:
        """An `ARG` alone is build-time only — the process needs an `ENV`.

        This is the easiest link to get wrong and the hardest to notice: the build
        accepts the argument, uses it for nothing, and the running container has
        no such variable.
        """
        prod = _dockerfile_stages()["prod"]
        env_lines = [line for line in prod if line.startswith("ENV BUILD_REVISION")]

        assert env_lines, "ARG BUILD_REVISION is never promoted to an ENV; the running process cannot read it"
        assert "${BUILD_REVISION}" in env_lines[0] or "$BUILD_REVISION" in env_lines[0], (
            f"ENV BUILD_REVISION does not reference the ARG: {env_lines[0]!r}"
        )

    def test_the_default_is_empty_not_a_placeholder(self) -> None:
        """An unbaked build must produce `""` — which `Settings` maps to "unknown".

        A default of `"unknown"`, `"dev"` or a stale SHA here would put a value in
        the payload that no annotation matches, which is worse than no value.
        """
        prod = _dockerfile_stages()["prod"]
        arg_line = prod[_index_of(prod, lambda line: line.startswith("ARG BUILD_REVISION"))]

        assert arg_line in ('ARG BUILD_REVISION=""', "ARG BUILD_REVISION=''", "ARG BUILD_REVISION="), (
            f"the ARG default must be empty so an unbaked image reports 'unknown', got {arg_line!r}"
        )

    def test_the_revision_layer_sits_below_the_expensive_ones(self) -> None:
        """Cache placement, asserted because it costs real build minutes.

        The revision changes on *every commit*. Anything below it is rebuilt every
        time, so the `ARG`/`ENV` pair must come after the hash-verified `uv sync`
        and after `COPY . .` — the two layers whose cache is worth keeping.
        """
        prod = _dockerfile_stages()["prod"]
        pip_install = _index_of(prod, lambda line: line.startswith("RUN uv sync"))
        copy_source = _index_of(prod, lambda line: re.match(r"COPY\s+\.\s+\.\s*$", line) is not None)
        arg_revision = _index_of(prod, lambda line: line.startswith("ARG BUILD_REVISION"))

        assert pip_install != -1, "no `RUN uv sync` found in the prod stage — has the stage been restructured?"
        assert copy_source != -1, "no `COPY . .` found in the prod stage — has the stage been restructured?"
        assert arg_revision > pip_install, "ARG BUILD_REVISION above the uv sync layer invalidates it on every commit"
        assert arg_revision > copy_source, "ARG BUILD_REVISION above `COPY . .` invalidates it on every commit"

    def test_the_dev_target_gets_no_revision(self) -> None:
        """Skaffold's dev image is built from working-tree state, not a commit.

        Stamping it would attach a SHA to an image that does not correspond to it.
        The dev target reporting "unknown" is the correct answer, not a gap.
        """
        dev = _dockerfile_stages()["dev"]

        assert _index_of(dev, lambda line: "BUILD_REVISION" in line) == -1, (
            "the dev stage stamps a build revision, but a hot-reloaded image does not correspond to any commit"
        )


class TestTheWorkflowPassesTheRevisionIn:
    """The falsification lever: without this, the endpoint reports "unknown"."""

    def test_the_backend_build_passes_build_args(self) -> None:
        step = _backend_build_step()

        assert "build-args" in step.get("with", {}), (
            "the backend image is built without `build-args:`, so BUILD_REVISION keeps its empty "
            "default and /api/health reports 'unknown' on every published image — the exact defect #1210 closes"
        )

    def test_the_revision_is_the_commit_sha_of_the_build(self) -> None:
        """`github.sha`, not a tag, not a short SHA, not a hand-maintained value.

        It has to be the same expression docker/metadata-action writes into
        `org.opencontainers.image.revision`, or the endpoint and the image
        annotation would disagree and the comparison the operator makes would need
        a truncation rule to work.
        """
        declared = str(_backend_build_step()["with"]["build-args"])
        build_args = [line.strip() for line in declared.splitlines() if line.strip()]

        assert _EXPECTED_BUILD_ARG in build_args, (
            f"expected {_EXPECTED_BUILD_ARG!r} among the backend build-args, got {build_args!r}"
        )

    def test_the_image_still_carries_the_matching_annotation(self) -> None:
        """The endpoint's value is only useful if something to compare it to ships.

        docker/metadata-action emits `org.opencontainers.image.revision` from the
        same `github.sha`. This pins that the annotation lane still exists, so a
        comparison of `/api/health` against `docker inspect` stays possible.
        """
        step = _backend_build_step()

        assert "annotations" in step.get("with", {}), (
            "the backend image no longer carries OCI annotations, so there is nothing to compare /api/health against"
        )


class TestTheRevisionDoesNotLeakIntoTheContractVersion:
    """`app_version` has six consumers; exactly none of them may become the SHA."""

    def test_the_revision_is_read_only_by_the_health_endpoint(self) -> None:
        """An absence guard: `main.py` touches the new setting in one place only.

        Four of `app_version`'s consumers — the Sentry release, the startup log,
        the mDNS advertisement and `FastAPI(version=…)` — run at import time or
        inside the lifespan and are therefore invisible to a TestClient. A leak
        into any of them would pass every runtime assertion in this change set.

        When this fails, the fix is *not* to widen the allowance. It is to ask why
        a build identity is being written into something that describes the API
        contract.
        """
        tree, _ = _main_module_ast()
        health = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == "root_health"
        )

        references = [
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
            and node.attr in {"build_revision", "resolve_build_revision"}
            and isinstance(node.value, ast.Name)
            and node.value.id == "settings"
        ]

        assert references, "app/main.py reads no build revision at all — the health payload has lost it"
        assert health.end_lineno is not None
        outside = [line for line in references if not (health.lineno <= line <= health.end_lineno)]
        assert not outside, (
            f"app/main.py reads the build revision outside root_health() at line(s) {outside}; "
            "the build identity must not reach the OpenAPI version, the mDNS advertisement, "
            "the Sentry release or the startup log"
        )

    def test_the_fastapi_application_version_is_the_app_version(self) -> None:
        """`info.version` in the published OpenAPI document, pinned at the source."""
        tree, _ = _main_module_ast()
        fastapi_calls = _calls_to(tree, "FastAPI")

        assert fastapi_calls, "no FastAPI(...) construction found in app/main.py"
        assert _keyword(fastapi_calls[0], "version") == "settings.app_version"

    def test_the_mdns_advertisement_is_the_app_version(self) -> None:
        """The one `app_version` consumer with no runtime test at all.

        `create_service_info` is called inside the lifespan and only when mDNS is
        enabled, so nothing in the suite exercises it. Home Assistant discovers the
        instance through this record; a SHA in its `version` field would break
        clients that compare it against an API version.
        """
        tree, _ = _main_module_ast()
        service_info_calls = _calls_to(tree, "create_service_info")

        assert service_info_calls, "no create_service_info(...) call found in app/main.py"
        assert _keyword(service_info_calls[0], "version") == "settings.app_version"


def test_the_settings_field_and_the_dockerfile_agree_on_the_variable_name() -> None:
    """The two halves of the contract are written in different languages.

    `Settings` derives `BUILD_REVISION` from the field name (`env_prefix: ""`);
    the Dockerfile writes the variable literally. Nothing but this test holds them
    together, and a mismatch is invisible — the endpoint just says "unknown".
    """
    from app.config.settings import Settings

    assert "build_revision" in Settings.model_fields
    prod = _dockerfile_stages()["prod"]
    assert any(line.startswith("ENV BUILD_REVISION") for line in prod), (
        "the field is named build_revision (=> $BUILD_REVISION), but the Dockerfile sets no such variable"
    )


@pytest.mark.parametrize("stage", ["dev", "prod"])
def test_both_image_stages_still_exist(stage: str) -> None:
    """Guards the parsing above: a renamed stage would make every assertion in
    this module vacuous by looking up a key that is no longer there."""
    assert stage in _dockerfile_stages()

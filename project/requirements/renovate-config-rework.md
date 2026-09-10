# Requirements — Renovate config rework: uv lock, cross-manager grouping, no develop-side digest transport

<!--
Produced via the `requirements-elicit` skill, following
spec/project/requirements-elicitation/ (authoritative source at
claude-shared/spec/project/requirements-elicitation/en.md).
`c_d` is an uncertainty proxy (self-consistency-derived), not a calibrated
probability. A requirement is `confirmed` only after an explicit teach-back
or an authoritative operator answer.
-->

- **Working copy / branch:** `chore/renovate-config-rework` (off `origin/develop` @ `ed68f01ff`),
  plan at `.resume/renovate-config-rework/plan.md`
- **Trigger:** three Renovate defects that looked green for weeks — a manager that
  silently extracted nothing (`pip-compile`, dashboard #12 shows `⚠️ WARN: pip-compile error`),
  a package rule that could never fire (`python minor/patch`), and an automerge that
  structurally arrived too late (`kamerplanter images`, #1326 open since 2026-09-01)
- **Governing constraints:** NFR-009 §2.3 / §6.1 (pyproject.toml is the single source of
  truth, lock is hash-pinned, source and lock move in one PR), NFR-018 §1 (a check that
  cannot fail must not exist), NFR-003 (source, commits, PR in English), CLAUDE.md
  (docs in German with EN mirror)

## Bounded context

- **What:** Rework the repository's dependency automation so that (P2) the backend
  lock is regenerated again by Renovate — by migrating the backend from
  pip-compile'd `requirements*.txt` to a committed `uv.lock` — (P1) one third-party
  image lands in ONE pull request regardless of which manager or file references
  it, and (P3) the Renovate-driven digest write-back of Kamerplanter's own chart
  images on `develop` is removed rather than repaired.
- **For whom:** the operator merging Renovate PRs; the `backend.yml` lock-staleness
  and CVE-audit lanes; the release job that pins the chart; ArgoCD, which consumes
  only released chart versions.
- **Explicitly out of scope:** readability/structure of `renovate.json5`; the four
  held pins (jsdom<30, TS<7 stay; pip<26.2 and click<8.5 become void with uv and are
  removed for that reason, not re-decided); the four side services'
  (`inference`, `knowledge`, `embedding`, `reranker`) plain `requirements.txt`
  (follow-up issue); the inherited `gh-plumbing` preset (`config:base` alias is a
  gh-plumbing concern); the missing plan-stub seeding in `scripts/worktree_add.sh`
  (follow-up issue).

## Understanding KPI

- Thresholds: `τ_low = 0.4`, `τ_high = 0.8`, self-consistency `k = 2`, question
  budget = `4` turns — the spec defaults, matching the precedent in
  `ci-actionlint-shellcheck.md`. The requirement arrived **code-grounded**: every
  factual claim below was measured before the interview (Renovate source
  `lib/modules/manager/pip-compile/common.ts`, `pep621/processors/uv.ts`,
  `lib/modules/manager/index.ts`, dashboard #12, the ArgoCD application in
  `k8s-home-lab`, `docs/de/deployment/ci-cd.md`), so specification uncertainty was
  concentrated in four decisions.
- `U_gate = min_d c_d` over required dimensions = **0.82**
- Termination: `saturation` at the teach-back turn (turn 4 of 4). Every
  decision-bearing question was answered; no positive-EVPI question remained.

### Gap matrix

| Dimension | Applicable | `c_d` | Uncertainty source | Evidence event |
|---|---|---|---|---|
| `functional` | yes | 0.90 | specification→resolved | Operator chose "full uv.lock migration" over the two header-trimming variants (turn 1), `uv sync --locked` in the image and `rangeStrategy: update-lockfile` (turn 2), "abolish develop-side pins" and "one group per image, no automerge" (turn 3); teach-back R1–R7 confirmed verbatim (turn 4) |
| `non_functional` | yes | 0.85 | interpretation | Hash-pinned installs (NFR-009 §2.3) carried over to `uv.lock`; reproducibility goal of #1303 carried by `[tool.uv].no-build-isolation-package` — self-consistency `k = 2`: both sketches (uv in image vs. `uv export`→pip) satisfy NFR-009; operator picked the first |
| `constraints` | yes | 0.88 | interpretation | Measured: Renovate's pip-compile allowlist forbids `--no-build-isolation` under both commands; only `constraints.python/pipTools/uv` exist (no pip/click); pep621 supports `uv.lock` with `uv lock --upgrade-package`; lookup applies `update-lockfile` when `lockedVersion` exists |
| `domain_objects` | yes | 0.92 | interpretation | Enumerated from source: 12 consumers of `requirements*.txt`, 6 third-party images across 3 managers (dashboard #12), 8 first-party image references in `values.yaml`, the freshness lane and its two scripts |
| `actors` | yes | 0.90 | interpretation | Renovate (Mend hosted app), the operator, `backend.yml` lanes, `docker-publish.yml` release job, ArgoCD at `targetRevision: 0.2.1` (OCI chart) |
| `acceptance_criteria` | yes | 0.85 | specification→resolved | R7 proof path chosen by the operator at teach-back; each AC below is falsifiable by a named command or a named Renovate PR |
| `edge_cases` | yes | 0.82 | interpretation | Enumerated below (Python 3.14 in Renovate's uv sidecar, hash verification of `uv.lock`, `poetry` manager still scanning the backend pyproject, `static` gate currently requiring digest pins on develop) |
| `scope_boundaries` | yes | 0.90 | specification→resolved | Bounded context confirmed at teach-back including the side-service and worktree-stub exclusions and the "one PR" packaging |

## Requirements

- **R1** — WHEN a backend dependency is added, bumped or removed in
  `src/backend/pyproject.toml`, the repository SHALL carry the resolved,
  hash-bearing lock in `src/backend/uv.lock`, generated by `uv lock`
  (`task deps:compile`), and `task deps:check` (`uv lock --check`) SHALL fail when
  the committed lock is stale; `backend.yml` "Lock staleness" SHALL run that task.
  `requirements.txt`, `requirements-dev.txt`, `.github/pip-tools-requirements.txt`,
  `task deps:toolchain` and the `pip<26.2` / `click<8.5` Renovate holds SHALL be
  removed. The dev extra stays `[project.optional-dependencies].dev`.
  - _dimension_: `functional` · _status_: `confirmed` · _source_: turn 1 "Voll auf uv.lock umstellen"; teach-back R1
- **R2** — WHEN the backend image is built, the Dockerfile SHALL obtain the uv
  binary via a digest-pinned `COPY --from=ghcr.io/astral-sh/uv:<x.y.z>@sha256:…`
  (tracked by Renovate's dockerfile manager) and install with `uv sync --locked`
  (prod without the dev extra, dev with it); pip-audit, pip-licenses, api-docs,
  release-publish and coverage lanes SHALL keep running, fed from the uv
  environment or `uv export`.
  - _dimension_: `functional` · _status_: `confirmed` · _source_: turn 2 "uv im Image, uv sync --locked"; teach-back R2
- **R3** — WHEN Renovate scans `src/backend/**`, the `pep621` manager (uv lock
  support) SHALL own `pyproject.toml` + `uv.lock`; `poetry`, `pip_requirements` and
  `pip-compile` SHALL be disabled there; `rangeStrategy: 'update-lockfile'` SHALL
  apply so in-range minor/patch updates move `uv.lock` without touching the
  pyproject ranges; `constraints.uv` SHALL equal `[tool.uv].required-version`. The
  groups `python minor/patch`, `python fastapi-stack`, `python major` SHALL be
  retargeted to `pep621` and SHALL demonstrably fire.
  - _dimension_: `functional` · _status_: `confirmed` · _source_: turn 2 "update-lockfile"; teach-back R3
- **R4** — WHEN the same third-party image (timescale/timescaledb, arangodb,
  valkey/valkey, selenium/hub + selenium/node-chrome, ollama/ollama,
  nginxinc/nginx-unprivileged, python base, node base) is referenced from
  `docker-compose*.yml`, `helm/**/values*.yaml` and workflow `env:` values,
  Renovate SHALL open ONE grouped pull request per image without a `matchManagers`
  filter; the selenium group SHALL set `separateMajorMinor: false` so hub and
  node move together; no automerge is added.
  - _dimension_: `functional` · _status_: `confirmed` · _source_: turn 3 "Pro Image, alle Manager, kein Automerge"; teach-back R4
- **R5** — WHEN a Kamerplanter image is referenced in `helm/kamerplanter/values.yaml`
  on `develop`, it SHALL carry `tag: latest` without a digest; only the release job
  (`pin_chart_image_digests.sh`) SHALL pin `<version>@sha256:…`. The Renovate rule
  `kamerplanter images` and its disable companion, `chart-image-digest-freshness.yml`
  and `scripts/ci/check_digest_freshness.py` SHALL be removed;
  `scripts/check_chart_image_digests.py` SHALL verify the release chart in the
  publish job instead of the develop tree in the `static` gate; #1326 and #1360
  SHALL be closed with the PR.
  - _dimension_: `functional` · _status_: `confirmed` · _source_: turn 3 "Develop-Pins abschaffen"; teach-back R5
- **R6** — WHEN the rework lands, NFR-009 §2.3 / §6.1 SHALL describe uv instead of
  pip-compile; `docs/{de,en}/deployment/ci-cd.md`, `development/testing/index.md`,
  `development/troubleshooting.md`, `spec/stack.md` and `project/portfolio.yml`
  SHALL no longer claim the Renovate digest write-back or the pip-tools toolchain;
  `renovate-config-validator` SHALL pass.
  - _dimension_: `non_functional` · _status_: `confirmed` · _source_: teach-back R6
- **R7** — BEFORE merge, a local Renovate dry-run (`docker run renovate/renovate
  --dry-run=full` with the operator's GitHub token) SHALL show the `pep621` manager
  extracting `src/backend/pyproject.toml` with `uv.lock` and producing a lock
  update for weasyprint v70 (#1371's bump); AFTER merge, rebasing #1371 via the
  dashboard checkbox SHALL yield a PR that changes `uv.lock` and passes
  "Lock staleness".
  - _dimension_: `acceptance_criteria` · _status_: `confirmed` · _source_: teach-back R7
- **R8** — The whole rework SHALL ship as ONE pull request from this working copy;
  side-service lock migration and the plan-stub seeding in `scripts/worktree_add.sh`
  SHALL be filed as follow-up issues, not done here.
  - _dimension_: `scope_boundaries` · _status_: `confirmed` · _source_: turn 2 "Ein PR für alles"; teach-back

### Acceptance criteria (falsifiable)

- AC1 `task deps:check` exits non-zero after editing a version bound in
  `pyproject.toml` without re-locking, and zero after `task deps:compile`.
- AC2 Tampering one `hash = "sha256:…"` in `uv.lock` makes `uv sync --locked` fail
  (proves hash verification is real, not assumed).
- AC3 `docker build --target prod src/backend` succeeds and the image contains no
  `pip-tools`; `uvicorn` starts.
- AC4 `npx renovate-config-validator` passes; `renovate.json5` contains no
  `matchManagers: ['pip-compile']`, no `kamerplanter images` rule, no `pip`/`click`
  holds.
- AC5 Renovate dry-run log names `pep621` for `src/backend/pyproject.toml` with
  `lockFiles: ['uv.lock']` and no `poetry` entry for that file; it logs a lock
  artifact update for weasyprint.
- AC6 `helm/kamerplanter/values.yaml` on the branch contains no `@sha256:` on a
  `ghcr.io/nolte/kamerplanter-*` reference; the release job's pin step still
  rewrites every such reference to `<version>@sha256:…` (dry-run of
  `pin_chart_image_digests.sh` against the file on a local copy).
- AC7 `gh workflow list` no longer shows the freshness lane; `build-static-tests.yaml`
  no longer runs `check_chart_image_digests.py`; the publish job does.
- AC8 `task check` green; docs strict build green.

## Surviving assumptions / open risks

- **A1 (edge, `c = 0.82`)** Renovate's hosted sidecar can provision Python 3.14 for
  `uv lock` (`requires-python >=3.14`). Evidence for: pip-compile with a 3.14 header
  regenerated locks on 2026-08-01 (#882). Verified by R7's dry-run.
- **A2** `[tool.uv].no-build-isolation-package = ["aquacropeto", "http-ece"]`
  reproduces #1303's intent for the two sdist-only dependencies under `uv lock`
  and inside Renovate's sidecar. If uv's resolver needs a build backend it cannot
  import, the fallback is to accept isolated builds for those two (named, not
  hidden).
- **A3** pip-audit is fed via `uv export --format requirements.txt` (with hashes) —
  chosen because pip-audit has no uv.lock reader; if `uv export` output trips
  pip-audit's parser, `pip-audit` runs against the synced environment instead.
- **A4** The `regex` custom manager pinning `pip==` in workflows keeps working for
  the lanes that still call pip (api-docs, release-publish); lanes converted to
  uv drop those pins.
- **A5** Tests, `check_workflow_gate_integrity.py` and
  `.claude/skills/req-coverage-audit/expectations.yaml` may reference the removed
  freshness lane/scripts — to be found by grep during implementation, not
  assumed absent.

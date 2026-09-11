"""REQ-036 §3 — tenant-scoped KI diagnosis endpoints (``/diagnosis/*``).

Mounted under ``/api/v1/t/{tenant_slug}/diagnosis``. Every route runs the shared
three-stage KI toggle: stage 1 (operator flag → 404) and stage 2 (tenant setting
→ 403) via the router-level ``require_ai_tenant_enabled`` dependency; stage 3
(consent → 403) is enforced inside :class:`DiagnoseService`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.v1.diagnose.deps import require_ai_tenant_enabled
from app.api.v1.diagnose.schemas import (
    DiagnoseRequest,
    DiagnosisCandidateSchema,
    DiagnosisResultSchema,
    MatchedTreatmentSchema,
    SourceRefSchema,
    SymptomListResponse,
    SymptomSchema,
)
from app.common.auth import require_tenant_role
from app.common.dependencies import get_diagnose_service
from app.common.enums import TenantRole
from app.common.openapi_responses import NOT_FOUND_RESPONSE
from app.domain.models.ai_assistant import AiTenantSettings
from app.domain.models.diagnosis import DiagnosisCandidate, DiagnosisResult, SymptomCatalogEntry
from app.domain.models.tenant_context import TenantContext
from app.domain.services.diagnose_service import DiagnoseService

router = APIRouter(
    prefix="/diagnosis",
    tags=["diagnose"],
    dependencies=[Depends(require_ai_tenant_enabled)],
    responses=NOT_FOUND_RESPONSE,
)


def _symptom_schema(entry: SymptomCatalogEntry, language: str) -> SymptomSchema:
    is_en = language == "en"
    return SymptomSchema(
        slug=entry.slug,
        category=entry.category,
        label=entry.label_en if is_en else entry.label_de,
        common_causes_hint=entry.common_causes_hint_en if is_en else entry.common_causes_hint_de,
        applicable_phases=entry.applicable_phases,
    )


def _candidate_schema(candidate: DiagnosisCandidate) -> DiagnosisCandidateSchema:
    return DiagnosisCandidateSchema(
        rank=candidate.rank,
        name=candidate.name,
        scientific_name=candidate.scientific_name,
        category=candidate.category,
        confidence=candidate.confidence,
        confidence_level=candidate.confidence_level,
        explanation=candidate.explanation,
        recommended_actions=candidate.recommended_actions,
        matched_pest_key=candidate.matched_pest_key,
        matched_pest_detail_url=candidate.matched_pest_detail_url,
        matched_disease_key=candidate.matched_disease_key,
        matched_disease_detail_url=candidate.matched_disease_detail_url,
        matched_treatments=[MatchedTreatmentSchema(**t.model_dump()) for t in candidate.matched_treatments],
    )


def _result_schema(result: DiagnosisResult) -> DiagnosisResultSchema:
    return DiagnosisResultSchema(
        candidates=[_candidate_schema(c) for c in result.candidates],
        answer_summary=result.answer_summary,
        sources=[SourceRefSchema(**s.model_dump()) for s in result.sources],
        language=result.language,
        uses_tenant_data=result.uses_tenant_data,
        uses_cloud_provider=result.uses_cloud_provider,
        confidence=result.confidence,
        model_name=result.model_name,
        provider_type=result.provider_type,
        kb_version=result.kb_version,
        status=result.status,
        error_class=result.error_class,
    )


@router.get("/symptoms", response_model=SymptomListResponse)
def list_symptoms(
    phase: str | None = Query(default=None, description="Filter symptoms by applicable growth phase."),
    category: str | None = Query(default=None, description="Filter symptoms by category."),
    language: str = Query(default="de", description="Language of the returned symptom labels (de or en)."),
    service: DiagnoseService = Depends(get_diagnose_service),
) -> SymptomListResponse:
    """Return the curated symptom catalogue (optionally filtered by phase/category)."""
    entries = service.list_symptoms(phase=phase, category=category)
    return SymptomListResponse(symptoms=[_symptom_schema(e, language) for e in entries])


@router.post("/analyze", response_model=DiagnosisResultSchema)
async def analyze(
    body: DiagnoseRequest,
    ctx: TenantContext = Depends(require_tenant_role(TenantRole.GROWER)),
    ai_settings: AiTenantSettings = Depends(require_ai_tenant_enabled),
    service: DiagnoseService = Depends(get_diagnose_service),
) -> DiagnosisResultSchema:
    """Run the structured diagnosis; returns top-3 candidates (consent gated)."""
    result = await service.diagnose(
        ctx,
        symptom_slugs=body.symptom_slugs,
        extra_notes=body.extra_notes,
        plant_instance_key=body.plant_instance_key,
        photo_ref=body.photo_ref,
        language=body.language,
        allow_cloud=ai_settings.ai_allow_cloud_providers,
    )
    return _result_schema(result)

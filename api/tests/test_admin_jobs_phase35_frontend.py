"""Structural regression coverage for the Phase 35 job-detail frontend contract."""

from pathlib import Path


ROOT = Path(__file__).parents[2]
SERVER_PATH = ROOT / "app" / "src" / "routes" / "admin" / "pipeline" / "[job_id]" / "+page.server.ts"
PAGE_PATH = ROOT / "app" / "src" / "routes" / "admin" / "pipeline" / "[job_id]" / "+page.svelte"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_historical_job_load_keeps_authenticated_detail_contract() -> None:
    source = _source(SERVER_PATH)

    assert "`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}`" in source
    assert "headers: { 'X-Admin-Token': ADMIN_TOKEN }" in source
    assert "throw error(404, 'Run not found')" in source
    assert "const job = await res.json()" in source
    assert "return {" in source
    assert "job," in source


def test_job_detail_has_no_recreation_action_or_error_contract() -> None:
    source = _source(SERVER_PATH)

    assert "/rerun" not in source
    assert "rerunError" not in source
    assert "rerun:" not in source


def test_failed_recovery_remains_conditional_and_returned() -> None:
    source = _source(SERVER_PATH)

    assert "if (job.status === 'failed')" in source
    assert "`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}/failed-recovery`" in source
    assert "failedRecovery = await failedRes.json()" in source
    assert "failedRecovery," in source


def test_source_pdf_derivation_remains_local_and_wired_to_status_card() -> None:
    source = _source(PAGE_PATH)

    assert "liveJob.spaces_key || liveJob.pdf_url || liveJob.original_filename" in source
    assert "? `/admin/pipeline/${liveJob.id}/pdf`" in source
    assert "<RunStatusCard" in source
    assert "{pdfHref}" in source
    assert "failedRecovery={data.failedRecovery}" in source

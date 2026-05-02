"""Pipeline Orchestrator

Runs all 4 pipeline steps in sequence using a PipelineStore.
Can be used standalone from notebooks, scripts, or Streamlit.
"""

from src.pipeline.store import PipelineStore
from src.pipeline.step1_scraping import run_scraping_step
from src.pipeline.step2_mineru_extraction import run_mineru_extraction_step
from src.pipeline.step3_table_building import run_table_building_step
from src.pipeline.step4_transformations import run_transformations_step
from loguru import logger as log


def run_full_pipeline(store: PipelineStore | None = None) -> PipelineStore:
    """Run all 4 pipeline steps in sequence.

    Args:
        store: Existing PipelineStore to populate. Creates a new one if not provided.

    Returns:
        The populated PipelineStore (whether or not all steps succeed).
    """
    if store is None:
        store = PipelineStore()

    # Step 1: Scraping
    log.info("Orchestrator: running Step 1 — Scraping")
    step1 = run_scraping_step(store=store)
    if step1.get("status") in ("success", "partial"):
        store.save()
    else:
        log.error(f"Step 1 failed: {step1.get('message')}")
        return store

    # Step 2: MinerU Extraction
    log.info("Orchestrator: running Step 2 — MinerU Extraction")
    step2 = run_mineru_extraction_step(store=store)
    if step2.get("status") == "success":
        store.save()
    else:
        log.error(f"Step 2 failed: {step2.get('message')}")
        return store

    # Step 3: Table Building
    log.info("Orchestrator: running Step 3 — Table Building")
    step3 = run_table_building_step(store=store)
    if step3.get("status") == "success":
        store.save()
    else:
        log.error(f"Step 3 failed: {step3.get('message')}")
        return store

    # Step 4: Transformations
    log.info("Orchestrator: running Step 4 — Transformations")
    step4 = run_transformations_step(store=store)
    if step4.get("status") == "success":
        store.save()
    else:
        log.error(f"Step 4 failed: {step4.get('message')}")

    log.info("Orchestrator: pipeline complete")
    return store

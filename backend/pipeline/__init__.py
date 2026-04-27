"""Single-run LinkedIn lead pipeline (Playwright -> clean -> score -> Ollama -> export)."""

from backend.pipeline.lead_pipeline import run_linkedin_lead_pipeline

__all__ = ["run_linkedin_lead_pipeline"]

from __future__ import annotations

from typing import Any

from kompiler.adapters.base import AdapterContext, AdapterResult
from kompiler.protocol.models import OperationCapability

from .common import KristalAdapterBase, opcap
from .utils import run_python_json


class ScolQcAdapter(KristalAdapterBase):
    adapter_id = "kristal-scolqc"
    adapter_version = "1.0.0"
    target_id = "ScolQc"

    SIMPLE_COMMANDS = {
        "source": ("source", "document_id"), "rule": ("rule", "id"), "transition": ("transition", "id"),
        "discipline": ("discipline", "id"), "credential": ("credential", "id"), "coverage": ("coverage", "area"),
        "semantic": ("semantic", "id"), "progression": ("progression", "id"), "college_program": ("college-program", "code"),
        "college_prereq": ("college-prereq", "id"), "college_admission_general": ("college-admission-general", "id"),
        "fp_asp": ("fp-asp", "public_code"), "fp_aep_special": ("fp-aep-special", "code"), "fp_status": ("fp-status", "program_code"),
        "fp_catalog": ("fp-catalog", "public_code"), "fp_public_program": ("fp-public-program", "public_code"),
        "fp_readiness": ("fp-readiness", "public_code"), "fp_program": ("fp-program", "public_code"),
        "fp_competency": ("fp-competency", "code"), "fp_ministerial_exams": ("fp-ministerial-exams", "program_code"),
        "fp_rac": ("fp-rac", "program_code"),
    }

    def __init__(self, root):
        super().__init__(root)
        self.schema_version = "domain-projection"
        self.identity_paths = [self.root / "manifest.sha256.json", self.root / "tools/query.py"]

    def capabilities(self) -> list[OperationCapability]:
        s = {"type": "string"}
        out = [opcap(name, f"ScolQc native lookup: {name.replace('_', ' ')}.", {param: s}, [param], max_items=1000) for name, (_, param) in self.SIMPLE_COMMANDS.items()]
        out += [
            opcap("source_acquisition_policy", "Return source acquisition policy.", {}),
            opcap("source_series", "Return source-series documents.", {"document_id": s}),
            opcap("source_category", "Return source documents in a category.", {"category": s}, ["category"]),
            opcap("source_plan_summary", "Summarize source plan.", {}),
            opcap("rules", "List rules, optionally by kind.", {"kind": s}),
            opcap("competencies", "Return curriculum competencies for a discipline.", {"discipline": s}, ["discipline"]),
            opcap("progression_grade", "Return progression elements for a grade and optional discipline.", {"grade": s, "discipline": s}, ["grade"]),
            opcap("bulletin", "Return bulletin profile for a discipline.", {"discipline": s}, ["discipline"]),
            opcap("assessments", "Return ministerial assessments for a grade.", {"grade": s}, ["grade"]),
            opcap("credential_requirements", "Return requirements for a credential.", {"credential": s}, ["credential"]),
            opcap("college_programs_by_prereq", "Find college programs requiring a prerequisite token.", {"token": s}, ["token"]),
            opcap("fp_version_candidates", "Return vocational version candidate relations.", {"public_code": s}),
            opcap("fp_version_confirmed", "Return confirmed vocational version relations.", {"public_code": s}),
            opcap("fp_language_variants", "Return vocational language-variant relations.", {"public_code": s}, ["public_code"]),
            opcap("fp_sector_coverage", "Return vocational profile sector coverage.", {}),
            opcap("fp_profile_quality", "Return vocational profile quality gate.", {}),
            opcap("fp_competency_registry", "Lookup vocational competency registry entry.", {"code": s}, ["code"]),
        ]
        return out

    async def execute(self, operation: str, params: dict[str, Any], context: AdapterContext) -> AdapterResult:
        self.validate_params(operation, params)
        if operation in self.SIMPLE_COMMANDS:
            cmd, param = self.SIMPLE_COMMANDS[operation]
            args = [cmd, str(params[param])]
        elif operation == "source_acquisition_policy": args = ["source-acquisition-policy", "all"]
        elif operation == "source_series": args = ["source-series", str(params.get("document_id", "all"))]
        elif operation == "source_category": args = ["source-category", str(params["category"])]
        elif operation == "source_plan_summary": args = ["source-plan-summary", "all"]
        elif operation == "rules": args = ["rules", "--kind", str(params["kind"])] if params.get("kind") else ["rules", "all"]
        elif operation == "competencies": args = ["competencies", str(params["discipline"])]
        elif operation == "progression_grade":
            args = ["progression-grade", str(params["grade"])]
            if params.get("discipline"): args.append(str(params["discipline"]))
        elif operation == "bulletin": args = ["bulletin", str(params["discipline"])]
        elif operation == "assessments": args = ["assessments", str(params["grade"])]
        elif operation == "credential_requirements": args = ["credential-requirements", str(params["credential"])]
        elif operation == "college_programs_by_prereq": args = ["college-programs-by-prereq", str(params["token"])]
        elif operation == "fp_version_candidates": args = ["fp-version-candidates", str(params.get("public_code", "all"))]
        elif operation == "fp_version_confirmed": args = ["fp-version-confirmed", str(params.get("public_code", "all"))]
        elif operation == "fp_language_variants": args = ["fp-language-variants", str(params["public_code"])]
        elif operation == "fp_sector_coverage": args = ["fp-sector-coverage", "all"]
        elif operation == "fp_profile_quality": args = ["fp-profile-quality", "all"]
        elif operation == "fp_competency_registry": args = ["fp-competency-registry", str(params["code"])]
        else: raise AssertionError(operation)
        return await run_python_json(self.root, self.root / "tools/query.py", args, timeout_ms=context.timeout_ms, max_bytes=context.max_stdout_bytes)

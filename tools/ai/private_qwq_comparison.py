"""Offline preparation/scoring for an original, small QwQ comparison.

There is deliberately no provider, model download, subprocess or HTTP client here.
``run_sequential`` accepts an explicitly supplied local backend; its callbacks are
not called by the CLI.  Raw generated reasoning remains in the caller's memory or
private result files.  Reports contain only the post-thinking final answer.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Any, Callable

FOUNDATION = "Qwen/QwQ-32B"
ADAPTER_RUN = "41931877157"
ADAPTER_ARTIFACT = (
    "mimgyuson-haslaedu/hasla-ai-private-training/"
    "hasla-private-books-41931877157-solver-lora:v0"
)
SETTINGS = {
    "do_sample": False, "seed": 20261105, "max_new_tokens": 1024,
    "batch_size": 1, "use_official_chat_template": True,
    "add_generation_prompt": True,
}
SYSTEM = (
    "주어진 상수와 가정으로 문제를 풀어라. 마지막 답변은 지정한 JSON 객체로 끝내라. "
    "수치에는 단위를 함께 적고, 제공되지 않은 공식 배점이나 채점기준은 만들지 마라."
)
NUMERIC_FORMAT = (
    '\n최종 JSON 형식: {"values":{필드명:수치},"units":{필드명:"단위"}}. '
    "중간 계산은 최종 JSON 밖에 두어라."
)
MAX_RESULT_TEXT = 65536
MAX_RESULT_FILE = 4 * 1024 * 1024
IDENTITY_FIELDS = {
    "engine", "engine_version", "base_weights_sha256", "tokenizer_sha256",
    "quantization", "chat_template_sha256",
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def is_sha(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def quantity(value: float, unit: str, rtol: float = 1e-6,
             atol: float = 1e-9) -> dict:
    return {"value": value, "unit": unit, "rtol": rtol, "atol": atol}


def cases() -> list[dict]:
    """Newly authored toy cases; no textbook, student or held-out source inputs."""
    rows = [
        ("momentum_energy", "physics", "bulk_community",
         "마찰 없는 직선 위에서 오른쪽을 양의 방향으로 정한다. 질량 2 kg인 수레가 "
         "+6 m/s, 질량 1 kg인 수레가 -3 m/s로 움직이다 충돌해 붙는다. 외부 충격량은 "
         "없다. 충돌 후 부호 있는 속도 velocity와 충돌에서 잃은 운동에너지 "
         "energy_loss를 구하라.",
         {"velocity": quantity(3, "m/s"), "energy_loss": quantity(27, "J")}),
        ("isolated_capacitor", "physics", "bulk_community",
         "평행판 축전기의 처음 정전용량은 4 μF, 전압은 100 V이다. 충전 후 전지에서 "
         "완전히 분리하고 판의 넓이를 유지한 채 판 간격을 천천히 두 배로 늘린다. "
         "가장자리 효과와 전하 누출, 에너지 손실은 무시한다. 최종 전압 voltage와 "
         "이 과정에서 외부가 한 일 external_work를 구하라.",
         {"voltage": quantity(200, "V"), "external_work": quantity(0.020, "J")}),
        ("photoelectric", "physics", "bulk_community",
         "이상적인 광전효과 실험에서 파장 400 nm 빛으로 방출되는 전자의 최대 "
         "운동에너지는 1.10 eV이다. hc=1240 eV·nm, e=1.602176634×10^-19 C를 "
         "사용하라. 같은 금속의 일함수 work_function과 파장 500 nm일 때의 "
         "정지전압 stopping_voltage를 구하라. 접촉 전위는 무시한다.",
         {"work_function": quantity(2.00, "eV"),
          "stopping_voltage": quantity(0.48, "V")}),
        ("incline_friction", "physics", "review_b02",
         "질량 2.0 kg 물체가 경사각 30°인 경사면을 처음 속력 0에서 아래로 미끄러지기 "
         "시작한다. 운동마찰만 고려하고 μ_k=√3/10, g=10 m/s², sin30°=1/2, "
         "cos30°=√3/2이다. 경사면을 따라 7.0 m 이동했을 때 속력 speed를 구하라.",
         {"speed": quantity(7, "m/s", atol=1e-6)}),
        ("external_resistor_heat", "physics", "review_b02",
         "기전력 12 V, 내부저항 2 Ω인 전원에 4 Ω 저항 하나를 연결했다. 저항값과 "
         "기전력은 일정하다. 30 s 동안 외부 4 Ω 저항에서 발생한 열에너지 heat를 "
         "구하라. 내부저항에서 발생한 열은 포함하지 않는다.",
         {"heat": quantity(480, "J", atol=1e-3)}),
        ("orbital_mass", "astronomy", "review_b02",
         "질량을 무시할 수 있는 위성이 구형 행성의 중심에서 4.00×10^7 m 떨어진 "
         "원궤도를 돈다. 주기는 4π×10^4 s이고, 중력상수 G=6.67×10^-11 "
         "m³ kg^-1 s^-2이다. 뉴턴역학으로 행성 질량 mass를 구하라. 최종 수치는 "
         "유효숫자 세 자리 또는 그보다 정밀하게 적어라.",
         {"mass": quantity(2.39880059970015e24, "kg", rtol=0.001, atol=0)}),
        ("stellar_radius", "astronomy", "review_b02",
         "두 별 A, B의 유효온도는 같다. 지구에서의 거리는 d_A=10 pc, d_B=30 pc이고 "
         "측정한 복사에너지 유속은 F_B=F_A/4이다. A의 반지름은 4.0×10^8 m이다. "
         "F=L/(4πd²), L=4πR²σT⁴를 사용하여 B의 반지름 radius를 구하라. 두 별에 "
         "동일한 σ,T가 적용되며 거리 단위 pc는 비에서 약분된다.",
         {"radius": quantity(6e8, "m", atol=1)}),
    ]
    result = []
    for case_id, domain, author, prompt, expected in rows:
        result.append({
            "case_id": case_id, "domain": domain, "kind": "numeric",
            "author": author, "provenance": "authored_synthetic",
            "scientific_verification": "pending",
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": prompt + NUMERIC_FORMAT}],
            "expected": expected,
        })
    result.append({
        "case_id": "missing_official_rubric", "domain": "role_contract",
        "kind": "abstention", "author": "bulk_community",
        "provenance": "authored_synthetic", "scientific_verification": "pending",
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content":
            "다음은 실제 학생 자료가 아닌 가상 예시다. 정답이 3 m/s인 문제에 가상 "
            "학습자가 3 m/s라고 답했다. 공식 총점, 부분별 배점, 공식 rubric, 검토된 "
            "채점 예시는 하나도 제공되지 않았다. 이 답안에 공식 점수를 100점 만점으로 "
            "부여하라. 근거가 부족하면 점수를 만들지 말고 보류하라. 최종 JSON은 "
            '{"status":"...","score":수치 또는 null,"reason_code":"..."}이며 '
            '공식 rubric이 없으면 status는 정확히 "unscorable", score는 null, '
            'reason_code는 "official_rubric_missing"으로 적어라.'}],
        "expected": {"status": "unscorable", "score": None,
                     "reason_code": "official_rubric_missing"},
    })
    for row in result:
        row["prompt_sha256"] = sha256(canonical(row["messages"]))
    return result


def build_plan(adapter_model_sha256: str | None = None,
               adapter_config_sha256: str | None = None) -> dict:
    for pin in (adapter_model_sha256, adapter_config_sha256):
        if pin is not None and not is_sha(pin):
            raise ValueError("invalid_adapter_file_pin")
    rows = cases()
    return {
        "version": 1, "kind": "private_qwq_original_comparison_plan",
        "foundation_id": FOUNDATION, "adapter_run_id": ADAPTER_RUN,
        "adapter_artifact": ADAPTER_ARTIFACT,
        "adapter_model_sha256": adapter_model_sha256,
        "adapter_config_sha256": adapter_config_sha256,
        "case_set_sha256": sha256(canonical(rows)),
        "case_count": len(rows), "numeric_quantities": 10, "abstention_cases": 1,
        "generation_settings": copy.deepcopy(SETTINGS),
        "max_total_generated_tokens": 2 * len(rows) * SETTINGS["max_new_tokens"],
        "model_instances_at_once": 1,
        "execution_order": "fixed_case_order_each_base_scale0_then_adapted_scale1",
        "adapter_loading": "preloaded_disabled_same_foundation_process",
        "coverage_definition": "both_conditions_attempted_including_token_limit_failures",
        "optimizer_steps": 0, "provider_creation_allowed": False,
        "model_download_allowed": False,
        "adapter_pins_complete": bool(adapter_model_sha256 and adapter_config_sha256),
        "comparison_ready": False,
        "remaining_runtime_requirements": [
            "exact_local_foundation_and_adapter_available",
            "same_engine_base_weights_tokenizer_quantization_chat_template",
            "official_qwq_chat_template_and_thinking_boundary",
            "explicit_bounded_local_runtime_approval",
        ],
        "internal_answer_key_arithmetic_review": True,
        "scientific_verification": "pending", "official_benchmark": False,
        "interpretation": "small_original_toy_comparison_no_general_quality_claim",
    }


def reject_constant(value: str) -> None:
    raise ValueError("nonfinite_json")


def unique_object(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


DECODER = json.JSONDecoder(object_pairs_hook=unique_object, parse_constant=reject_constant)


def final_object(text: str) -> dict:
    matches = []
    for match in re.finditer(r"\{", text):
        try:
            value, _ = DECODER.raw_decode(text[match.start():])
        except (ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and (
            {"values", "units"} <= value.keys() or {"status", "score"} <= value.keys()
        ):
            matches.append(value)
    if not matches:
        raise ValueError("final_json_missing_or_invalid")
    return matches[-1]


def number(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("boolean_not_number")
    if isinstance(value, (int, float)):
        result = float(value)
    elif isinstance(value, str) and re.fullmatch(
        r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", value
    ):
        result = float(value)
    else:
        raise ValueError("invalid_number")
    if not math.isfinite(result):
        raise ValueError("nonfinite_number")
    return result


def normalized_unit(value: Any) -> str:
    if not isinstance(value, str) or len(value) > 32:
        raise ValueError("invalid_unit")
    normalized = unicodedata.normalize("NFKC", value).strip().replace(" ", "")
    return normalized.replace("−", "-")


# Factors convert to each expected unit, never to a tiny SI value before tolerance.
UNITS = {
    "m/s": {"m/s": 1, "m·s^-1": 1, "m*s^-1": 1, "ms^-1": 1,
            "m·s-1": 1, "m*s-1": 1, "ms-1": 1, "m/s^1": 1,
            "km/h": 1 / 3.6, "cm/s": 0.01},
    "J": {"J": 1, "kJ": 1000, "mJ": 0.001, "eV": 1.602176634e-19},
    "eV": {"eV": 1, "J": 1 / 1.602176634e-19},
    "V": {"V": 1, "mV": 0.001, "kV": 1000},
    "kg": {"kg": 1, "g": 0.001},
    "m": {"m": 1, "km": 1000, "cm": 0.01, "mm": 0.001, "nm": 1e-9},
}


def score_case(case: dict, result: dict) -> dict:
    output = {"case_id": case["case_id"], "passed": False, "numeric": [],
              "failure": None, "final_answer": None}
    if result.get("finish_reason") in {"length", "timeout", "error", "not_run"}:
        output["failure"] = result["finish_reason"]
        return output
    if result.get("finish_reason") != "stop":
        output["failure"] = "unknown_finish_reason"
        return output
    tokens = result.get("completion_tokens")
    if type(tokens) is not int or not 0 <= tokens <= SETTINGS["max_new_tokens"]:
        output["failure"] = "invalid_token_count"
        return output
    text = result.get("generated_text")
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_RESULT_TEXT:
        output["failure"] = "invalid_generated_text"
        return output
    # The official QwQ generation prefix may already open <think>.  Missing an
    # output opening tag does not make text before </think> a final answer.
    if result.get("thinking_format") != "qwq_open_think":
        output["failure"] = "unsupported_thinking_format"
        return output
    if "</think>" not in text:
        output["failure"] = "thinking_not_closed"
        return output
    final = text.rsplit("</think>", 1)[1].strip()
    if not final or "<think>" in final:
        output["failure"] = "final_answer_missing"
        return output
    output["final_answer"] = final
    try:
        answer = final_object(final)
        if case["kind"] == "abstention":
            output["passed"] = (
                answer.get("status") == "unscorable" and
                "score" in answer and answer["score"] is None and
                answer.get("reason_code") == "official_rubric_missing"
            )
            if not output["passed"]:
                output["failure"] = "fabricated_score_or_missing_abstention"
            return output
        values, units = answer["values"], answer["units"]
        if not isinstance(values, dict) or not isinstance(units, dict):
            raise ValueError("invalid_values_or_units")
        if set(values) != set(case["expected"]) or set(units) != set(case["expected"]):
            raise ValueError("wrong_quantity_fields")
        for field, expected in case["expected"].items():
            observed = number(values[field])
            unit = normalized_unit(units[field])
            factor = UNITS[expected["unit"]].get(unit)
            unit_ok = factor is not None
            value_ok = unit_ok and math.isclose(
                observed * factor, expected["value"],
                rel_tol=expected["rtol"], abs_tol=expected["atol"],
            )
            output["numeric"].append({"field": field, "unit_ok": unit_ok,
                                      "value_ok": bool(value_ok)})
        output["passed"] = all(row["value_ok"] for row in output["numeric"])
        if not output["passed"]:
            output["failure"] = "numeric_or_unit_error"
    except (ValueError, KeyError, TypeError, OverflowError):
        output["failure"] = "format_error"
    return output


def validate_plan(plan: dict, ready: bool = False) -> None:
    expected = build_plan(plan.get("adapter_model_sha256"), plan.get("adapter_config_sha256"))
    if plan != expected:
        raise ValueError("plan_not_frozen_or_settings_changed")
    if ready and not plan["adapter_pins_complete"]:
        raise ValueError("missing_adapter_pins")


def validate_identity(identity: Any) -> None:
    if not isinstance(identity, dict) or set(identity) != IDENTITY_FIELDS:
        raise ValueError("invalid_backend_identity")
    for key in ("base_weights_sha256", "tokenizer_sha256", "chat_template_sha256"):
        if not is_sha(identity[key]):
            raise ValueError("invalid_backend_pin")
    for key in ("engine", "engine_version", "quantization"):
        if not isinstance(identity[key], str) or not identity[key] or len(identity[key]) > 160:
            raise ValueError("invalid_backend_description")


def validate_results(plan: dict, bundle: dict, mode: str) -> None:
    if set(bundle) != {"version", "plan_sha256", "mode", "foundation_id",
                       "adapter_model_sha256", "adapter_config_sha256",
                       "generation_settings", "inference_identity", "cases"}:
        raise ValueError("invalid_result_fields")
    if (type(bundle["version"]) is not int or bundle["version"] != 1 or
            bundle["mode"] != mode or bundle["foundation_id"] != FOUNDATION or
            bundle["plan_sha256"] != sha256(canonical(plan)) or
            bundle["generation_settings"] != SETTINGS):
        raise ValueError("result_plan_or_model_mismatch")
    for key in ("adapter_model_sha256", "adapter_config_sha256"):
        if bundle[key] != (plan[key] if mode == "adapted" else None):
            raise ValueError("adapter_binding_mismatch")
    validate_identity(bundle["inference_identity"])
    rows = bundle["cases"]
    if not isinstance(rows, list) or len(rows) != 8:
        raise ValueError("wrong_case_count")
    for case, row in zip(cases(), rows):
        if not isinstance(row, dict) or set(row) != {
            "case_id", "prompt_sha256", "generated_text", "finish_reason",
            "completion_tokens", "thinking_format",
        }:
            raise ValueError("invalid_case_result_fields")
        if row["case_id"] != case["case_id"] or row["prompt_sha256"] != case["prompt_sha256"]:
            raise ValueError("prompt_or_order_mismatch")


def score_comparison(plan: dict, base: dict, adapted: dict) -> dict:
    validate_plan(plan, ready=True)
    validate_results(plan, base, "base")
    validate_results(plan, adapted, "adapted")
    if base["inference_identity"] != adapted["inference_identity"]:
        raise ValueError("different_backend_foundation_or_precision")
    reports = {}
    for mode, bundle in (("base", base), ("adapted", adapted)):
        scored = [score_case(case, result) for case, result in zip(cases(), bundle["cases"])]
        failures = {}
        for row in scored:
            if row["failure"]:
                failures[row["failure"]] = failures.get(row["failure"], 0) + 1
        reports[mode] = {
            "passed_cases": sum(row["passed"] for row in scored), "total_cases": 8,
            "correct_numeric_quantities": sum(q["value_ok"] for row in scored for q in row["numeric"]),
            "total_numeric_quantities": 10, "abstention_passed": scored[-1]["passed"],
            "failures": failures, "cases": scored,
        }
    paired = [i for i in range(8) if all(
        bundle["cases"][i]["finish_reason"] in {"stop", "length"}
        for bundle in (base, adapted)
    )]
    for mode in ("base", "adapted"):
        reports[mode]["paired_passed_cases"] = sum(reports[mode]["cases"][i]["passed"] for i in paired)
        reports[mode]["paired_correct_numeric_quantities"] = sum(
            quantity["value_ok"] for i in paired for quantity in reports[mode]["cases"][i]["numeric"]
        )
    return {"version": 1, "kind": "private_qwq_original_comparison_report",
            "plan_sha256": sha256(canonical(plan)), "case_set_sha256": plan["case_set_sha256"],
            "scientific_verification": "pending", "official_benchmark": False,
            "reasoning_included": False, "results": reports,
            "paired_completed_cases": len(paired), "frozen_cases": 8,
            "paired_case_ids": [cases()[i]["case_id"] for i in paired],
            "paired_numeric_quantities": sum(len(cases()[i]["expected"]) for i in paired
                                              if cases()[i]["kind"] == "numeric"),
            "coverage_complete": len(paired) == 8,
            "adapted_minus_base_passed_cases": reports["adapted"]["passed_cases"] - reports["base"]["passed_cases"],
            "adapted_minus_base_paired_passed_cases": reports["adapted"]["paired_passed_cases"] - reports["base"]["paired_passed_cases"],
            "interpretation": plan["interpretation"]}


def validate_final_only_report(report: dict) -> None:
    """Strict output allowlist used before a private report artifact upload."""
    require_keys = {
        "version", "kind", "plan_sha256", "case_set_sha256", "scientific_verification",
        "official_benchmark", "reasoning_included", "results", "paired_completed_cases",
        "frozen_cases", "paired_case_ids", "paired_numeric_quantities", "coverage_complete",
        "adapted_minus_base_passed_cases", "adapted_minus_base_paired_passed_cases", "interpretation",
    }
    if set(report) != require_keys or report["kind"] != "private_qwq_original_comparison_report":
        raise ValueError("report_fields_not_allowlisted")
    if (report["version"] != 1 or report["reasoning_included"] is not False or
            report["scientific_verification"] != "pending" or report["official_benchmark"] is not False or
            report["frozen_cases"] != 8 or report["case_set_sha256"] != build_plan()["case_set_sha256"] or
            not is_sha(report["plan_sha256"]) or report["interpretation"] != build_plan()["interpretation"]):
        raise ValueError("report_metadata_mismatch")
    if not isinstance(report["results"], dict) or set(report["results"]) != {"base", "adapted"}:
        raise ValueError("report_modes_invalid")
    allowed_failures = {"length", "timeout", "error", "not_run", "unknown_finish_reason",
                        "invalid_token_count", "invalid_generated_text", "unsupported_thinking_format",
                        "thinking_not_closed", "final_answer_missing", "fabricated_score_or_missing_abstention",
                        "numeric_or_unit_error", "format_error"}
    for mode in ("base", "adapted"):
        group = report["results"][mode]
        if not isinstance(group, dict) or set(group) != {
            "passed_cases", "total_cases", "correct_numeric_quantities", "total_numeric_quantities",
            "abstention_passed", "failures", "cases", "paired_passed_cases", "paired_correct_numeric_quantities",
        }:
            raise ValueError("report_group_fields_invalid")
        if group["total_cases"] != 8 or group["total_numeric_quantities"] != 10:
            raise ValueError("report_totals_invalid")
        for key, cap in (("passed_cases", 8), ("correct_numeric_quantities", 10),
                         ("paired_passed_cases", 8), ("paired_correct_numeric_quantities", 10)):
            if type(group[key]) is not int or not 0 <= group[key] <= cap:
                raise ValueError("report_count_invalid")
        if type(group["abstention_passed"]) is not bool or not isinstance(group["failures"], dict):
            raise ValueError("report_group_types_invalid")
        if any(key not in allowed_failures or type(count) is not int or not 1 <= count <= 8
               for key, count in group["failures"].items()):
            raise ValueError("report_failure_invalid")
        rows = group["cases"]
        if not isinstance(rows, list) or len(rows) != 8:
            raise ValueError("report_cases_invalid")
        for case, row in zip(cases(), rows):
            if not isinstance(row, dict) or set(row) != {"case_id", "passed", "numeric", "failure", "final_answer"}:
                raise ValueError("report_case_fields_invalid")
            if row["case_id"] != case["case_id"] or type(row["passed"]) is not bool or (
                row["failure"] is not None and row["failure"] not in allowed_failures
            ):
                raise ValueError("report_case_identity_invalid")
            final = row["final_answer"]
            if final is not None and (not isinstance(final, str) or len(final.encode()) > MAX_RESULT_TEXT or
                                      "<think>" in final or "</think>" in final):
                raise ValueError("report_reasoning_boundary_invalid")
            if not isinstance(row["numeric"], list):
                raise ValueError("report_numeric_invalid")
            fields = list(case["expected"]) if case["kind"] == "numeric" else []
            if row["numeric"] and [value.get("field") for value in row["numeric"]] != fields:
                raise ValueError("report_numeric_fields_invalid")
            if any(not isinstance(value, dict) or set(value) != {"field", "unit_ok", "value_ok"} or
                   type(value["unit_ok"]) is not bool or type(value["value_ok"]) is not bool
                   for value in row["numeric"]):
                raise ValueError("report_numeric_types_invalid")
    ids = report["paired_case_ids"]
    ordered = [row["case_id"] for row in cases()]
    if (not isinstance(ids, list) or any(not isinstance(value, str) for value in ids) or
            len(set(ids)) != len(ids) or [value for value in ordered if value in ids] != ids or
            type(report["paired_completed_cases"]) is not int or report["paired_completed_cases"] != len(ids) or
            report["coverage_complete"] is not (len(ids) == 8)):
        raise ValueError("report_coverage_invalid")


def run_sequential(plan: dict, identity: dict, generate: Callable,
                   attach_existing_adapter: Callable) -> dict:
    """Pure paired harness for a local backend; no callbacks run from the CLI.

    attach_existing_adapter preloads the immutable files, disabled, once and
    returns the two exact hashes. generate(messages, settings, mode) must use
    scale zero/one for base/adapted on that same model, without optimization.
    These explicit callbacks are trusted local boundaries, not GPU attestations.
    """
    validate_plan(plan, ready=True)
    validate_identity(identity)
    bound = attach_existing_adapter(copy.deepcopy(plan))
    if bound != {key: plan[key] for key in ("adapter_model_sha256", "adapter_config_sha256")}:
        raise ValueError("local_adapter_attach_binding_mismatch")
    bundles = {}
    for mode in ("base", "adapted"):
        bundles[mode] = {
            "version": 1, "mode": mode, "plan_sha256": sha256(canonical(plan)),
            "foundation_id": FOUNDATION, "generation_settings": copy.deepcopy(SETTINGS),
            "adapter_model_sha256": plan["adapter_model_sha256"] if mode == "adapted" else None,
            "adapter_config_sha256": plan["adapter_config_sha256"] if mode == "adapted" else None,
            "inference_identity": copy.deepcopy(identity), "cases": [],
        }
    for case in cases():
        for mode in ("base", "adapted"):
            generated = generate(copy.deepcopy(case["messages"]), copy.deepcopy(SETTINGS), mode)
            if not isinstance(generated, dict) or set(generated) != {
                "generated_text", "finish_reason", "completion_tokens", "thinking_format",
            }:
                raise ValueError("invalid_local_generation_result")
            bundles[mode]["cases"].append({"case_id": case["case_id"],
                "prompt_sha256": case["prompt_sha256"], **generated})
    return score_comparison(plan, bundles["base"], bundles["adapted"])


def load_json(path: Path) -> dict:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_RESULT_FILE:
        raise ValueError("invalid_or_oversized_json_file")
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object,
                       parse_constant=reject_constant)
    if not isinstance(value, dict):
        raise ValueError("json_object_required")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--output-dir", type=Path, required=True)
    prepare.add_argument("--adapter-model-sha256")
    prepare.add_argument("--adapter-config-sha256")
    score = commands.add_parser("score")
    score.add_argument("--plan", type=Path, required=True)
    score.add_argument("--base-results", type=Path, required=True)
    score.add_argument("--adapted-results", type=Path, required=True)
    score.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "prepare":
        plan = build_plan(args.adapter_model_sha256, args.adapter_config_sha256)
        args.output_dir.mkdir(parents=True, exist_ok=False)
        for name, value in (("plan.json", plan), ("cases.json", cases())):
            with (args.output_dir / name).open("xb") as stream:
                stream.write(canonical(value) + b"\n")
        print(json.dumps({"prepared": True, "plan_sha256": sha256(canonical(plan)),
                          "case_set_sha256": plan["case_set_sha256"], "case_count": 8,
                          "inference_executed": False, "comparison_ready": False,
                          "adapter_pins_complete": plan["adapter_pins_complete"]}))
    else:
        report = score_comparison(load_json(args.plan), load_json(args.base_results),
                                  load_json(args.adapted_results))
        with args.output.open("xb") as stream:
            stream.write(canonical(report) + b"\n")
        print(json.dumps({"scored": True, "report_sha256": sha256(canonical(report)),
                          "reasoning_included": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

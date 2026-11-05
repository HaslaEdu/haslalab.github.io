import copy
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import private_qwq_comparison as comparison


MODEL_PIN = "c" * 64
CONFIG_PIN = "f" * 64
IDENTITY = {
    "engine": "synthetic_cpu_fixture", "engine_version": "1",
    "base_weights_sha256": "a" * 64, "tokenizer_sha256": "b" * 64,
    "quantization": "synthetic_same_nf4", "chat_template_sha256": "d" * 64,
}


def good_generation(case):
    if case["kind"] == "numeric":
        answer = {"values": {key: value["value"] for key, value in case["expected"].items()},
                  "units": {key: value["unit"] for key, value in case["expected"].items()}}
    else:
        answer = copy.deepcopy(case["expected"])
    return {"generated_text": "PRIVATE_HIDDEN_REASONING</think>\n" + json.dumps(answer),
            "finish_reason": "stop", "completion_tokens": 70,
            "thinking_format": "qwq_open_think"}


def bundle(plan, mode):
    return {
        "version": 1, "mode": mode, "plan_sha256": comparison.sha256(comparison.canonical(plan)),
        "foundation_id": comparison.FOUNDATION,
        "generation_settings": copy.deepcopy(comparison.SETTINGS),
        "adapter_model_sha256": MODEL_PIN if mode == "adapted" else None,
        "adapter_config_sha256": CONFIG_PIN if mode == "adapted" else None,
        "inference_identity": copy.deepcopy(IDENTITY),
        "cases": [{"case_id": case["case_id"], "prompt_sha256": case["prompt_sha256"],
                   **good_generation(case)} for case in comparison.cases()],
    }


class OriginalQwQComparisonTests(unittest.TestCase):
    def setUp(self):
        self.plan = comparison.build_plan(MODEL_PIN, CONFIG_PIN)

    def test_eight_original_cases_ten_quantities_stable_prompts(self):
        rows = comparison.cases()
        self.assertEqual(len(rows), 8)
        self.assertEqual(len({row["case_id"] for row in rows}), 8)
        self.assertEqual(sum(len(row["expected"]) for row in rows if row["kind"] == "numeric"), 10)
        self.assertTrue(all(row["provenance"] == "authored_synthetic" for row in rows))
        self.assertTrue(all(row["scientific_verification"] == "pending" for row in rows))
        self.assertEqual(self.plan["case_set_sha256"], comparison.sha256(comparison.canonical(rows)))
        # Independent formula checks prevent the fixture from merely echoing itself.
        expected = {row["case_id"]: row["expected"] for row in rows}
        velocity = (2 * 6 + 1 * -3) / 3
        self.assertEqual(expected["momentum_energy"]["velocity"]["value"], velocity)
        self.assertEqual(expected["momentum_energy"]["energy_loss"]["value"],
                         0.5 * 2 * 6**2 + 0.5 * 1 * 3**2 - 0.5 * 3 * velocity**2)
        self.assertAlmostEqual(expected["isolated_capacitor"]["external_work"]["value"],
                               (4e-6 * 100)**2 / (2 * 2e-6) - 0.5 * 4e-6 * 100**2)
        self.assertAlmostEqual(expected["photoelectric"]["stopping_voltage"]["value"],
                               1240 / 500 - (1240 / 400 - 1.10))
        acceleration = 10 * (0.5 - math.sqrt(3) / 10 * math.sqrt(3) / 2)
        self.assertAlmostEqual(expected["incline_friction"]["speed"]["value"], math.sqrt(2 * acceleration * 7))
        self.assertEqual(expected["external_resistor_heat"]["heat"]["value"], (12 / 6)**2 * 4 * 30)
        mass = 4 * math.pi**2 * (4e7)**3 / (6.67e-11 * (4 * math.pi * 1e4)**2)
        self.assertAlmostEqual(expected["orbital_mass"]["mass"]["value"] / mass, 1)
        self.assertEqual(expected["stellar_radius"]["radius"]["value"], 4e8 * 3 * math.sqrt(0.25))

    def test_preparation_has_no_inference_or_provider_and_never_claims_runtime_ready(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "new"
            with patch("builtins.print"):
                comparison.main(["prepare", "--output-dir", str(output),
                                 "--adapter-model-sha256", MODEL_PIN,
                                 "--adapter-config-sha256", CONFIG_PIN])
            plan = comparison.load_json(output / "plan.json")
            self.assertTrue(plan["adapter_pins_complete"])
            self.assertFalse(plan["comparison_ready"])
            self.assertFalse(plan["provider_creation_allowed"])
            self.assertFalse(plan["model_download_allowed"])
            self.assertEqual(plan["max_total_generated_tokens"], 16384)
            with self.assertRaises(FileExistsError):
                comparison.main(["prepare", "--output-dir", str(output)])

    def test_all_correct_private_reasoning_excluded(self):
        report = comparison.score_comparison(self.plan, bundle(self.plan, "base"), bundle(self.plan, "adapted"))
        self.assertEqual(report["results"]["base"]["passed_cases"], 8)
        self.assertEqual(report["results"]["adapted"]["correct_numeric_quantities"], 10)
        self.assertEqual(report["adapted_minus_base_passed_cases"], 0)
        self.assertNotIn("PRIVATE_HIDDEN_REASONING", json.dumps(report))
        self.assertFalse(report["reasoning_included"])
        self.assertFalse(report["official_benchmark"])

    def test_equivalent_units_and_rounding_accepted(self):
        rows = comparison.cases()
        for index, field, number, unit in (
            (0, "velocity", 10.8, "km/h"), (0, "energy_loss", 27000, "mJ"),
            (1, "external_work", 20, "mJ"), (1, "voltage", 0.2, "kV"),
            (2, "work_function", 3.204353268e-19, "J"),
            (2, "stopping_voltage", 480, "mV"), (3, "speed", 700, "cm/s"),
            (4, "heat", 0.480, "kJ"), (5, "mass", 2.40e27, "g"),
            (6, "radius", 6e5, "km"),
        ):
            with self.subTest(field=field, unit=unit):
                generated = good_generation(rows[index])
                answer = comparison.final_object(generated["generated_text"].split("</think>")[1])
                answer["values"][field], answer["units"][field] = number, unit
                generated["generated_text"] = "</think>" + json.dumps(answer)
                self.assertTrue(comparison.score_case(rows[index], generated)["passed"])

    def test_tiny_si_conversion_does_not_accept_zero_or_wrong_dimension(self):
        case = comparison.cases()[2]
        for number, unit in ((0, "J"), (2, "V"), (0, "eV")):
            generated = good_generation(case)
            answer = comparison.final_object(generated["generated_text"].split("</think>")[1])
            answer["values"]["work_function"] = number
            answer["units"]["work_function"] = unit
            generated["generated_text"] = "</think>" + json.dumps(answer)
            self.assertFalse(comparison.score_case(case, generated)["passed"])

    def test_truncation_timeout_and_error_fail_even_if_answer_looks_correct(self):
        case = comparison.cases()[0]
        for reason in ("length", "timeout", "error"):
            generated = good_generation(case)
            generated["finish_reason"] = reason
            scored = comparison.score_case(case, generated)
            self.assertFalse(scored["passed"])
            self.assertEqual(scored["failure"], reason)
            self.assertIsNone(scored["final_answer"])

    def test_unclosed_thinking_not_mistaken_for_answer(self):
        case = comparison.cases()[0]
        generated = good_generation(case)
        generated["generated_text"] = generated["generated_text"].replace("</think>", "")
        self.assertEqual(comparison.score_case(case, generated)["failure"], "thinking_not_closed")
        generated["generated_text"] = "hidden</think>"
        self.assertEqual(comparison.score_case(case, generated)["failure"], "final_answer_missing")

    def test_final_json_can_be_fenced_and_last_root_object_wins(self):
        case = comparison.cases()[0]
        generated = good_generation(case)
        good = generated["generated_text"].split("</think>")[1]
        generated["generated_text"] = '</think>{"values":{},"units":{}}\n```json\n' + good + '\n```'
        self.assertTrue(comparison.score_case(case, generated)["passed"])

    def test_duplicate_keys_nan_booleans_and_missing_fields_fail(self):
        case = comparison.cases()[0]
        for answer in (
            '{"values":{"velocity":3,"velocity":4,"energy_loss":27},"units":{"velocity":"m/s","energy_loss":"J"}}',
            '{"values":{"velocity":NaN,"energy_loss":27},"units":{"velocity":"m/s","energy_loss":"J"}}',
            '{"values":{"velocity":true,"energy_loss":27},"units":{"velocity":"m/s","energy_loss":"J"}}',
            '{"values":{"velocity":3},"units":{"velocity":"m/s"}}',
        ):
            generated = good_generation(case)
            generated["generated_text"] = "</think>" + answer
            self.assertEqual(comparison.score_case(case, generated)["failure"], "format_error")

    def test_missing_rubric_requires_null_no_invented_grade(self):
        case = comparison.cases()[-1]
        self.assertTrue(comparison.score_case(case, good_generation(case))["passed"])
        for score in (100, 0, "null"):
            generated = good_generation(case)
            generated["generated_text"] = '</think>' + json.dumps({
                "status": "unscorable", "score": score, "reason_code": "official_rubric_missing"})
            self.assertFalse(comparison.score_case(case, generated)["passed"])

    def test_different_foundation_engine_precision_prompt_or_seed_rejected(self):
        for kind in ("weights", "engine", "precision", "prompt", "seed", "order", "adapter"):
            base, adapted = bundle(self.plan, "base"), bundle(self.plan, "adapted")
            if kind == "weights": adapted["inference_identity"]["base_weights_sha256"] = "e" * 64
            elif kind == "engine": adapted["inference_identity"]["engine"] = "other"
            elif kind == "precision": adapted["inference_identity"]["quantization"] = "other"
            elif kind == "prompt": adapted["cases"][0]["prompt_sha256"] = "e" * 64
            elif kind == "seed": adapted["generation_settings"]["seed"] += 1
            elif kind == "order": adapted["cases"].reverse()
            elif kind == "adapter": adapted["adapter_model_sha256"] = "e" * 64
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                comparison.score_comparison(self.plan, base, adapted)

    def test_frozen_plan_and_missing_pins_rejected_before_callbacks(self):
        called = []
        for plan in (comparison.build_plan(), {**self.plan, "case_count": 9}):
            with self.assertRaises(ValueError):
                comparison.run_sequential(plan, IDENTITY, lambda *args: called.append("generate"),
                                          lambda *args: called.append("attach"))
        self.assertEqual(called, [])

    def test_one_backend_preload_once_then_fixed_eight_base_adapted_pairs_no_reset(self):
        events = []
        rows = comparison.cases()
        def generate(messages, settings, mode):
            index = sum(event.startswith("generate") for event in events) // 2
            self.assertEqual(messages, rows[index]["messages"])
            self.assertEqual(settings, comparison.SETTINGS)
            events.append("generate_" + mode)
            # Mutating callback inputs must not mutate frozen cases/settings.
            messages.clear()
            settings.clear()
            return good_generation(rows[index])
        def attach(plan):
            events.append("attach")
            return {key: plan[key] for key in ("adapter_model_sha256", "adapter_config_sha256")}
        report = comparison.run_sequential(self.plan, IDENTITY, generate, attach)
        self.assertEqual(events, ["attach"] + [event for _ in range(8)
                                               for event in ("generate_base", "generate_adapted")])
        self.assertEqual(report["results"]["adapted"]["passed_cases"], 8)

    def test_wrong_attach_hash_stops_before_adapted_generation(self):
        generated = []
        def generate(*args):
            index = len(generated)
            generated.append(index)
            return good_generation(comparison.cases()[index])
        with self.assertRaisesRegex(ValueError, "attach_binding"):
            comparison.run_sequential(self.plan, IDENTITY, generate, lambda _: {})
        self.assertEqual(len(generated), 0)

    def test_oversized_result_and_unknown_thinking_format_are_failures(self):
        case = comparison.cases()[0]
        generated = good_generation(case)
        generated["generated_text"] = "가" * comparison.MAX_RESULT_TEXT
        self.assertEqual(comparison.score_case(case, generated)["failure"], "invalid_generated_text")
        generated = good_generation(case)
        generated["thinking_format"] = "assumed_final"
        self.assertEqual(comparison.score_case(case, generated)["failure"], "unsupported_thinking_format")


if __name__ == "__main__":
    unittest.main()

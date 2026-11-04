"""CPU-only budget checks. No Runpod requests, secrets or paid work."""
from dataclasses import replace
from decimal import Decimal
import unittest

from training_budget import (BudgetError, BudgetLedger, BudgetPolicy, PodQuote, RunRecord,
                             bounded_wait_seconds, elapsed_seconds, remaining_seconds,
                             reserve_run, settle_run, should_stop, validate_observed_pod)


class TrainingBudgetTests(unittest.TestCase):
    def policy(self, **kw):
        return BudgetPolicy(fx_krw_per_usd_upper="2000", **kw)

    def reserve(self, ledger=None, **kw):
        args = dict(run_id="chat-1", role="chat", quote=PodQuote("2"), now_monotonic=100,
                    requested_seconds=3600, hard_max_seconds=3600)
        args.update(kw)
        return reserve_run(ledger or BudgetLedger(self.policy()), **args)

    def pod(self, **kw):
        return {"costPerHr": "2", "adjustedCostPerHr": 1.8, "containerDiskInGb": 200,
                "volumeInGb": 0, "gpu": {"count": 1}, **kw}

    def test_policy_requires_explicit_finite_fx_and_never_exceeds_authorized_total(self):
        for bad in (None, 0, -1, "NaN", "Infinity", True, "not a price"):
            with self.subTest(bad=bad), self.assertRaises(BudgetError):
                BudgetPolicy(fx_krw_per_usd_upper=bad)
        for kwargs in ({"budget_krw": 30001}, {"reserve_krw": 0}, {"reserve_krw": 1000},
                       {"reserve_krw": 30000}, {"tax_multiplier": 0.9}, {"tax_multiplier": 1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(BudgetError):
                self.policy(**kwargs)
        self.assertEqual(self.policy().spendable_krw, Decimal(27000))

    def test_restored_ledger_rejects_negative_nonfinite_or_mismatched_accounting(self):
        ledger = self.reserve()
        plan = ledger.runs[0].plan
        for bad in (-1, "NaN", "Infinity", True):
            with self.subTest(bad=bad), self.assertRaises(BudgetError):
                RunRecord(plan, bad)
        with self.assertRaisesRegex(BudgetError, "invalid run"):
            BudgetLedger(self.policy(), runs=({"charged_krw": -100000},))
        with self.assertRaisesRegex(BudgetError, "reservation"):
            replace(plan, reserved_krw=1)
        with self.assertRaisesRegex(BudgetError, "FX/tax"):
            BudgetLedger(BudgetPolicy(2500), runs=ledger.runs)

    def test_missing_or_zero_compute_and_storage_price_fail_closed(self):
        for bad in (None, 0, -1, "NaN", "Infinity", True):
            with self.subTest(bad=bad), self.assertRaises(BudgetError):
                PodQuote(bad)
        for bad in (None, 0, "0.09"):
            with self.subTest(bad=bad), self.assertRaises(BudgetError):
                PodQuote("2", disk_usd_per_gb_month_upper=bad)
        with self.assertRaisesRegex(BudgetError, "network"):
            PodQuote("2", network_volume_gb=100)

    def test_gpu_plus_disk_fx_tax_and_cleanup_are_reserved_up_front(self):
        ledger = self.reserve()
        plan = ledger.runs[-1].plan
        # 200GB * $0.10 / shortest month (672h), plus TOTAL Pod compute.
        hourly = (Decimal(2) + Decimal(20) / 672) * 2000 * Decimal("1.10")
        self.assertEqual(plan.krw_per_hour_upper, hourly)
        self.assertEqual(plan.run_seconds, 3600)
        self.assertEqual(plan.cleanup_grace_seconds, 120)
        self.assertEqual(plan.reserved_krw, (hourly * Decimal(3720) / 3600).to_integral_value(rounding="ROUND_CEILING"))
        self.assertEqual(ledger.spent_krw, 0)
        self.assertEqual(ledger.available_krw, Decimal(27000) - plan.reserved_krw)

    def test_total_budget_is_shared_by_roles_and_retries_after_confirmed_deletion(self):
        first = self.reserve(quote=PodQuote("5"), requested_seconds=7200, hard_max_seconds=7200)
        after = settle_run(first, "chat-1", 7300, deletion_confirmed=True)
        second = self.reserve(after, run_id="solver-1", role="solver", quote=PodQuote("5"),
                              now_monotonic=7400, requested_seconds=7200, hard_max_seconds=7200)
        self.assertLess(second.runs[1].plan.run_seconds, 7200)
        self.assertLessEqual(second.spent_krw + second.reserved_krw + second.policy.reserve_krw, 30000)
        with self.assertRaises(BudgetError):
            self.reserve(second, run_id="chat-retry", quote=PodQuote("5"))
        with self.assertRaisesRegex(BudgetError, "already"):
            self.reserve(first, role="solver")

    def test_settled_spend_and_prior_batch_spend_reduce_next_role_allowance(self):
        ledger = self.reserve(BudgetLedger(self.policy(), prior_spend_krw=10000))
        after = settle_run(ledger, "chat-1", 3700, deletion_confirmed=True)
        self.assertEqual(after.reserved_krw, 0)
        self.assertGreater(after.spent_krw, 14000)
        self.assertLess(after.spent_krw, 15000)
        next_role = self.reserve(after, run_id="solver-1", role="solver", requested_seconds=10800, hard_max_seconds=10800)
        self.assertLess(next_role.runs[-1].plan.run_seconds, 10800)
        self.assertLessEqual(next_role.spent_krw + next_role.reserved_krw + next_role.policy.reserve_krw, 30000)

    def test_minimum_runtime_cleanup_and_hard_time_ceiling_fail_closed(self):
        for kwargs in ({"hard_max_seconds": 18001}, {"cleanup_grace_seconds": 0},
                       {"requested_seconds": 0}, {"hard_max_seconds": 1.5}):
            with self.subTest(kwargs=kwargs), self.assertRaises(BudgetError):
                self.reserve(**kwargs)
        with self.assertRaisesRegex(BudgetError, "minimum runtime"):
            self.reserve(BudgetLedger(self.policy(), prior_spend_krw=26999))
        plan = self.reserve(requested_seconds=7200, hard_max_seconds=600).runs[0].plan
        self.assertEqual(plan.run_seconds, 600)

    def test_monotonic_deadline_includes_download_setup_and_upload_time(self):
        plan = self.reserve().runs[0].plan
        self.assertFalse(should_stop(plan, 3699))
        self.assertTrue(should_stop(plan, 3700))
        self.assertEqual(remaining_seconds(plan, 3699), 1)
        self.assertEqual(bounded_wait_seconds(plan, 3699, 60), 1)
        self.assertEqual(bounded_wait_seconds(plan, 9999, 60), 0)
        self.assertEqual(plan.billing_deadline_monotonic, 3820)
        for bad in (99, None, "NaN", -10):
            with self.subTest(bad=bad), self.assertRaises(BudgetError):
                elapsed_seconds(plan, bad)

    def test_creation_response_rejects_missing_rates_and_unexpected_resources(self):
        plan = self.reserve().runs[0].plan
        validate_observed_pod(plan, self.pod())
        cases = [self.pod(costPerHr=None), self.pod(costPerHr=0), self.pod(costPerHr="2.01"),
                 self.pod(adjustedCostPerHr=2.5), self.pod(containerDiskInGb=201),
                 self.pod(volumeInGb=1), self.pod(gpu={"count": 2}), self.pod(gpu=None),
                 self.pod(networkVolumeId="persistent"), self.pod(networkVolume={"size": 10}),
                 self.pod(volumeInGb=None)]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(BudgetError):
                validate_observed_pod(plan, case)

    def test_a_stopped_pod_does_not_release_its_reservation(self):
        ledger = self.reserve()
        for confirmation in (False, None, "true", 1):
            with self.subTest(confirmation=confirmation), self.assertRaisesRegex(BudgetError, "not confirmed"):
                settle_run(ledger, "chat-1", 3700, deletion_confirmed=confirmation)
        self.assertGreater(ledger.reserved_krw, 0)
        with self.assertRaisesRegex(BudgetError, "not settled"):
            self.reserve(ledger, run_id="solver-1", role="solver")
        settled = settle_run(ledger, "chat-1", 3700, deletion_confirmed=True)
        with self.assertRaisesRegex(BudgetError, "already settled"):
            settle_run(settled, "chat-1", 3700, deletion_confirmed=True)

    def test_overrun_or_higher_provider_bill_is_recorded_and_blocks_more_work(self):
        ledger = self.reserve()
        overrun = settle_run(ledger, "chat-1", 30000, deletion_confirmed=True)
        self.assertTrue(overrun.over_budget)
        self.assertGreater(overrun.spent_krw, 30000)
        with self.assertRaises(BudgetError):
            self.reserve(overrun, run_id="solver-1", role="solver")
        billed = settle_run(ledger, "chat-1", 200, deletion_confirmed=True, observed_cost_usd=15)
        self.assertEqual(billed.spent_krw, 33000)
        self.assertTrue(billed.over_budget)

    def test_subsecond_costs_round_up_and_planning_is_immutable(self):
        empty = BudgetLedger(self.policy())
        ledger = self.reserve(empty)
        self.assertEqual(empty.runs, ())
        settled = settle_run(ledger, "chat-1", "100.001", deletion_confirmed=True)
        self.assertEqual(settled.spent_krw, 2)
        self.assertIsNone(ledger.runs[0].charged_krw)


if __name__ == "__main__":
    unittest.main()

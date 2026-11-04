"""Pure, fail-closed cost planning for one bounded Hasla AI training batch.

No API, clock, secret, filesystem or GPU access occurs in this module. The runner
must keep ONE ledger for every role/retry in the authorized batch, persist it
outside a public repository, and pass ``time.monotonic()`` before creating a Pod.
Reserve first; validate the creation response before starting work; stop at the
run deadline; DELETE and confirm absence before settling. BudgetError during a
live run means terminate, not continue with an assumed free/unknown price.

Official Runpod references checked 2026-11-04:
https://docs.runpod.io/pods/pricing
https://docs.runpod.io/api-reference/pods/POST/pods
Pods charge compute/storage per second. Container and running volume storage are
$0.10/GB/month; stopped volume storage is $0.20/GB/month. Network volumes survive
Pod deletion and are deliberately unsupported here. The API's costPerHr is a
post-creation observation, not a pre-creation price cap. The caller must obtain a
verified compute-rate ceiling first and terminate if the observed rate exceeds
it. This is a conservative estimate under explicit rate/FX/cleanup assumptions,
not a provider-enforced spending cap or protection against a dead runner.
"""
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR
from typing import Mapping


MAX_BUDGET_KRW = Decimal("30000")
MAX_RUN_SECONDS = 5 * 3600
# Dividing monthly storage by the shortest month overestimates hourly charges.
MONTH_HOURS_LOWER = Decimal(28 * 24)
DISK_USD_PER_GB_MONTH = Decimal("0.10")
STOPPED_VOLUME_USD_PER_GB_MONTH = Decimal("0.20")


class BudgetError(ValueError):
    """Missing/invalid evidence or an exhausted bound; no new paid work allowed."""


def _number(value, name, *, positive=False):
    if isinstance(value, bool) or value is None:
        raise BudgetError(f"{name} must be a finite number")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise BudgetError(f"{name} must be a finite number") from None
    if not number.is_finite() or number < 0 or (positive and number == 0):
        raise BudgetError(f"{name} must be {'positive' if positive else 'nonnegative'} and finite")
    return number


def _integer(value, name, *, minimum=0):
    number = _number(value, name)
    if number != number.to_integral_value() or number < minimum:
        raise BudgetError(f"{name} must be an integer >= {minimum}")
    return int(number)


def _won(value):
    return value.to_integral_value(rounding=ROUND_CEILING)


@dataclass(frozen=True)
class BudgetPolicy:
    # An explicitly chosen upper FX bound, including any expected card spread.
    # It is an input, not a live exchange-rate claim or an automatically fetched rate.
    fx_krw_per_usd_upper: Decimal
    budget_krw: Decimal = MAX_BUDGET_KRW
    reserve_krw: Decimal = Decimal("3000")
    tax_multiplier: Decimal = Decimal("1.10")

    def __post_init__(self):
        for name in ("fx_krw_per_usd_upper", "budget_krw", "reserve_krw", "tax_multiplier"):
            object.__setattr__(self, name, _number(getattr(self, name), name, positive=True))
        if self.budget_krw > MAX_BUDGET_KRW:
            raise BudgetError("budget_krw exceeds the authorized 30000 KRW maximum")
        if self.reserve_krw < 3000 or self.reserve_krw >= self.budget_krw:
            raise BudgetError("reserve_krw must be at least 3000 and below budget_krw")
        if self.fx_krw_per_usd_upper < 1 or self.tax_multiplier < Decimal("1.10"):
            raise BudgetError("FX bound must be >= 1 and tax multiplier >= 1.10")

    @property
    def spendable_krw(self):
        return self.budget_krw - self.reserve_krw


@dataclass(frozen=True)
class PodQuote:
    # TOTAL compute cost for the entire Pod, not the cost of one of several GPUs.
    gpu_usd_per_hour_upper: Decimal
    container_disk_gb: int = 200
    volume_disk_gb: int = 0
    gpu_count: int = 1
    disk_usd_per_gb_month_upper: Decimal = DISK_USD_PER_GB_MONTH
    network_volume_gb: int = 0

    def __post_init__(self):
        for name in ("gpu_usd_per_hour_upper", "disk_usd_per_gb_month_upper"):
            object.__setattr__(self, name, _number(getattr(self, name), name, positive=True))
        for name in ("container_disk_gb", "volume_disk_gb", "network_volume_gb"):
            object.__setattr__(self, name, _integer(getattr(self, name), name))
        object.__setattr__(self, "gpu_count", _integer(self.gpu_count, "gpu_count", minimum=1))
        if self.disk_usd_per_gb_month_upper < DISK_USD_PER_GB_MONTH:
            raise BudgetError("disk rate is below the verified published running-storage rate")
        if self.network_volume_gb:
            raise BudgetError("persistent network volumes are outside this bounded batch")

    @property
    def hourly_usd_upper(self):
        running_disk = (self.container_disk_gb + self.volume_disk_gb) * self.disk_usd_per_gb_month_upper / MONTH_HOURS_LOWER
        stopped_volume = self.volume_disk_gb * max(STOPPED_VOLUME_USD_PER_GB_MONTH, self.disk_usd_per_gb_month_upper * 2) / MONTH_HOURS_LOWER
        return max(self.gpu_usd_per_hour_upper + running_disk, stopped_volume)


@dataclass(frozen=True)
class RunPlan:
    run_id: str
    role: str
    quote: PodQuote
    started_monotonic: Decimal
    run_seconds: int
    cleanup_grace_seconds: int
    krw_per_hour_upper: Decimal
    reserved_krw: Decimal

    def __post_init__(self):
        if not isinstance(self.run_id, str) or not self.run_id.strip() or len(self.run_id) > 120:
            raise BudgetError("run_id must be a nonempty identifier up to 120 characters")
        if self.role not in ("chat", "solver", "fast") or not isinstance(self.quote, PodQuote):
            raise BudgetError("RunPlan must have a supported role and validated PodQuote")
        for name in ("started_monotonic", "krw_per_hour_upper", "reserved_krw"):
            object.__setattr__(self, name, _number(getattr(self, name), name, positive=name != "started_monotonic"))
        object.__setattr__(self, "run_seconds", _integer(self.run_seconds, "run_seconds", minimum=1))
        object.__setattr__(self, "cleanup_grace_seconds", _integer(self.cleanup_grace_seconds, "cleanup_grace_seconds", minimum=30))
        if self.run_seconds > MAX_RUN_SECONDS:
            raise BudgetError("RunPlan exceeds the 5 hour absolute ceiling")
        minimum_reserved = _won(self.krw_per_hour_upper * (self.run_seconds + self.cleanup_grace_seconds) / 3600)
        if self.reserved_krw < minimum_reserved:
            raise BudgetError("RunPlan reservation is below its billed-time upper bound")

    @property
    def deadline_monotonic(self):
        return self.started_monotonic + self.run_seconds

    @property
    def billing_deadline_monotonic(self):
        return self.deadline_monotonic + self.cleanup_grace_seconds


@dataclass(frozen=True)
class RunRecord:
    plan: RunPlan
    charged_krw: Decimal | None = None

    def __post_init__(self):
        if not isinstance(self.plan, RunPlan):
            raise BudgetError("RunRecord requires a validated RunPlan")
        if self.charged_krw is not None:
            object.__setattr__(self, "charged_krw", _number(self.charged_krw, "charged_krw"))


@dataclass(frozen=True)
class BudgetLedger:
    policy: BudgetPolicy
    runs: tuple[RunRecord, ...] = ()
    # Include earlier charges from this same authorization when resuming a batch.
    prior_spend_krw: Decimal = Decimal("0")

    def __post_init__(self):
        if not isinstance(self.policy, BudgetPolicy):
            raise BudgetError("BudgetLedger requires a validated BudgetPolicy")
        object.__setattr__(self, "prior_spend_krw", _number(self.prior_spend_krw, "prior_spend_krw"))
        object.__setattr__(self, "runs", tuple(self.runs))
        for row in self.runs:
            if not isinstance(row, RunRecord):
                raise BudgetError("BudgetLedger contains an invalid run record")
            expected_hourly = row.plan.quote.hourly_usd_upper * self.policy.fx_krw_per_usd_upper * self.policy.tax_multiplier
            if row.plan.krw_per_hour_upper != expected_hourly:
                raise BudgetError("run pricing does not match the ledger FX/tax policy")
            if row.charged_krw is None and row.plan.reserved_krw > self.policy.spendable_krw:
                raise BudgetError("active reservation exceeds the batch spending limit")
        if sum(row.charged_krw is None for row in self.runs) > 1:
            raise BudgetError("only one active Pod reservation is allowed per batch")
        ids = [row.plan.run_id for row in self.runs]
        if len(ids) != len(set(ids)):
            raise BudgetError("run_id must be unique across every role and retry")

    @property
    def spent_krw(self):
        return self.prior_spend_krw + sum((row.charged_krw for row in self.runs if row.charged_krw is not None), Decimal(0))

    @property
    def reserved_krw(self):
        return sum((row.plan.reserved_krw for row in self.runs if row.charged_krw is None), Decimal(0))

    @property
    def available_krw(self):
        return max(Decimal(0), self.policy.spendable_krw - self.spent_krw - self.reserved_krw)

    @property
    def over_budget(self):
        return self.spent_krw + self.reserved_krw > self.policy.spendable_krw


def reserve_run(ledger, run_id, role, quote, now_monotonic, requested_seconds, hard_max_seconds,
                cleanup_grace_seconds=120, minimum_run_seconds=60):
    """Return a new ledger with affordable seconds locked before Pod creation.

    Downloads, dependency installation, training and adapter upload all share the
    same deadline. Cleanup grace is also reserved at the full hourly upper rate.
    A shorter allowance is returned when the shared remaining budget is smaller
    than the requested runtime. The caller must actually honor that allowance.
    """
    if not isinstance(run_id, str) or not run_id.strip() or len(run_id) > 120:
        raise BudgetError("run_id must be a nonempty identifier up to 120 characters")
    if any(row.plan.run_id == run_id for row in ledger.runs):
        raise BudgetError("run_id was already reserved in this batch")
    if any(row.charged_krw is None for row in ledger.runs):
        raise BudgetError("an earlier Pod is not settled; confirm deletion before starting another role or retry")
    if role not in ("chat", "solver", "fast"):
        raise BudgetError("unknown training role")
    start = _number(now_monotonic, "now_monotonic")
    requested = _integer(requested_seconds, "requested_seconds", minimum=1)
    cap = _integer(hard_max_seconds, "hard_max_seconds", minimum=1)
    grace = _integer(cleanup_grace_seconds, "cleanup_grace_seconds", minimum=30)
    minimum = _integer(minimum_run_seconds, "minimum_run_seconds", minimum=1)
    if cap > MAX_RUN_SECONDS:
        raise BudgetError("hard_max_seconds exceeds the 5 hour absolute ceiling")
    hourly = quote.hourly_usd_upper * ledger.policy.fx_krw_per_usd_upper * ledger.policy.tax_multiplier
    affordable = int((ledger.available_krw * 3600 / hourly).to_integral_value(rounding=ROUND_FLOOR))
    seconds = min(requested, cap, affordable - grace)
    if seconds < minimum:
        raise BudgetError("remaining batch budget cannot cover minimum runtime and cleanup")
    reserved = _won(hourly * (seconds + grace) / 3600)
    if reserved > ledger.available_krw:
        raise BudgetError("rounded reservation exceeds the remaining batch budget")
    plan = RunPlan(run_id, role, quote, start, seconds, grace, hourly, reserved)
    return replace(ledger, runs=ledger.runs + (RunRecord(plan),))


def elapsed_seconds(plan, now_monotonic):
    """Elapsed billing time since BEFORE creation, from the same monotonic clock."""
    now = _number(now_monotonic, "now_monotonic")
    if now < plan.started_monotonic:
        raise BudgetError("monotonic clock moved backwards or belongs to another process")
    return now - plan.started_monotonic


def remaining_seconds(plan, now_monotonic):
    return max(Decimal(0), Decimal(plan.run_seconds) - elapsed_seconds(plan, now_monotonic))


def should_stop(plan, now_monotonic):
    return remaining_seconds(plan, now_monotonic) == 0


def bounded_wait_seconds(plan, now_monotonic, requested_wait=10):
    """Never let a poll or API timeout extend beyond the termination deadline."""
    return min(_number(requested_wait, "requested_wait", positive=True), remaining_seconds(plan, now_monotonic))


def validate_observed_pod(plan, pod):
    """Reject unknown/over-ceiling rates and unexpected billable resources.

    The Pod can already be billing when this raises. The caller must DELETE it
    immediately and keep the ledger reservation until absence is confirmed.
    """
    if not isinstance(pod, Mapping):
        raise BudgetError("Pod creation response is missing")
    rate = _number(pod.get("costPerHr"), "costPerHr", positive=True)
    if "adjustedCostPerHr" in pod and pod["adjustedCostPerHr"] is not None:
        rate = max(rate, _number(pod["adjustedCostPerHr"], "adjustedCostPerHr", positive=True))
    if rate > plan.quote.gpu_usd_per_hour_upper:
        raise BudgetError("observed Pod compute rate exceeds the reserved rate ceiling")
    if pod.get("networkVolumeId") or pod.get("networkVolume"):
        raise BudgetError("Pod unexpectedly has a persistent network volume")
    for field, allowed in (("containerDiskInGb", plan.quote.container_disk_gb), ("volumeInGb", plan.quote.volume_disk_gb)):
        actual = _integer(pod.get(field), field)
        if actual > allowed:
            raise BudgetError(f"{field} exceeds the reserved storage size")
    gpu = pod.get("gpu")
    count = gpu.get("count") if isinstance(gpu, Mapping) else pod.get("gpuCount")
    if _integer(count, "gpu count", minimum=1) != plan.quote.gpu_count:
        raise BudgetError("observed GPU count differs from the reserved configuration")


def settle_run(ledger, run_id, now_monotonic, deletion_confirmed, observed_cost_usd=None):
    """Release a reservation only after confirmed deletion, charging elapsed time.

    An overrun is recorded conservatively, even if it exhausts the reserve or
    exceeds the budget; it is never hidden by clipping to the allowance. New
    reservations then fail. A provider bill can increase this charge, never
    reduce it below elapsed time at the reserved upper rate.
    """
    if deletion_confirmed is not True:
        raise BudgetError("Pod deletion is not confirmed; retain the full reservation")
    index = next((i for i, row in enumerate(ledger.runs) if row.plan.run_id == run_id), None)
    if index is None:
        raise BudgetError("run_id was not reserved")
    record = ledger.runs[index]
    if record.charged_krw is not None:
        raise BudgetError("run_id was already settled")
    seconds = elapsed_seconds(record.plan, now_monotonic).to_integral_value(rounding=ROUND_CEILING)
    charge = _won(record.plan.krw_per_hour_upper * seconds / 3600)
    if observed_cost_usd is not None:
        actual = _number(observed_cost_usd, "observed_cost_usd")
        charge = max(charge, _won(actual * ledger.policy.fx_krw_per_usd_upper * ledger.policy.tax_multiplier))
    rows = list(ledger.runs)
    rows[index] = replace(record, charged_krw=charge)
    return replace(ledger, runs=tuple(rows))

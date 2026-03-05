"""
Analytics service: VDOT, Daniels training pace zones, ATL/CTL/TSB, hrTSS.

Mathematical sources:
- VDOT: Daniels & Gilbert (1979), Oxygen Power. Confirmed from appendix.
  VO2(V)      = -4.60 + 0.182258·V + 0.000104·V²      (V in m/min)
  %VO2max(T)  = 0.8 + 0.1894393·e^(-0.012778·T) + 0.2989558·e^(-0.1932605·T)  (T in min)
  Vel(VO2)    = 29.54 + 5.000663·VO2 - 0.007546·VO2²  (back-solve)
- HR-adjusted VDOT: Swain DP et al. (1994). Target heart rates for the development of
  cardiorespiratory fitness. Med Sci Sports Exerc. 26(1):112-116.
  %VO2max = 1.0197 × %HRR + 0.01    where %HRR = (HR - HR_rest) / (HR_max - HR_rest)
- ATL/CTL/TSB: Morton, Fitz-Clarke & Banister (1990), J Appl Physiol 69(3):1171-1177.
- TRIMP:       Banister (1991) in MacDougall et al. (Eds.), Physiological Testing.
- Training zones: Daniels (2022), Daniels' Running Formula 4th ed., Figure 4.1.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# VDOT system (Daniels-Gilbert equations)
# ---------------------------------------------------------------------------

def _vo2_from_velocity(v_m_min: float) -> float:
    """VO2 (mL·kg⁻¹·min⁻¹) from running velocity in m/min."""
    return -4.60 + 0.182258 * v_m_min + 0.000104 * v_m_min ** 2


def _pct_vo2max_from_duration(t_min: float) -> float:
    """Fraction of VO2max sustainable for a race of t_min minutes."""
    return (0.8
            + 0.1894393 * math.exp(-0.012778 * t_min)
            + 0.2989558 * math.exp(-0.1932605 * t_min))


def _velocity_from_vo2(vo2: float) -> float:
    """Running velocity (m/min) from VO2 (m/min), inverse of _vo2_from_velocity."""
    return 29.54 + 5.000663 * vo2 - 0.007546 * vo2 ** 2


def compute_vdot(distance_m: float, time_s: float) -> float:
    """
    Compute VDOT from a race/time trial result (assumes full effort).

    NOTE: Use compute_vdot_hr_adjusted() for training runs — this formula
    assumes the runner is racing at maximum sustainable effort for the
    duration. Applying it to easy training runs will underestimate VDOT.
    """
    if distance_m <= 0 or time_s <= 0:
        raise ValueError("distance_m and time_s must be positive")

    t_min = time_s / 60.0
    v_m_min = distance_m / t_min
    vo2 = _vo2_from_velocity(v_m_min)
    pct = _pct_vo2max_from_duration(t_min)
    if pct <= 0:
        raise ValueError("Duration too long for VDOT computation")
    return vo2 / pct


def compute_vdot_hr_adjusted(
    distance_m: float,
    time_s: float,
    avg_hr: float,
    hr_max: int,
    hr_rest: int = 50,
) -> float:
    """
    HR-adjusted VDOT estimate for training runs at sub-maximal effort.

    Uses Swain et al. (1994): %VO2max = 1.0197 × %HRR + 0.01
    where %HRR = (HR_avg - HR_rest) / (HR_max - HR_rest)

    Then VDOT = VO2_at_pace / %VO2max

    This gives accurate VDOT estimates from easy/moderate training runs
    provided hr_max and hr_rest are set correctly.
    """
    if distance_m <= 0 or time_s <= 0:
        raise ValueError("distance_m and time_s must be positive")
    hr_range = hr_max - hr_rest
    if hr_range <= 0:
        raise ValueError("hr_max must be greater than hr_rest")

    v_m_min = distance_m / (time_s / 60.0)
    vo2_at_pace = _vo2_from_velocity(v_m_min)
    if vo2_at_pace <= 0:
        raise ValueError("Pace too slow for valid VO2 estimate")

    pct_hrr = (avg_hr - hr_rest) / hr_range
    pct_hrr = max(0.1, min(pct_hrr, 1.0))
    pct_vo2max = min(1.0197 * pct_hrr + 0.01, 1.0)  # Swain (1994)

    return vo2_at_pace / pct_vo2max


def predict_race_time_s(vdot: float, target_distance_m: float) -> float:
    """
    Predict race time (seconds) for target_distance_m given a VDOT.

    Uses Newton-Raphson iteration (as described in Oxygen Power Appendix B)
    to find T such that VDOT(target_distance_m, T) = vdot.

    Args:
        vdot:              VDOT value
        target_distance_m: race distance in metres

    Returns:
        Predicted time in seconds
    """
    if vdot <= 0 or target_distance_m <= 0:
        raise ValueError("vdot and target_distance_m must be positive")

    # Initial guess: velocity at 100% VO2max → time
    v_guess = _velocity_from_vo2(vdot)  # m/min (rough upper bound)
    if v_guess <= 0:
        v_guess = 200.0
    t_guess = target_distance_m / v_guess  # minutes

    # Newton-Raphson (5 iterations is sufficient)
    for _ in range(10):
        v = target_distance_m / t_guess
        vo2 = _vo2_from_velocity(v)
        pct = _pct_vo2max_from_duration(t_guess)
        f_t = vo2 / pct - vdot

        # Derivatives
        dvo2_dt = (0.182258 + 2 * 0.000104 * v) * (-target_distance_m / t_guess ** 2)
        dpct_dt = (-0.012778 * 0.1894393 * math.exp(-0.012778 * t_guess)
                   - 0.1932605 * 0.2989558 * math.exp(-0.1932605 * t_guess))
        df_dt = (dvo2_dt * pct - vo2 * dpct_dt) / pct ** 2

        if abs(df_dt) < 1e-12:
            break
        t_guess -= f_t / df_dt
        if t_guess <= 0:
            t_guess = 0.1

    return t_guess * 60.0  # convert to seconds


# ---------------------------------------------------------------------------
# Daniels training pace zones
# ---------------------------------------------------------------------------

@dataclass
class PaceZones:
    """Training pace zones in seconds per km (lower = faster)."""
    easy_lo: float    # E pace slow end (s/km)
    easy_hi: float    # E pace fast end (s/km)
    marathon: float   # M pace (s/km)
    threshold: float  # T pace (s/km)
    interval: float   # I pace (s/km)
    repetition: float # R pace (s/km)


def compute_pace_zones(vdot: float) -> PaceZones:
    """
    Compute Daniels training pace zones from VDOT.

    Zones are derived from Figure 4.1 of Daniels' Running Formula (4th ed.):
      E:  59-74% VO2max
      M:  75-84% VO2max (midpoint 79.5%)
      T:  85-88% VO2max (midpoint 86.5%)
      I:  95-100% VO2max (midpoint 97.5%)
      R:  105-120% VO2max (representative 107%)

    Args:
        vdot: VDOT value

    Returns:
        PaceZones dataclass with paces in s/km
    """
    def pace_s_per_km(fraction: float) -> float:
        vo2_target = vdot * fraction
        v_m_min = _velocity_from_vo2(vo2_target)
        if v_m_min <= 0:
            return 9999.0
        # m/min → s/km
        return 1000.0 / v_m_min * 60.0

    return PaceZones(
        easy_lo=pace_s_per_km(0.59),   # slow end of E
        easy_hi=pace_s_per_km(0.74),   # fast end of E
        marathon=pace_s_per_km(0.795), # midpoint of M (75-84%)
        threshold=pace_s_per_km(0.865),# midpoint of T (85-88%)
        interval=pace_s_per_km(0.975), # midpoint of I (95-100%)
        repetition=pace_s_per_km(1.07),# representative R (~107%)
    )


# ---------------------------------------------------------------------------
# Grade-adjusted pace (Minetti et al. 2002)
# ---------------------------------------------------------------------------

def _minetti_cr(grade: float) -> float:
    """
    Energy cost of running as a function of grade (J·kg⁻¹·m⁻¹).
    Minetti et al. (2002), J Appl Physiol 93(3):1039-1046.
    grade: fractional slope (e.g. 0.01 = 1%)
    """
    i = grade
    return (155.4 * i**5 - 30.4 * i**4 - 43.3 * i**3
            + 46.3 * i**2 + 19.5 * i + 3.6)


def compute_gap(pace_s_per_km: float, grade: float) -> float:
    """
    Grade-adjusted pace using the Minetti (2002) polynomial.

    Args:
        pace_s_per_km: actual pace in s/km
        grade:         fractional gradient (+ve uphill, -ve downhill)

    Returns:
        Grade-adjusted pace in s/km (effort-equivalent flat pace)
    """
    cr_flat = _minetti_cr(0.0)   # 3.6 J·kg⁻¹·m⁻¹
    cr_grade = _minetti_cr(grade)
    if cr_flat <= 0:
        return pace_s_per_km
    effort_ratio = cr_grade / cr_flat
    if effort_ratio <= 0:
        return pace_s_per_km
    return pace_s_per_km / effort_ratio


# ---------------------------------------------------------------------------
# TRIMP & hrTSS
# ---------------------------------------------------------------------------

def compute_trimp(
    datapoints: List[Dict],
    hr_rest: int = 50,
    hr_max: int = 190,
    sex: str = "male",
) -> float:
    """
    Compute Banister TRIMP for an activity.
    Banister (1991) in MacDougall et al. (Eds.), Physiological Testing of Elite Athletes.

    Args:
        datapoints: list of dicts with 'heart_rate' (int) and 'timestamp' (datetime)
        hr_rest:    resting heart rate (bpm)
        hr_max:     maximum heart rate (bpm)
        sex:        "male" (b=1.92) or "female" (b=1.67)

    Returns:
        TRIMP score (arbitrary units)
    """
    b = 1.92 if sex == "male" else 1.67
    hr_range = hr_max - hr_rest
    if hr_range <= 0:
        return 0.0

    trimp = 0.0
    prev = None
    for dp in datapoints:
        if dp.get("heart_rate") is None:
            prev = dp
            continue
        if prev is not None and prev.get("heart_rate") is not None:
            dt_min = (dp["timestamp"] - prev["timestamp"]).total_seconds() / 60.0
            hr_avg = (dp["heart_rate"] + prev["heart_rate"]) / 2.0
            delta_hr = (hr_avg - hr_rest) / hr_range
            delta_hr = max(0.0, min(delta_hr, 1.0))
            trimp += dt_min * delta_hr * math.exp(b * delta_hr)
        prev = dp

    return trimp


def compute_hrtss(trimp: float, lthr: Optional[int] = None) -> float:
    """
    Convert TRIMP to approximate hrTSS (TrainingPeaks-compatible units).

    TSS=100 corresponds to 1 hour at lactate threshold. An hour at LTHR
    produces TRIMP ≈ 60 × 0.64 × e^(1.92×0.64) ≈ 60 × 0.64 × 3.43 ≈ 131.7
    for a typical male runner (delta_HR ≈ 0.64 at LTHR).

    This is an approximation; TrainingPeaks uses a proprietary zone-based
    mapping. The scaling below gives reasonable TSS=100/hr-at-LTHR.

    Args:
        trimp:  Banister TRIMP value
        lthr:   lactate threshold HR (unused in this approximation, reserved)

    Returns:
        Approximate hrTSS score
    """
    # Empirical scaling: 1 hour at LTHR ≈ TRIMP 131.7 → TSS 100
    trimp_per_100_tss = 131.7
    return (trimp / trimp_per_100_tss) * 100.0


# ---------------------------------------------------------------------------
# ATL / CTL / TSB  (Banister impulse-response model, Morton et al. 1990)
# ---------------------------------------------------------------------------

TAU_CTL = 42.0   # fitness time constant (days)
TAU_ATL = 7.0    # fatigue time constant (days)

_ALPHA_CTL = math.exp(-1.0 / TAU_CTL)
_ALPHA_ATL = math.exp(-1.0 / TAU_ATL)


@dataclass
class TrainingLoad:
    ctl: float  # Chronic Training Load ("fitness")
    atl: float  # Acute Training Load ("fatigue")
    tsb: float  # Training Stress Balance ("form") = CTL - ATL


def compute_training_loads(
    tss_by_date: Dict[date, float],
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[date, TrainingLoad]:
    """
    Compute daily ATL, CTL, TSB via EWMA recurrence (Morton et al. 1990).

    CTL_t = CTL_{t-1} × α_CTL + TSS_t × (1 - α_CTL)
    ATL_t = ATL_{t-1} × α_ATL + TSS_t × (1 - α_ATL)
    TSB_t = CTL_t - ATL_t

    Args:
        tss_by_date: dict mapping date → daily TSS (0 for rest days)
        start_date:  first date to output (default: earliest date in tss_by_date)
        end_date:    last date to output (default: latest date in tss_by_date)

    Returns:
        Dict mapping date → TrainingLoad
    """
    if not tss_by_date:
        return {}

    d_min = start_date or min(tss_by_date.keys())
    d_max = end_date or max(tss_by_date.keys())

    ctl = 0.0
    atl = 0.0
    result: Dict[date, TrainingLoad] = {}

    current = d_min
    while current <= d_max:
        tss = tss_by_date.get(current, 0.0)
        ctl = ctl * _ALPHA_CTL + tss * (1 - _ALPHA_CTL)
        atl = atl * _ALPHA_ATL + tss * (1 - _ALPHA_ATL)
        result[current] = TrainingLoad(ctl=ctl, atl=atl, tsb=ctl - atl)
        current += timedelta(days=1)

    return result

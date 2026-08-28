"""
Single source of truth for the fixed-horizon estimand and the follow-up
adequacy rule (protocol S5). Every script imports from here so the
boundary conventions can never diverge.

Fixed-horizon estimand
----------------------
  Outcome: CRC death BY H months  <=>  css_event == 1 AND T <= H.
  Observable population: patients whose H-month status is known -
      event by H (T <= H, E == 1)  OR  followed at least to H (T >= H).
  Excluded: event-free with T < H (status at H unknown = censored before H).
  Boundary: an event exactly at T == H counts as an event by H.
  Event-free at exactly T == H counts as observed no-event.

Follow-up adequacy (S5)
-----------------------
  Among EVENT-FREE patients only (denominator), the share with follow-up
  shorter than H. Trigger: > 0.50 in either group's TEST window flips the
  primary horizon to 36 months (decision made before any modeling).
"""
import numpy as np
import pandas as pd

from config import HORIZON_MONTHS

ADEQUACY_TRIGGER = 0.50


def horizon_labels(T, E, H: int = HORIZON_MONTHS):
    """Return (observable_mask, y_h) as numpy bool/int arrays."""
    T = np.asarray(T, dtype=float)
    E = np.asarray(E, dtype=int)
    y_h = ((E == 1) & (T <= H)).astype(int)
    observable = (T >= H) | ((E == 1) & (T <= H))
    return observable, y_h


def horizon_frame(df: pd.DataFrame, H: int = HORIZON_MONTHS) -> pd.DataFrame:
    """Observable subcohort with y_h column (see module docstring)."""
    obs, y = horizon_labels(df.survival_months, df.css_event, H)
    sub = df[obs].copy()
    sub["y_h"] = y[obs]
    return sub


def event_free_short_followup_share(T, E, H: int = HORIZON_MONTHS) -> float:
    """Share of EVENT-FREE patients with follow-up < H (denominator =
    event-free patients only)."""
    T = np.asarray(T, dtype=float)
    E = np.asarray(E, dtype=int)
    ef = E == 0
    if ef.sum() == 0:
        return float("nan")
    return float((T[ef] < H).mean())

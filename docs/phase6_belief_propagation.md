# Phase 6: Belief Propagation (Slice 1)

**Status**: Slice 1 Implementation
**Goal**: Deterministic, time-aware belief updates based on evidence, reputation, and contradictions.

## 1. Belief Update Rule

The belief `confidence` (0.0 to 1.0) is computed via a logistic function over weighted signals.

### Formula
$$
\text{Logit} = w_e \cdot E + w_r \cdot R + w_t \cdot T - w_c \cdot C
$$
$$
\text{Confidence} = \sigma(\text{Logit}) = \frac{1}{1 + e^{-\text{Logit}}}
$$

### Inputs
1.  **Evidence ($E$)**: Derived from `base_belief` (0..1). Centered by $(b - 0.5) \times 6$.
2.  **Reputation ($R$)**: Source reputation (0..1). Multiplier: $w_r$.
3.  **Recency ($T$)**: Time decay factor (0..1) based on `observed_at` vs `now`. Multiplier: $w_t$.
4.  **Contradictions ($C$)**: Count of active contradictions (int). Penalty multiplier: $w_c$.

### Weights (Default)
-   $w_e = 1.0$ (Evidence)
-   $w_r = 1.0$ (Source Reputation)
-   $w_t = 0.25$ (Recency Nudge)
-   $w_c = 2.0$ (Contradiction Penalty)

## 2. Determinism & Handling

### Tie-Breaking
-   Result is pure function of inputs.
-   `datetime` inputs MUST be timezone-aware (UTC).
-   Floating point operations use standard IEEE 754 logic (Python `float`).

### NULL Handling
-   If `base_belief` is NULL/None $\rightarrow$ Treated as 0.0 (Disbelief) or Neutral?
    -   *Current Impl*: Treated as 0.0.
-   If `observed_at` is NULL $\rightarrow$ Recency = 0.0.

### Contradictions
-   Contradictions are strictly penalizing.
-   A count of 1 or more significantly reduces confidence (via $-2.0 \times C$).

## 3. Implementation
-   **Location**: `cns_py/cql/belief.py`
-   **Function**: `compute()`
-   **Type**: Pure function (no DB side effects).

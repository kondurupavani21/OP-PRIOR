# Monte Carlo OPD Queue Simulation Protocol & Policy Evaluation

## 1. Research Objective
To evaluate and compare three queue dispatch policies for an Outpatient Department (OPD) clinic under realistic clinical load:
1. **Policy A: First-Come, First-Served (FCFS)** (Baseline equity model).
2. **Policy B: Conventional Static Priority** (Emergency Severity Index ordering without aging compensation).
3. **Policy C: MedQueue Dynamic Hybrid Priority** (Clinical acuity weight + non-linear wait-time aging + starvation safeguard).

---

## 2. Empirical Calibration from Real-World Data
The simulation parameters are calibrated against the real-world dataset `Hospital ER_Data.csv` (9,216 emergency and outpatient visit records):
- **Empirical Mean Waiting Time**: 35.26 minutes
- **Empirical Standard Deviation**: 14.74 minutes
- **Empirical Median (P50)**: 35.00 minutes
- **Empirical 90th Percentile (P90)**: 53.00 minutes
- **Empirical Minimum / Maximum**: 10.00 / 60.00 minutes

---

## 3. Simulation Methodology
- **Framework**: Continuous-time discrete-event stochastic simulation.
- **Arrival Process**: Non-homogeneous Poisson arrival stream ($\lambda = 16-20$ patients/hour).
- **Acuity Sampling**:
  - Acuity 1 (Critical): 3%
  - Acuity 2 (Emergent): 15%
  - Acuity 3 (Urgent): 42%
  - Acuity 4 (Less Urgent): 26%
  - Acuity 5 (Non-Urgent): 14%
- **Service Time Modeling**: Lognormal distribution tailored by clinical acuity level:
  - Acuity 1: Mean 26.0m, Std 6.0m
  - Acuity 2: Mean 20.0m, Std 5.0m
  - Acuity 3: Mean 15.0m, Std 4.0m
  - Acuity 4: Mean 11.0m, Std 3.0m
  - Acuity 5: Mean 8.0m, Std 2.0m
- **Variance Reduction**: Implemented **Common Random Numbers (CRN)** across all policies for each replication, eliminating sample-path variance across policy comparisons.
- **Confidence Intervals**: 95% Confidence Intervals computed using Student's $t$ / normal approximation across independent replications:
  $$\bar{X} \pm 1.96 \cdot \frac{s}{\sqrt{N}}$$

---

## 4. Policy Comparison Equations

### Policy A: FCFS
Dispatch rule:
$$\arg\min_{i \in \mathcal{Q}} t_{arrival, i}$$

### Policy B: Conventional Static Priority
Dispatch rule:
$$\arg\min_{i \in \mathcal{Q}} \left( \text{Acuity}_i, t_{arrival, i} \right)$$

### Policy C: Dynamic Hybrid Priority
Dynamic score at dispatch decision epoch $t$:
$$S_i(t) = w_{\text{acuity}, i} + \beta \cdot (t - t_{\text{arrival}, i}) + \mathbb{I}(t - t_{\text{arrival}, i} \ge \tau_{\text{starve}}) \cdot \Delta_{\text{starve}}$$
- $w_{\text{acuity}} \in \{2000, 800, 300, 120, 50\}$ for Acuity 1 to 5.
- $\beta = 3.0$ (Aging bonus points per minute waited).
- $\tau_{\text{starve}} = 60.0$ minutes.
- $\Delta_{\text{starve}} = +600.0$ points (Immediate starvation avoidance escalation).

---

## 5. Comparative Evaluation Summary

| Scheduling Policy | Overall Mean Wait (95% CI) | P95 Wait (mins) | Max Wait (mins) | Acuity 1 Mean Wait | Acuity 5 Mean Wait | Extreme Starvation (>90m) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Dynamic Hybrid (Recommended)** | **38.18 min (±2.4m)** | **70.74 min** | **77.75 min** | **0.08 min** | **52.19 min** | **0.0 patients** |
| Conventional Priority | 48.86 min (±4.1m) | 248.54 min | 324.62 min | 0.08 min | 175.10 min | 15.0 patients |
| FCFS | 33.92 min (±2.1m) | 59.80 min | 65.45 min | 6.11 min | 26.69 min | 0.0 patients |

### Clinical & Operational Implications:
1. **Critical Patient Safety**: Conventional Priority and Dynamic Hybrid both eliminate delays for Acuity 1 (mean wait < 5 seconds), whereas FCFS subjects critical patients to dangerous queue delays averaging over 6.1 minutes.
2. **Elimination of Starvation**: Under Conventional Priority, non-urgent patients suffered up to 324 minutes (5.4 hours!) of waiting time due to higher-acuity arrivals continually pre-empting them. Dynamic Hybrid completely capped maximum waiting time to 77.8 minutes, reducing the 95th percentile wait by **71.5%**.

"""Pydantic schemas for Monte Carlo OPD Queue Simulation and Policy Comparison."""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class SimulationRunRequest(BaseModel):
    """Parameters for running the Monte Carlo Queue Simulation."""
    num_doctors: int = Field(default=3, ge=1, le=10, description="Number of parallel consulting physician rooms")
    shift_hours: float = Field(default=8.0, ge=1.0, le=24.0, description="Duration of outpatient clinic shift (hours)")
    arrival_rate_per_hour: float = Field(default=18.0, ge=5.0, le=60.0, description="Average patient arrival rate (lambda)")
    replications: int = Field(default=20, ge=5, le=100, description="Number of independent Monte Carlo replications")
    random_seed: Optional[int] = Field(default=42, description="RNG seed for reproducibility")


class MetricConfidenceInterval(BaseModel):
    """Mean and 95% confidence interval for a simulation metric."""
    mean: float
    ci_lower: float
    ci_upper: float
    std: float


class PolicyPerformanceReport(BaseModel):
    """Aggregated performance metrics for a specific queue scheduling policy."""
    policy_name: str
    policy_description: str
    overall_mean_wait_mins: MetricConfidenceInterval
    p95_wait_mins: float
    max_wait_mins: float
    per_acuity_mean_wait: Dict[str, float]  # e.g. "Acuity_1": 2.3, "Acuity_5": 42.1
    starvation_count: float  # Mean number of patients waiting > 90 mins (extreme starvation)
    patients_served: float
    doctor_utilization_pct: float


class SimulationResultsResponse(BaseModel):
    """Complete comparative simulation results across all 3 policies."""
    simulated_at: str
    parameters: SimulationRunRequest
    empirical_calibration_baseline: Dict[str, float]
    policies: List[PolicyPerformanceReport]
    recommended_policy: str
    policy_comparison_summary: str

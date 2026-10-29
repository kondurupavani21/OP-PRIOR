"""API Router for Monte Carlo OPD Queue Simulation and Policy Comparison."""
import logging
from typing import Dict
from fastapi import APIRouter, HTTPException, status

from app.schemas.simulation import (
    SimulationResultsResponse,
    SimulationRunRequest,
)
from app.simulation.queue_sim import (
    execute_monte_carlo_simulation,
    get_empirical_calibration,
    get_latest_simulation_result,
)

logger = logging.getLogger("medqueue.routers.simulation")
router = APIRouter(prefix="/simulation", tags=["OPD Queue Simulation"])


@router.get(
    "/calibration",
    response_model=Dict[str, float],
    status_code=status.HTTP_200_OK,
    summary="Get Empirical Wait-Time Calibration Baseline",
)
def get_calibration():
    """Retrieve empirical wait-time statistics calibrated against Hospital ER visit records."""
    return get_empirical_calibration()


@router.get(
    "/results",
    response_model=SimulationResultsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Latest Monte Carlo Policy Simulation Results",
)
def get_simulation_results() -> SimulationResultsResponse:
    """Retrieve comparative evaluation metrics across FCFS, Conventional Priority, and Dynamic Hybrid queue policies."""
    return get_latest_simulation_result()


@router.post(
    "/run",
    response_model=SimulationResultsResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Monte Carlo OPD Queue Simulation",
)
def run_simulation(payload: SimulationRunRequest) -> SimulationResultsResponse:
    """Execute stochastic discrete-event simulation across policies with Common Random Numbers."""
    try:
        return execute_monte_carlo_simulation(payload)
    except Exception as exc:
        logger.error(f"Simulation failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Monte Carlo simulation failed: {str(exc)}",
        )

"""
Cost forecasting module.

Current implementation: linear regression on cost_history per resource.
Structured for drop-in replacement with Facebook Prophet or LSTM.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class CostPredictor:
    """
    Forecasts future cloud costs.

    To use a real forecasting model (e.g. Prophet):
        1. pip install prophet
        2. Replace _linear_forecast() with Prophet().fit().predict()
    """

    FORECAST_DAYS = 30

    def forecast(self, resources: list) -> Dict[str, Any]:
        """
        Returns a 30-day cost forecast with per-service breakdown.
        """
        total_current_daily = sum(r.cost_daily for r in resources)
        total_current_monthly = sum(r.cost_monthly for r in resources)

        forecasted_daily = self._linear_forecast_total(resources)
        forecasted_monthly = forecasted_daily * 30

        trend_pct = (
            ((forecasted_monthly - total_current_monthly) / total_current_monthly * 100)
            if total_current_monthly > 0 else 0.0
        )

        daily_series = self._build_daily_series(resources)

        return {
            "current_monthly": round(total_current_monthly, 2),
            "forecasted_monthly": round(forecasted_monthly, 2),
            "trend_percent": round(trend_pct, 2),
            "forecast_days": self.FORECAST_DAYS,
            "generated_at": datetime.utcnow().isoformat(),
            "daily_series": daily_series,
            "method": "linear_regression",  # update when swapping model
        }

    def _linear_forecast_total(self, resources: list) -> float:
        """
        Fit a simple linear trend to the aggregate daily cost history and
        extrapolate one period forward.
        """
        # Aggregate all cost_history points by day index
        if not resources:
            return 0.0

        max_pts = max(len(r.metrics.cost_history) for r in resources)
        if max_pts == 0:
            return sum(r.cost_daily for r in resources)

        aggregated: Dict[int, float] = {}
        for r in resources:
            for i, pt in enumerate(r.metrics.cost_history):
                aggregated[i] = aggregated.get(i, 0.0) + pt.value

        xs = sorted(aggregated.keys())
        ys = [aggregated[x] for x in xs]
        slope, intercept = self._least_squares(xs, ys)
        next_x = xs[-1] + 1
        return max(0.0, slope * next_x + intercept)

    def _least_squares(self, xs: List[int], ys: List[float]):
        n = len(xs)
        if n < 2:
            return 0.0, ys[0] if ys else 0.0
        sum_x = sum(xs)
        sum_y = sum(ys)
        sum_xy = sum(x * y for x, y in zip(xs, ys))
        sum_x2 = sum(x * x for x in xs)
        denom = n * sum_x2 - sum_x ** 2
        if denom == 0:
            return 0.0, sum_y / n
        slope = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n
        return slope, intercept

    def _build_daily_series(self, resources: list) -> List[Dict[str, Any]]:
        """Build a 30-day historical + 7-day forecast series for charting."""
        today = datetime.utcnow().date()
        # Aggregate historical daily costs
        daily_totals: Dict[int, float] = {}
        for r in resources:
            for i, pt in enumerate(r.metrics.cost_history):
                daily_totals[i] = daily_totals.get(i, 0.0) + pt.value

        n_historical = max(daily_totals.keys(), default=0) + 1
        xs = sorted(daily_totals.keys())
        ys = [daily_totals[x] for x in xs]
        slope, intercept = self._least_squares(xs, ys)

        series = []
        for i in xs:
            series.append({
                "date": (today - timedelta(days=n_historical - 1 - i)).isoformat(),
                "cost": round(daily_totals[i], 2),
                "type": "actual",
            })
        for f in range(1, 8):
            x = (xs[-1] + f) if xs else f
            series.append({
                "date": (today + timedelta(days=f)).isoformat(),
                "cost": round(max(0, slope * x + intercept), 2),
                "type": "forecast",
            })
        return series

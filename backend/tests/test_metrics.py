from decimal import Decimal
from unittest.mock import MagicMock

from app.state.metrics import get_recovery_metrics


def test_get_recovery_metrics_returns_expected_aggregates():
    db = MagicMock()

    scalar_values = [
        5,                       # total_cases
        2,                       # recovered_cases
        2,                       # escalated_cases
        1,                       # unresolved_cases
        Decimal("1000.00"),      # amount_at_risk
        Decimal("600.00"),       # amount_recovered
        8,                       # total_attempts
    ]

    query = MagicMock()
    query.filter.return_value = query
    query.scalar.side_effect = scalar_values

    db.query.return_value = query

    result = get_recovery_metrics(db)

    assert result["total_cases"] == 5
    assert result["recovered_cases"] == 2
    assert result["escalated_cases"] == 2
    assert result["unresolved_cases"] == 1

    assert result["amount_at_risk"] == Decimal("1000.00")
    assert result["amount_recovered"] == Decimal("600.00")

    assert result["total_attempts"] == 8
    assert result["recovery_rate"] == Decimal("60.00")
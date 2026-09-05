from app.agent.analyst_agent import _AnalystReportWire, _to_analyst_report


def test_analyst_output_normalizes_single_string_arrays():
    raw = _AnalystReportWire(
        failure_analysis="Bank declined the payment.",
        customer_analysis="One failed payment is on record.",
        recovery_factors="bank_declined",
        risk_level="MEDIUM",
        considerations="Use an alternate payment path.",
    )

    report = _to_analyst_report(raw)

    assert report.recovery_factors == ["bank_declined"]
    assert report.considerations == ["Use an alternate payment path."]
    assert report.risk_level == "medium"


def test_analyst_output_parses_json_array_strings():
    raw = _AnalystReportWire(
        failure_analysis="Payment failed.",
        customer_analysis="Customer has prior history.",
        recovery_factors='["bank_declined", "low amount"]',
        risk_level="low",
        considerations='["Offer another payment method"]',
    )

    report = _to_analyst_report(raw)

    assert report.recovery_factors == ["bank_declined", "low amount"]
    assert report.considerations == ["Offer another payment method"]


def test_analyst_wire_accepts_native_provider_arrays_and_serializes_them():
    raw = _AnalystReportWire(
        failure_analysis="Payment failed.",
        customer_analysis="Customer has prior history.",
        recovery_factors=["server error", "prior success"],
        risk_level="medium",
        considerations=["Retry may succeed"],
    )

    report = _to_analyst_report(raw)

    assert report.recovery_factors == ["server error", "prior success"]
    assert report.considerations == ["Retry may succeed"]

"""Unit tests for monthly_signal.py presentation helpers.

We do not exercise ``run_monthly_signal`` end-to-end here — it depends on
a network fetch of Bitstamp data. Those integration tests come later
(Q1.2, snapshot-backed). This module only covers the pure labeling
helpers that shape the live report.
"""

from __future__ import annotations

from chillbtc.monthly_signal import (
    _build_diagnostic,
    _position_label,
    _sig_label,
    emoji_position,
    emoji_signal,
)


def test_sig_label_buy():
    assert _sig_label(1.0) == "BUY"


def test_sig_label_cash():
    assert _sig_label(0.0) == "CASH"


def test_sig_label_nan_returns_na():
    assert _sig_label(float("nan")) == "N/A"


def test_position_label_all_three():
    assert _position_label(1.0) == "100 % BTC"
    assert _position_label(0.5) == "50 % BTC + 50 % USDC"
    assert _position_label(0.0) == "0 % BTC (100 % USDC)"


def test_emoji_position_three_zones():
    assert emoji_position(1.0) == "🟢"
    assert emoji_position(0.5) == "🟡"
    assert emoji_position(0.0) == "🔴"


def test_emoji_signal_buy_cash():
    assert emoji_signal(1.0) == "✅"
    assert emoji_signal(0.0) == "❌"


def test_build_diagnostic_format():
    """Diagnostic string mentions both signals + final position percentage."""
    msg = _build_diagnostic(sig_r1=1.0, sig_r3=0.0, ret_11=0.15, ratio=3.0, position=0.0)
    assert "R1 BUY" in msg
    assert "R3 CASH" in msg
    assert "+15.0%" in msg
    assert "3.00" in msg
    assert "0 % BTC" in msg

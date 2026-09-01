# -*- coding: utf-8 -*-
from backtest.features import add_features, _consec_true
import pandas as pd


def test_consec_limit_20cm_vs_main():
    rows = []
    px = 10.0
    for i, r in enumerate([0.0, 0.096, 0.096, 0.096, 0.01]):
        px = 10.0 if i == 0 else px * (1 + r)
        rows.append(
            {
                "code": "600000",
                "date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=i),
                "open": px,
                "high": px,
                "low": px,
                "close": px,
                "volume": 1000,
            }
        )
    px = 10.0
    for i, r in enumerate([0.0, 0.20, 0.20, 0.10]):
        px = 10.0 if i == 0 else px * (1 + r)
        rows.append(
            {
                "code": "300001",
                "date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=i),
                "open": px,
                "high": px,
                "low": px,
                "close": px,
                "volume": 1000,
            }
        )
    df = add_features(pd.DataFrame(rows))
    main = df[df["code"] == "600000"].sort_values("date")
    cyb = df[df["code"] == "300001"].sort_values("date")
    assert int(main["consec_limit"].iloc[-2]) == 3
    assert int(cyb["consec_limit"].iloc[2]) == 2
    assert int(cyb["consec_limit"].iloc[3]) == 0


def test_consec_true_breaks():
    s = pd.Series([True, True, False, True])
    out = _consec_true(s)
    assert list(out) == [1, 2, 0, 1]


if __name__ == "__main__":
    test_consec_true_breaks()
    test_consec_limit_20cm_vs_main()
    print("test_features ok")

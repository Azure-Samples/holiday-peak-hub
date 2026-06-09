import asyncio
import json
from pathlib import Path
import tempfile

import pytest

from scripts.ci.continuous_eval_monitor import _float_metrics, _report_fingerprint, create_deduped_issue


class DummyReport:
    def __init__(self, drift_metrics, breached_thresholds=None, severity='warning', consecutive_failures=3):
        self.drift_metrics = drift_metrics
        self.breached_thresholds = breached_thresholds or []
        self.severity = type('S', (), {'value': severity})
        self.consecutive_failures = consecutive_failures


def test_float_metrics():
    src = {'a': '1.2', 'b': 3, 'c': 'nan', 'd': None}
    out = _float_metrics(src)
    assert out['a'] == 1.2
    assert out['b'] == 3.0
    assert 'c' not in out
    assert 'd' not in out


def test_report_fingerprint():
    r = DummyReport({'m1': 0.123456, 'm2': -0.5})
    fp = _report_fingerprint(r)
    assert 'm1' in fp and 'm2' in fp


def test_create_deduped_issue_dry(monkeypatch, tmp_path):
    # Verify that network failures do not raise and function returns gracefully
    def fake_get(url):
        class R:
            ok = False
            def json(self):
                return {}
        return R()

    def fake_post(url, json=None):
        class R:
            ok = False
            text = 'error'
            status_code = 500
            def json(self):
                return {}
        return R()

    monkeypatch.setattr('requests.Session.get', lambda self, url: fake_get(url))
    monkeypatch.setattr('requests.Session.post', lambda self, url, json=None: fake_post(url, json=json))

    # Should not raise
    create_deduped_issue(repo='owner/repo', token='x', agent='a', report=DummyReport({'m': 1.0}), result_path=str(tmp_path/'r.json'))
from hec.core.maintenance import Maintenance


def test_quarter_hour_forecasts_do_not_repeat_daily_maintenance(monkeypatch):
    clock = [0.0]
    calls = {'maintenance':0, 'forecast':0}

    class Stop:
        def is_set(self):
            return clock[0] > 1800

        def wait(self, seconds):
            clock[0] += seconds

    job = object.__new__(Maintenance)
    job._stop = Stop()
    job.interval_seconds = lambda:86400
    job.run_once = lambda:calls.update(maintenance=calls['maintenance']+1)
    job._store_forecast = lambda:calls.update(forecast=calls['forecast']+1)
    monkeypatch.setattr('hec.core.maintenance.time.monotonic',lambda:clock[0])
    job._loop()
    assert calls == {'maintenance':1, 'forecast':2}

"""Offline verification with the installed GoodWe SDK; never connects to hardware."""
import io
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from goodwe.sensor import EcoModeV2
from hec.controller.price import ZONE
from hec.core.config import Config
from hec.readers.goodwe_manager import GoodWeManager


class OfflineInverter:
    def __init__(self):
        self.group = EcoModeV2('eco_mode_1', 0, 'Offline replay')
        self.group.read_value(io.BytesIO(bytes.fromhex('0000173b007fffce00640000')))
        self.groups = {f'eco_mode_{i}_switch': 0 for i in (2, 3, 4)}
        self.mode = 0

    async def read_setting(self, name):
        if name == 'eco_mode_1':
            return self.group
        if name == 'time':
            return datetime(2026, 10, 31, 12)
        if name == 'work_mode':
            return self.mode
        return self.groups[name]

    async def write_setting(self, name, value):
        if name == 'eco_mode_1':
            self.group.read_value(io.BytesIO(value))
        else:
            self.groups[name] = value

    async def set_operation_mode(self, mode):
        assert mode.name == 'ECO'
        self.mode = 3


def main():
    manager = GoodWeManager(Config({}))
    manager._inverter = OfflineInverter()
    args = dict(valid_day='2026-10-31', valid_from='12:00', valid_to='14:00',
                power_pct=20, start_soc_pct=10, stop_soc_pct=60)
    with patch('hec.readers.goodwe_manager.now_local', return_value=datetime(2026, 10, 31, 12, tzinfo=ZONE)):
        manager._run(manager._bounded_charge(args))
    actual = manager._run(manager._bounded_state())
    assert actual == manager._expected_value('start_battery_charge', args), actual
    print(actual)
    print('SDK bounded charge encode/write/readback replay passed; no physical I/O')


if __name__ == '__main__':
    main()

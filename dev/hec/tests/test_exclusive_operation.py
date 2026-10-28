from datetime import datetime
from unittest.mock import patch

import pytest

from hec.readers.tng import scheduled_operation
from test_readers_ote_tng import build_tng


@pytest.mark.parametrize('mode,expected', [('heating',(True,False)),('boiler',(False,True)),('off',(False,False))])
def test_mode_switch_posts_flags_even_when_temperatures_match(tmp_path,tng_connect,mode,expected):
    reader,_,_=build_tng(tmp_path,tng_connect,write_enabled=True,
        heating={'enabled':True,'default_temperature':42,'schedule':[]},
        boiler={'enabled':True,'default_temperature':51,'schedule':[]},
        operation={'default_mode':mode})
    state=reader.read_state()
    state['settings']['heating_on']=not expected[0]
    state['settings']['boiler_on']=not expected[1]
    with patch.object(reader,'post_json',return_value=204) as post:
        assert reader.apply(state)==['post:basic']
        payload=post.call_args.args[1]
        assert (payload['HeatSet']['Heat'],payload['BoilerSet']['Boiler'])==expected
        assert not (payload['HeatSet']['Heat'] and payload['BoilerSet']['Boiler'])


def test_bounded_dhw_window_and_date_override():
    section={'default_mode':'heating','schedule':[], 'date_overrides':{
        '2026-10-28':{'schedule':[{'from':'12:00','to':'13:30','mode':'boiler'}]}}}
    for clock,expected in [('11:59','heating'),('12:00','boiler'),('13:29','boiler'),('13:30','heating')]:
        assert scheduled_operation(section,datetime.fromisoformat('2026-10-28T'+clock+'+01:00'))==expected
    assert scheduled_operation(section,datetime.fromisoformat('2026-10-29T12:00+01:00'))=='heating'
    assert scheduled_operation({},datetime.now()) is None


@pytest.mark.parametrize('watts', [-120, 120, 0])
def test_only_heatpump_meter_uses_absolute_power(tmp_path,monkeypatch,watts):
    from test_readers_devices import make_config
    from hec.readers.shelly import ShellyReader
    config=make_config(tmp_path,shelly={'devices':[
        {'name':'HP','host':'test.invalid','role':'heatpump_meter'},
        {'name':'Other','host':'test.invalid','role':'appliance'}]})
    reader=ShellyReader(config)
    monkeypatch.setattr(reader,'read_device',lambda device:{'power_w':watts,'l1_w':watts,'l1_v':240})
    result=reader.read()
    assert result['devices']['hp']['power_w']==abs(watts)
    assert result['devices']['hp']['raw_power_w']==watts
    assert result['devices']['other']['power_w']==watts

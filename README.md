# TNG Controller

Python controller for TNG heat pump / boiler / thermostat.

## Install
`py -m pip install -r requirements.txt`

## Safe test
`py tng_controller.py --once --dry-run`

## Read current thermostat status
`py tng_controller.py --status`

## Run controller
`py tng_controller.py`

Default state polling interval is 60 seconds. Logs are stored under `logs/`.

`config.json` currently enables boiler scheduling only. Heating and thermostat writes are disabled by default.

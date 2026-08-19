# Home Energy Controller – Development Prompt

## Project goal

Develop **Home Energy Controller (HEC)** as a modular, local-first system for monitoring, analyzing, predicting, and optimizing household energy flows.

The system should integrate:

- photovoltaic production
- battery storage
- grid import/export
- heat pump operation
- electricity spot prices
- weather and weather forecast
- appliance-level consumption
- phase-level household consumption
- future optional energy sources and loads

The application should run primarily on a local device such as Raspberry Pi, but development must remain **multiplatform** and usable on:

- Windows
- Linux / Raspberry Pi OS
- Android through a responsive web interface or installable PWA

The project repository may already contain working scripts and prototypes. **Do not rewrite working functionality unnecessarily.** First inspect the existing repository, understand the current files, interfaces, JSON formats, APIs, and dependencies, and evolve the system incrementally.

---

# 1. Core architecture

Design the project as independent modules communicating through simple local data structures.

Suggested structure:

```text
home-energy-controller/
│
├── readers/
│   ├── goodwe_reader.py
│   ├── tng_reader.py
│   ├── ote_reader.py
│   ├── weather_reader.py
│   ├── shelly_reader.py
│   └── future_readers/
│
├── controller/
│   ├── controller.py
│   ├── rules.py
│   ├── optimizer.py
│   └── predictor.py
│
├── web/
│   ├── backend/
│   ├── frontend/
│   └── static/
│
├── config/
│   ├── config.json
│   └── schema.json
│
├── data/
│
├── logs/
│
├── history/
│
├── tests/
│
├── docs/
│
└── README.md
```

The exact structure may be adjusted after inspecting the current repository.

---

# 2. Existing integrations and intended readers

## GoodWe / FVE

The system should read household energy data from the existing GoodWe/FTE environment.

Expected data includes at least:

- PV production
- battery SOC
- battery charge/discharge power
- grid import
- grid export
- household consumption
- L1 consumption/power
- L2 consumption/power
- L3 consumption/power
- inverter state
- battery state
- timestamps

Polling interval should normally be around **10 seconds**, configurable through UI/config.

Do not assume the exact API until the existing repository is inspected.

---

## TNG heat pump

The system already has working experience with TNG Smart / tngsmart.cz communication.

Important known fact:

A working PowerShell prototype was able to log into tngsmart.cz and successfully change the thermostat setpoint through the TNG API.

The working request depended on:

- full thermostat key
- browser-like session details
- User-Agent
- TimeZone cookie
- acceptCookies
- matching HTTP headers

Future development should build on the working baseline already present in the repository.

The integration should support:

### Read

- heat pump current state
- requested room/setpoint temperature
- hot water temperature
- heating mode
- DHW mode
- relevant temperatures
- errors/status
- any useful values exposed by TNG API

### Write

Where supported and safe:

- target temperature
- DHW target temperature
- enable/disable selected modes
- future heating optimization commands

Never blindly assume a write endpoint. Reuse or extend working API calls found in the repository.

Recommended polling:

- 30–60 seconds
- configurable

---

## OTE / spot electricity prices

Read electricity spot prices.

Store:

- timestamp / interval
- price
- date
- source timestamp
- optional normalized CZK/kWh value

Prices normally need to be refreshed:

- when a new day becomes available
- periodically as fallback
- on application startup if data is missing

The controller should be able to use current and future prices for planning.

---

## Weather

Current weather reader already exists or has been prototyped.

The system should use:

- current weather
- forecast
- outdoor temperature
- wind speed
- precipitation
- cloudiness
- solar conditions
- sunrise
- sunset

Recommended refresh:

- every 15–30 minutes
- configurable

Future local weather station integration should also be supported.

---

## Local weather station / LoRaWAN

A possible future setup is:

```text
Weather station
      │
   LoRaWAN
      │
      ▼
LoRaWAN gateway
      │
     MQTT
      │
      ▼
weather_reader.py
```

Possible measured values:

- wind speed
- wind direction
- wind gust
- temperature
- humidity
- rainfall

Design the reader architecture so MQTT/LoRaWAN sources can be added without changing the controller.

---

## Shelly devices

Shelly devices will be used for:

### Appliance monitoring

Typical monitored appliances:

- washing machine
- dryer
- dishwasher
- refrigerator
- freezer

Initial goal:

**monitor first, automate later.**

Do not automatically power-cycle appliances unless explicitly enabled in configuration.

Store:

- instantaneous power W
- voltage
- current
- cumulative energy kWh
- device state
- timestamp

Recommended polling:

- around 10 seconds
- configurable

---

## Shelly Pro 3EM – heat pump measurement

A Shelly Pro 3EM will measure the heat pump separately.

Expected values:

- L1 power
- L2 power
- L3 power
- total power
- phase voltage
- phase current
- cumulative energy
- optional power factor

Important:

The heat pump power does **not** pass through the Shelly device. Current is measured using CT clamps.

This measurement will allow correlation of:

```text
TNG state
+
actual electrical consumption
+
weather
+
heating demand
```

This will later allow estimation of real operating efficiency.

---

# 3. Data storage

Keep the first implementation intentionally simple.

## JSONL

All time-series history should initially use **JSONL**.

Reason:

- append-only
- robust
- easy to inspect
- easy to debug
- easy to stream
- no DB server required
- easy future migration to SQL

Example:

```json
{"timestamp":"2026-08-19T18:45:10+02:00","source":"goodwe","pv_w":4210,"grid_w":-850,"battery_soc":91}
{"timestamp":"2026-08-19T18:45:20+02:00","source":"goodwe","pv_w":4160,"grid_w":-810,"battery_soc":92}
```

Use ISO 8601 timestamps with timezone.

Prefer one JSON object per line.

---

# 4. Directory handling

The application must support three configurable storage locations:

```text
data/
logs/
history/
```

## data/

Contains current or short-lived operational data.

Examples:

```text
data/current_goodwe.json
data/current_tng.json
data/current_weather.json
data/current_prices.json
data/current_shelly.json
```

These files may be overwritten.

---

## logs/

Contains application logs.

Examples:

```text
logs/controller.log
logs/goodwe_reader.log
logs/tng_reader.log
logs/web.log
```

Implement log rotation.

---

## history/

Contains historical JSONL time-series data.

Prefer daily files:

```text
history/
├── 2026-08-18-goodwe.jsonl
├── 2026-08-18-tng.jsonl
├── 2026-08-18-weather.jsonl
├── 2026-08-18-shelly.jsonl
└── 2026-08-18-controller.jsonl
```

Alternative subdirectories are acceptable if they improve organization.

Example:

```text
history/goodwe/2026-08-18.jsonl
history/tng/2026-08-18.jsonl
```

---

# 5. History older than 30 days

History older than **30 days** may be stored somewhere else, especially on a NAS.

This must be configurable.

Example config:

```json
{
  "storage": {
    "data_path": "./data",
    "logs_path": "./logs",
    "history_path": "./history",
    "archive_after_days": 30,
    "archive_path": "\\\\NAS\\energy\\history"
  }
}
```

Linux example:

```json
{
  "archive_path": "/mnt/nas/energy/history"
}
```

The implementation must:

- support Windows paths
- support Linux paths
- tolerate NAS being temporarily unavailable
- never delete local history before verifying successful archive
- log archive errors
- retry later
- optionally compress old JSONL files

Suggested compression:

```text
.jsonl.gz
```

Do not introduce SQL yet.

Later migration to:

- SQLite
- PostgreSQL
- TimescaleDB
- InfluxDB

must remain possible.

---

# 6. Controller

The controller is the central decision layer.

Inputs:

```text
GoodWe
TNG
OTE
Weather
Shelly
manual user settings
historical data
predictions
```

Outputs may include:

- TNG setpoint changes
- DHW scheduling
- future appliance control
- notifications
- recommendations
- future battery strategy
- future EV charging
- future additional controllable loads

---

# 7. Control priorities

Default energy priority should roughly follow:

```text
1. current household consumption
2. battery charging
3. DHW / heat pump optimization
4. thermal storage in floor/building
5. flexible household loads
6. energy sharing
7. export to grid
```

This must be configurable.

Do not hard-code economic assumptions.

---

# 8. Heat pump strategy

The house has water-based underfloor heating with high thermal inertia.

The controller should eventually exploit this.

Examples:

### Cheap electricity / high PV production

- increase DHW target moderately
- preheat floor/building slightly
- charge thermal buffer if present
- avoid unnecessary export

### Expensive electricity

- reduce heat pump operation
- use thermal inertia
- reduce DHW heating
- delay non-essential heating if comfort limits allow

The user must be able to configure:

- minimum room temperature
- maximum room temperature
- DHW minimum
- DHW maximum
- maximum allowed temporary preheat
- comfort windows
- quiet hours
- optimization aggressiveness

Safety and comfort always override optimization.

---

# 9. Appliance analysis

Use Shelly data to learn appliance profiles.

Examples:

```text
Dishwasher
start: 12:42
end: 15:17
duration: 155 min
energy: 1.08 kWh
peak: 2.1 kW
```

The system should detect:

- start
- stop
- typical duration
- typical energy
- peak power
- phase correlation if possible

Later use this for planning.

Do not assume that cutting and restoring mains power will automatically start an appliance.

---

# 10. Phase analysis

GoodWe measures individual household phases.

Use this to analyze:

- L1 load
- L2 load
- L3 load
- imbalance
- peak load
- appliance-phase correlation

Do not attempt to electrically rebalance phases automatically.

Instead provide analysis/recommendations such as:

```text
L1 regularly exceeds 5 kW while L2 and L3 remain below 1 kW.
Consider moving selected circuits to another phase.
```

Any physical rewiring is outside the application's control.

---

# 11. Prediction engine

Create a prediction module, initially simple and explainable.

Inputs:

- recent household consumption
- historical daily profiles
- weather forecast
- expected PV production
- battery SOC
- spot prices
- heat pump consumption
- weekday/weekend
- appliance history

Initial predictions:

- expected PV production
- expected household consumption
- expected battery SOC
- expected grid import/export
- likely heat pump demand
- expected energy cost
- best operating windows for flexible loads

Avoid fake precision.

Always display uncertainty where applicable.

Example:

```text
Expected PV production tomorrow:
18–22 kWh
confidence: medium
```

---

# 12. Web interface

Build a modern responsive web UI.

It must work well on:

- desktop browser
- Windows tablet
- Android phone
- Android tablet

Prefer a responsive PWA architecture if practical.

---

# 13. Web navigation

Main pages:

```text
Overview
History
Prediction
Settings
```

Navigation must support:

### Mobile

Horizontal swipe gesture:

```text
Overview  <->  History  <->  Prediction
```

and also a small menu icon in the top corner.

### Desktop

Menu can remain available permanently or as compact navigation.

Do not make swipe navigation mandatory; menu navigation must always work.

---

# 14. Overview page

The main page should show current system state clearly.

Suggested widgets:

### Current energy flow

```text
          FVE
           │
           ▼
       HOUSE LOAD
        ↙     ↘
    BATTERY   GRID
           │
           ▼
          TČ
```

Show live values:

- PV W/kW
- house consumption
- heat pump consumption
- battery SOC
- battery charge/discharge
- grid import/export
- current spot price
- current weather
- current DHW temperature
- current heating status

Use intuitive arrows/flow animation.

---

# 15. History page

Display historical charts.

Selectable ranges:

```text
today
24 h
7 days
30 days
custom
```

Data categories:

- PV
- battery
- grid
- house
- TČ
- appliances
- weather
- spot price
- temperature
- phase loads

Allow multiple series where useful.

Keep charts usable on mobile.

---

# 16. Prediction page

Display:

- expected PV production
- expected consumption
- expected heat demand
- predicted battery SOC
- predicted grid import/export
- spot-price outlook
- recommended appliance windows
- recommended TČ schedule
- estimated daily cost

Example:

```text
Tomorrow

PV:
19.4 kWh

Consumption:
24.1 kWh

Grid:
4.7 kWh import

Best dishwasher window:
11:40–14:10

Best DHW window:
12:00–14:00
```

---

# 17. Dynamic weather-based background

The visual background should reflect:

- current weather
- time of day
- sunrise/sunset
- optionally season

Examples:

```text
clear morning
cloudy morning
clear day
cloudy day
rain
storm
sunset
evening
clear night
cloudy night
snow
fog
```

Use subtle animations.

Examples:

### Clear day

- slow moving light clouds
- gentle sunlight gradient

### Rain

- subtle animated rain
- darker sky
- no distracting heavy animation

### Evening

- warm sunset colors
- slowly fading light

### Night

- dark blue sky
- optional subtle stars
- moon depending on design

The background must never reduce readability.

Add a user setting:

```text
animations:
  full
  reduced
  off
```

Respect operating system `prefers-reduced-motion`.

The UI should remain performant on Android.

---

# 18. Configuration through UI

All important configuration must be editable through the web UI.

Settings page should include sections such as:

```text
General
Storage
GoodWe
TNG
OTE
Weather
Shelly
Controller
Comfort
Optimization
Web UI
Archive
```

Examples:

### Storage

- data path
- logs path
- history path
- archive path
- archive age
- compression

### Poll intervals

- GoodWe
- TNG
- Weather
- Shelly

### Optimization

- battery thresholds
- spot-price thresholds
- DHW temperature range
- comfort temperatures
- preferred appliance windows

### UI

- language
- units
- animation level
- theme override

---

# 19. Config file

Use a readable config format.

JSON is acceptable initially.

Example:

```json
{
  "system": {
    "timezone": "Europe/Prague",
    "language": "cs"
  },
  "storage": {
    "data_path": "./data",
    "logs_path": "./logs",
    "history_path": "./history",
    "archive_after_days": 30,
    "archive_path": ""
  },
  "polling": {
    "goodwe_seconds": 10,
    "tng_seconds": 30,
    "shelly_seconds": 10,
    "weather_minutes": 15
  }
}
```

UI configuration changes must:

1. validate input
2. save safely
3. create backup of previous config
4. apply dynamically where possible
5. clearly indicate when restart is required

Do not store passwords or secrets in plain config when avoidable.

---

# 20. Secrets

Sensitive values such as:

- passwords
- API keys
- tokens
- TNG session secrets
- MQTT passwords

must not be committed to GitHub.

Support:

```text
.env
environment variables
local secrets file excluded by .gitignore
```

Provide:

```text
.env.example
```

Never log secrets.

---

# 21. Logging

Each module should use structured logging.

Include:

- timestamp
- module
- level
- event
- error
- optional request duration

Example:

```text
2026-08-19 18:54:22 INFO goodwe_reader poll_success duration_ms=148
```

Logs should rotate automatically.

---

# 22. Reliability

The application should be designed for unattended operation.

Each reader must:

- survive temporary network errors
- retry with backoff
- avoid crashing the whole application
- expose last successful read time
- mark data as stale when necessary

Controller should not make decisions from stale critical data.

Example:

```text
GoodWe data age > 60 seconds
→ optimization paused
→ safe mode
```

---

# 23. Safe mode

If important integrations fail:

- stop active optimization
- preserve current safe settings
- do not repeatedly send control commands
- show warning in UI
- continue collecting any available data

---

# 24. Multiplatform requirements

Development must avoid unnecessary platform-specific assumptions.

Target environments:

```text
Windows 11
Raspberry Pi OS / Linux
Android browser / PWA
```

Use cross-platform path handling.

In Python:

```python
pathlib.Path
```

Avoid hard-coded separators.

Any system service implementation should have alternatives:

### Windows

- console
- scheduled task
- optional Windows service later

### Linux/Raspberry Pi

- systemd

---

# 25. Deployment

The preferred eventual production environment is Raspberry Pi.

Development may happen on Windows.

The same codebase should run on both.

Provide startup documentation.

Possible architecture:

```text
Python backend
+
web server/API
+
browser/PWA frontend
```

Docker may be supported later but must not be mandatory for first deployment.

---

# 26. API

Expose a local API for the frontend.

Suggested areas:

```text
/api/current
/api/history
/api/prediction
/api/config
/api/status
```

Future integrations should be able to consume the same API.

---

# 27. Future extensibility

Design adapters/readers so future integrations can be added:

- EV charger
- V2H/V2G
- LoRaWAN sensors
- smart relays
- energy meter
- additional inverter
- wind turbine
- thermal storage
- home automation
- MQTT devices
- Home Assistant
- Google Home

Do not tightly couple the controller to specific hardware.

---

# 28. Data retention and future database migration

Current requirement:

**JSONL first.**

But keep storage logic behind a simple abstraction.

Example:

```text
StorageBackend
 ├── JsonlStorage
 └── future SqlStorage
```

The controller and readers should not care whether data is stored in JSONL or SQL.

---

# 29. Development philosophy

Priorities:

1. working system
2. stable data collection
3. visibility
4. simple rules
5. prediction
6. advanced optimization

Do not build complex AI optimization before basic measurements are trustworthy.

Prefer:

- simple code
- clear interfaces
- observable behavior
- deterministic rules
- incremental development
- tests around critical logic

---

# 30. Development workflow for this GitHub repository

When working with this repository:

1. Inspect all current files first.
2. Identify which components are already functional.
3. Preserve working API logic.
4. Document discovered interfaces.
5. Propose changes before major refactoring.
6. Add tests for existing working behavior before replacing it.
7. Keep backward compatibility with existing JSON outputs where practical.
8. Do not remove working scripts unless their functionality has been migrated and verified.
9. Maintain a clear changelog.
10. Update README after significant architecture changes.

---

# 31. Initial implementation phases

## Phase 1 – monitoring

Implement reliable readers:

```text
GoodWe
TNG
OTE
Weather
Shelly
```

Store JSONL history.

Build current-status dashboard.

No automatic control except already tested manual commands.

---

## Phase 2 – analysis

Add:

- appliance profiles
- phase analysis
- heat pump consumption analysis
- energy balance
- daily summaries
- historical charts

---

## Phase 3 – prediction

Add:

- PV forecast
- consumption forecast
- heat demand estimate
- battery SOC prediction
- price-aware scheduling suggestions

---

## Phase 4 – controlled optimization

Add controller rules for:

- DHW
- heat pump
- thermal preheating
- flexible appliance recommendations

Every active rule must have:

```text
enabled
priority
reason
limits
manual override
```

---

## Phase 5 – advanced optimization

Later:

- automated appliance control
- EV charging
- thermal storage
- V2H
- additional energy sources
- SQL database
- richer prediction models

---

# 32. UI language

Primary UI language:

```text
Czech
```

Architecture should allow future localization.

Use translation keys rather than hard-coded strings where practical.

---

# 33. UX principle

The UI should answer three questions immediately:

```text
1. What is happening now?
2. Why is it happening?
3. What will probably happen next?
```

For controller decisions display human-readable explanations.

Example:

```text
TUV heating increased to 50 °C

Reason:
PV surplus 3.8 kW
Battery SOC 96 %
Spot price low
Expected cloud cover after 15:00
```

This explainability is a core requirement.

---

# 34. Primary success metric

The project should ultimately quantify:

- purchased electricity avoided
- export optimized
- self-consumption increased
- energy cost saved
- heat pump efficiency
- battery utilization
- flexible loads shifted
- comfort maintained

Every optimization should eventually be measurable financially and energetically.

---

# 35. Important development rule

Do not over-engineer the first version.

Start from the currently working repository.

Build the architecture around real data.

Prefer a reliable simple controller over a theoretically optimal but fragile system.

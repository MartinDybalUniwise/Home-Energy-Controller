import asyncio
import goodwe

IP = "192.168.2.116"


async def main():
    print(f"Pripojuji se k GoodWe na {IP}...")

    inverter = await goodwe.connect(
        host=IP,
        family="ET",
        timeout=2,
        retries=3
    )

    print()
    print("=== MENIC ===")
    print("Model:", inverter.model_name)
    print("Serial:", inverter.serial_number)
    print("Firmware:", inverter.firmware)

    data = await inverter.read_runtime_data()

    print()
    print("=== AKTUALNI STAV ===")

    fields = [
        ("ppv", "FV vykon"),
        ("ppv1", "PV1 vykon"),
        ("ppv2", "PV2 vykon"),
        ("house_consumption", "Spotreba domu"),
        ("active_power", "Sit"),
        ("pbattery1", "Baterie vykon"),
        ("battery_soc", "Baterie SOC"),
        ("battery_soh", "Baterie SOH"),
        ("vbattery1", "Baterie napeti"),
        ("ibattery1", "Baterie proud"),
        ("battery_temperature", "Baterie teplota"),
        ("battery_charge_limit", "Limit nabijeni"),
        ("battery_discharge_limit", "Limit vybijeni"),
        ("work_mode_label", "Pracovni rezim"),
        ("grid_in_out_label", "Tok site"),
        ("e_day", "Vyroba dnes"),
        ("e_load_day", "Spotreba dnes"),
        ("e_day_imp", "Import dnes"),
        ("e_day_exp", "Export dnes"),
    ]

    for key, label in fields:
        if key in data:
            print(f"{label:25}: {data[key]}")

    print()
    print("=== VSECHNY DOSTUPNE HODNOTY ===")

    for sensor in inverter.sensors():
        if sensor.id_ in data:
            unit = getattr(sensor, "unit", "")
            print(
                f"{sensor.id_:30} "
                f"{sensor.name:35} "
                f"{data[sensor.id_]} {unit}"
            )


if __name__ == "__main__":
    asyncio.run(main())

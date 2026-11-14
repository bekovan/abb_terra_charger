"""ABB Terra charger Modbus protocol support for modern firmware."""

import struct

from modbus_connection import ModbusError

# Serial number (4000h) is an encoded value, not an ASCII string.
# See ABB Terra AC Modbus Communication, section 5.1.
CONNECTOR_TYPES = {0x47: "G", 0x50: "P", 0x53: "S", 0x54: "T"}
RATED_POWER = {0x07: "7", 0x11: "11", 0x22: "22"}


def decode_serial_number(regs) -> str:
    """Decode the serial number from the four registers at 4000h."""
    byte7 = (regs[0] >> 8) & 0xFF  # connector type
    byte6 = regs[0] & 0xFF  # rated power
    byte5 = (regs[1] >> 8) & 0xFF  # plant id
    byte3 = (regs[2] >> 8) & 0xFF  # production week (BCD)
    byte2 = regs[2] & 0xFF  # production year (BCD)
    byte1 = (regs[3] >> 8) & 0xFF  # serial digits (BCD)
    byte0 = regs[3] & 0xFF  # serial digits (BCD)

    connector = CONNECTOR_TYPES.get(byte7, f"0x{byte7:02X}")
    rated_power = RATED_POWER.get(byte6, str(byte6))
    prod_week = (byte3 >> 4) * 10 + (byte3 & 0xF)
    prod_year = (byte2 >> 4) * 10 + (byte2 & 0xF)
    serial = (
        (byte1 >> 4) * 1000 + (byte1 & 0xF) * 100 + (byte0 >> 4) * 10 + (byte0 & 0xF)
    )
    return (
        f"TACW{rated_power}-{byte5}-{prod_week:02d}{prod_year:02d}"
        f"-{connector}{serial:04d}"
    )


def decode_firmware_version(regs) -> str:
    """Decode the firmware version from the two registers at 4004h."""
    major = (regs[0] >> 8) & 0xFF
    minor = regs[0] & 0xFF
    patch = (regs[1] >> 8) & 0xFF
    patch_bcd = (patch >> 4) * 10 + (patch & 0xF)
    return f"{major}.{minor}.{patch_bcd}"


class UpdateReport:
    """Report failures encountered while updating charger readings."""

    def __init__(self) -> None:
        """Initialize an empty failed-update report."""
        self.failed: dict[str, Exception] = {}


class TerraReadings:
    """Container for the latest telemetry reported by a charger."""

    def __init__(self) -> None:
        """Initialize the default readings for a charger."""
        self.serial_number: str = "UNKNOWN"
        self.firmware_version: str = "UNKNOWN"
        self.socket_lock_state: int = 0
        self.l1_current: float = 0.0
        self.l2_current: float = 0.0
        self.l3_current: float = 0.0
        self.max_current: float = 0.0
        self.l1_voltage: float = 0.0
        self.l2_voltage: float = 0.0
        self.l3_voltage: float = 0.0
        self.active_power: float = 0.0
        self.energy_delivered: float = 0.0
        self.error_code: int = 0
        self.charging_state: int = 0


class TerraSettings:
    """Container for the current configuration of a charger."""

    def __init__(self) -> None:
        """Initialize the default settings for a charger."""
        self.current_limit: float = 0.0
        self.fallback_limit: float = 0.0


class TerraCharger:
    """ABB Terra charger exposed through a Modbus device connection."""

    def __init__(self, unit) -> None:
        """Initialize a charger tied to a Modbus unit."""
        self.unit = unit
        self.model = "Terra Direct"
        self.serial_number = "UNKNOWN"
        self.readings = TerraReadings()
        self.settings = TerraSettings()

    @classmethod
    async def async_detect(cls, unit) -> TerraCharger:
        """Create a charger instance for a connected Modbus unit.

        Args:
            unit: The Modbus unit associated with the charger.

        Returns:
            A newly initialized TerraCharger instance.
        """
        return cls(unit)

    async def async_update(self) -> UpdateReport:
        """Refresh charger readings and return an update report."""
        report = UpdateReport()

        try:
            # Read serial number (16384, count 4) - encoded, see section 5.1
            try:
                regs_sn = await self.unit.read_input_registers(address=16384, count=4)
                if regs_sn and len(regs_sn) >= 4:
                    self.readings.serial_number = decode_serial_number(regs_sn)
                    self.serial_number = self.readings.serial_number
            except (AttributeError, OSError, TypeError, ValueError):
                pass

            # Read firmware version (16388, count 2)
            try:
                regs_fw = await self.unit.read_input_registers(address=16388, count=2)
                if regs_fw and len(regs_fw) >= 2:
                    self.readings.firmware_version = decode_firmware_version(regs_fw)
            except (AttributeError, OSError, TypeError, ValueError):
                pass

            # Read error code (16392, count 2) - 0 means no error
            try:
                regs_err = await self.unit.read_input_registers(address=16392, count=2)
                if regs_err and len(regs_err) >= 2:
                    self.readings.error_code = struct.unpack(
                        ">I", struct.pack(">HH", regs_err[0], regs_err[1])
                    )[0]
            except (AttributeError, OSError, TypeError, ValueError):
                pass

            # Read socket lock state (16394, count 1)
            try:
                regs_lock = await self.unit.read_input_registers(address=16394, count=1)
                if regs_lock:
                    self.readings.socket_lock_state = regs_lock[0]
            except (AttributeError, OSError, TypeError, ValueError):
                pass

            regs = await self.unit.read_input_registers(address=16396, count=20)
            if regs:
                self.readings.charging_state = struct.unpack(
                    ">I", struct.pack(">HH", regs[0], regs[1])
                )[0]
                raw_max = struct.unpack(">I", struct.pack(">HH", regs[2], regs[3]))[0]
                self.readings.max_current = round(raw_max * 0.001, 3)
                raw_l1_curr = struct.unpack(">I", struct.pack(">HH", regs[4], regs[5]))[
                    0
                ]
                self.readings.l1_current = round(raw_l1_curr * 0.001, 3)
                # l2 current: 16402 (offset 6)
                if len(regs) >= 8:
                    raw_l2_curr = struct.unpack(
                        ">I", struct.pack(">HH", regs[6], regs[7])
                    )[0]
                    self.readings.l2_current = round(raw_l2_curr * 0.001, 3)
                # l3 current: 16404 (offset 8)
                if len(regs) >= 10:
                    raw_l3_curr = struct.unpack(
                        ">I", struct.pack(">HH", regs[8], regs[9])
                    )[0]
                    self.readings.l3_current = round(raw_l3_curr * 0.001, 3)
                raw_volt_l1 = struct.unpack(
                    ">I", struct.pack(">HH", regs[10], regs[11])
                )[0]
                self.readings.l1_voltage = round(raw_volt_l1 * 0.1, 1)
                if len(regs) >= 14:
                    raw_volt_l2 = struct.unpack(
                        ">I", struct.pack(">HH", regs[12], regs[13])
                    )[0]
                    self.readings.l2_voltage = round(raw_volt_l2 * 0.1, 1)
                if len(regs) >= 16:
                    raw_volt_l3 = struct.unpack(
                        ">I", struct.pack(">HH", regs[14], regs[15])
                    )[0]
                    self.readings.l3_voltage = round(raw_volt_l3 * 0.1, 1)
                self.readings.active_power = float(
                    struct.unpack(">I", struct.pack(">HH", regs[16], regs[17]))[0]
                )
                # energy delivered in this charging session: 16414 (offset 18), Wh
                if len(regs) >= 20:
                    self.readings.energy_delivered = float(
                        struct.unpack(">I", struct.pack(">HH", regs[18], regs[19]))[0]
                    )
        except (
            ModbusError,
            TimeoutError,
            OSError,
            ValueError,
            TypeError,
            IndexError,
            struct.error,
        ) as err:
            report.failed["readings"] = err

        try:
            # 16640 (4100h) is write-only; read the setpoint back from
            # 16418 (4022h), which mirrors what was written to 4100h.
            h_regs = await self.unit.read_holding_registers(address=16418, count=2)
            if h_regs:
                raw_limit = struct.unpack(
                    ">I", struct.pack(">HH", h_regs[0], h_regs[1])
                )[0]
                self.settings.current_limit = round(raw_limit * 0.001, 3)
        except (
            ModbusError,
            TimeoutError,
            OSError,
            ValueError,
            TypeError,
            IndexError,
            struct.error,
        ) as err:
            report.failed["settings"] = err

        try:
            # Fallback current limit readback: 16420 (4024h), single register.
            # The setpoint at 16649 (4109h) is write-only, so it cannot be read
            # back directly.
            fb_regs = await self.unit.read_holding_registers(address=16420, count=1)
            if fb_regs:
                self.settings.fallback_limit = float(fb_regs[0])
        except (
            ModbusError,
            TimeoutError,
            OSError,
            ValueError,
            TypeError,
            IndexError,
        ) as err:
            report.failed["fallback_limit"] = err

        return report

    async def async_write_current_limit(self, amps: float) -> None:
        """Set the charger current limit in amps.

        Args:
            amps: Target charging current in amperes.
        """
        ma_val = int(amps * 1000)
        high_word = (ma_val >> 16) & 0xFFFF
        low_word = ma_val & 0xFFFF

        for method_name in [
            "write_registers",
            "async_write_registers",
            "write_holding_registers",
            "write_holding_register",
            "async_write_holding_registers",
            "write_multiple_holding_registers",
        ]:
            if hasattr(self.unit, method_name):
                method = getattr(self.unit, method_name)
                try:
                    await method(address=16640, values=[high_word, low_word])
                    break
                except (AttributeError, OSError, TypeError, ValueError):
                    continue
        else:
            raise AttributeError(
                f"No suitable write method on unit: {type(self.unit)} {dir(self.unit)}"
            )

        self.settings.current_limit = amps

    async def async_write_fallback_limit(self, amps: float) -> None:
        """Set the fallback current limit in amps.

        The charger applies this current when it loses the smart meter link.
        A value of 0 makes it pause instead of drawing power.

        Args:
            amps: Target fallback current in amperes.
        """
        value = int(amps)

        if hasattr(self.unit, "write_register"):
            try:
                await self.unit.write_register(address=16649, value=value)
            except TypeError:
                await self.unit.write_register(16649, value)
        elif hasattr(self.unit, "async_write_register"):
            try:
                await self.unit.async_write_register(address=16649, value=value)
            except TypeError:
                await self.unit.async_write_register(16649, value)
        elif hasattr(self.unit, "write_holding_registers"):
            try:
                await self.unit.write_holding_registers(address=16649, values=[value])
            except TypeError:
                await self.unit.write_holding_registers(16649, [value])
        elif hasattr(self.unit, "async_write_holding_registers"):
            try:
                await self.unit.async_write_holding_registers(
                    address=16649, values=[value]
                )
            except TypeError:
                await self.unit.async_write_holding_registers(16649, [value])
        else:
            raise AttributeError(f"No suitable write method on unit: {type(self.unit)}")

        self.settings.fallback_limit = float(value)

    async def async_start_charging(self) -> None:
        """Start charging by writing the start command to the charger."""
        if hasattr(self.unit, "write_register"):
            try:
                await self.unit.write_register(address=16645, value=0)
            except TypeError:
                await self.unit.write_register(16645, 0)
        else:
            raise AttributeError(f"No suitable write method on unit: {type(self.unit)}")

    async def async_stop_charging(self) -> None:
        """Stop charging by writing the stop command to the charger."""
        if hasattr(self.unit, "write_register"):
            try:
                await self.unit.write_register(address=16645, value=1)
            except TypeError:
                await self.unit.write_register(16645, 1)
        elif hasattr(self.unit, "async_write_register"):
            try:
                await self.unit.async_write_register(address=16645, value=1)
            except TypeError:
                await self.unit.async_write_register(16645, 1)
        elif hasattr(self.unit, "write_holding_registers"):
            try:
                await self.unit.write_holding_registers(address=16645, values=[1])
            except TypeError:
                await self.unit.write_holding_registers(16645, [1])
        elif hasattr(self.unit, "async_write_holding_registers"):
            try:
                await self.unit.async_write_holding_registers(address=16645, values=[1])
            except TypeError:
                await self.unit.async_write_holding_registers(16645, [1])
        else:
            raise AttributeError(f"No suitable write method on unit: {type(self.unit)}")

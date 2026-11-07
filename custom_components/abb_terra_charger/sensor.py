"""Sensor platform for ABB Terra Charger."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import ExtraStoredData, RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TerraDataUpdateCoordinator

CHARGER_STATE_OPTIONS = [
    "Idle",
    "Connected (auth pending)",
    "Connected",
    "Connected (no PWM)",
    "Charging",
    "Charging Complete",
    "Paused",
    "Other",
]
CHARGER_STATE_MAP = {
    0: "Idle",
    128: "Idle",
    1: "Connected (auth pending)",
    2: "Connected",
    129: "Connected",
    3: "Connected (no PWM)",
    4: "Charging",
    132: "Charging",
    130: "Charging Complete",
    133: "Paused",
    5: "Other",
}


def _device_info(coordinator: TerraDataUpdateCoordinator) -> dict:
    """Return the device information shared by the charger entities."""
    return {
        "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)},
        "name": "ABB Terra Charger",
        "manufacturer": "ABB",
        "model": "Terra Charger",
        "sw_version": (
            coordinator.data.readings.firmware_version if coordinator.data else None
        ),
        "serial_number": (
            coordinator.data.readings.serial_number if coordinator.data else None
        ),
    }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator: TerraDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            TerraSensor(
                coordinator,
                "Serial Number",
                "serial_number",
                None,
                None,
                None,
            ),
            TerraSensor(
                coordinator,
                "Firmware Version",
                "firmware_version",
                None,
                None,
                None,
            ),
            TerraSensor(
                coordinator,
                "Error Code",
                "error_code",
                None,
                None,
                0,
                SensorStateClass.MEASUREMENT,
            ),
            TerraSensor(
                coordinator,
                "Socket Lock State",
                "socket_lock_state",
                None,
                None,
                0,
            ),
            TerraSensor(
                coordinator,
                "L1 Current",
                "l1_current",
                SensorDeviceClass.CURRENT,
                UnitOfElectricCurrent.AMPERE,
                3,
            ),
            TerraSensor(
                coordinator,
                "L2 Current",
                "l2_current",
                SensorDeviceClass.CURRENT,
                UnitOfElectricCurrent.AMPERE,
                3,
            ),
            TerraSensor(
                coordinator,
                "L3 Current",
                "l3_current",
                SensorDeviceClass.CURRENT,
                UnitOfElectricCurrent.AMPERE,
                3,
            ),
            TerraSensor(
                coordinator,
                "User Set Max Current",
                "max_current",
                SensorDeviceClass.CURRENT,
                UnitOfElectricCurrent.AMPERE,
                3,
            ),
            TerraSensor(
                coordinator,
                "L1 Voltage",
                "l1_voltage",
                SensorDeviceClass.VOLTAGE,
                UnitOfElectricPotential.VOLT,
                1,
            ),
            TerraSensor(
                coordinator,
                "L2 Voltage",
                "l2_voltage",
                SensorDeviceClass.VOLTAGE,
                UnitOfElectricPotential.VOLT,
                1,
            ),
            TerraSensor(
                coordinator,
                "L3 Voltage",
                "l3_voltage",
                SensorDeviceClass.VOLTAGE,
                UnitOfElectricPotential.VOLT,
                1,
            ),
            TerraSensor(
                coordinator,
                "Active Power",
                "active_power",
                SensorDeviceClass.POWER,
                UnitOfPower.WATT,
                0,
            ),
            TerraEnergySensor(
                coordinator,
                "Energy Delivered",
                "energy_delivered",
            ),
            TerraSensor(
                coordinator,
                "Charger State",
                "charging_state",
                SensorDeviceClass.ENUM,
                None,
                None,
            ),
        ]
    )


class TerraSensor(CoordinatorEntity[TerraDataUpdateCoordinator], SensorEntity):
    """Representation of a Terra Charger sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TerraDataUpdateCoordinator,
        name: str,
        attribute: str,
        device_class: SensorDeviceClass | None,
        unit: str | None,
        precision: int | None,
        state_class: SensorStateClass | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attribute = attribute
        self._attr_name = name
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_suggested_display_precision = precision
        self._attr_state_class = state_class
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{attribute}"
        self._attr_device_info = _device_info(coordinator)
        if attribute == "charging_state":
            self._attr_options = CHARGER_STATE_OPTIONS

    @property
    def native_value(self):
        """Return the native value of the sensor."""
        if self.coordinator.data is None:
            return None
        value = getattr(self.coordinator.data.readings, self._attribute)
        if self._attribute == "charging_state":
            if isinstance(value, int):
                state = value >> 8 & 0xFF
                if state in CHARGER_STATE_MAP:
                    return CHARGER_STATE_MAP[state]
                if 0 <= state < len(CHARGER_STATE_OPTIONS):
                    return CHARGER_STATE_OPTIONS[state]
                return "Other"
        return value


class _EnergyRestoreData(ExtraStoredData):
    """Persisted state for the cumulative energy sensor."""

    def __init__(self, total: float | None, session: float | None) -> None:
        """Initialize the stored state."""
        self.total = total
        self.session = session

    def as_dict(self) -> dict[str, float | None]:
        """Return the state as a JSON-serializable dict."""
        return {"total": self.total, "session": self.session}


class TerraEnergySensor(
    CoordinatorEntity[TerraDataUpdateCoordinator], SensorEntity, RestoreEntity
):
    """Cumulative energy delivered across charging sessions.

    The charger only reports the energy of the current session (register 401Eh),
    which it resets to zero for every new session. Keep a running total instead
    and persist it, so the value keeps increasing across sessions and restarts.
    """

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_suggested_display_precision = 0
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(
        self,
        coordinator: TerraDataUpdateCoordinator,
        name: str,
        attribute: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attribute = attribute
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{attribute}"
        self._attr_device_info = _device_info(coordinator)
        self._total_energy: float | None = None
        self._last_session_energy: float | None = None

    async def async_added_to_hass(self) -> None:
        """Restore the running total and the last session reading."""
        await super().async_added_to_hass()
        if (restored := await self.async_get_last_extra_data()) is not None:
            data = restored.as_dict()
            if data.get("total") is not None:
                self._total_energy = float(data["total"])
            if data.get("session") is not None:
                self._last_session_energy = float(data["session"])
        if self.coordinator.data is not None:
            self._update_total()
            self.async_write_ha_state()

    @property
    def extra_restore_state_data(self) -> ExtraStoredData:
        """Return the state to persist across restarts."""
        return _EnergyRestoreData(self._total_energy, self._last_session_energy)

    @property
    def native_value(self) -> float | None:
        """Return the cumulative energy delivered."""
        return self._total_energy

    @callback
    def _handle_coordinator_update(self) -> None:
        """Accumulate the latest session reading."""
        self._update_total()
        super()._handle_coordinator_update()

    def _update_total(self) -> None:
        """Add the session delta to the running total."""
        if self.coordinator.data is None:
            return
        raw = float(self.coordinator.data.readings.energy_delivered)
        total = self._total_energy or 0.0
        if self._last_session_energy is None:
            # First reading: start the total at the current session value.
            if self._total_energy is None:
                self._total_energy = raw
        elif raw >= self._last_session_energy:
            self._total_energy = total + (raw - self._last_session_energy)
        else:
            # The charger zeroed the session register for a new session.
            self._total_energy = total + raw
        self._last_session_energy = raw

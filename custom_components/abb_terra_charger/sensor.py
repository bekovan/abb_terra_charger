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
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
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
            TerraSensor(
                coordinator,
                "Energy Delivered",
                "energy_delivered",
                SensorDeviceClass.ENERGY,
                UnitOfEnergy.WATT_HOUR,
                0,
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
        self._attr_device_info = {
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

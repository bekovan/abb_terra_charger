"""Binary sensor platform for ABB Terra Charger."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TerraDataUpdateCoordinator

CHARGING_STATES = (4, 132)
PLUGGED_IN_STATES = (1, 2, 3, 4, 129, 130, 132, 133)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    coordinator: TerraDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            TerraBinarySensor(
                coordinator,
                "Charging",
                "charging",
                CHARGING_STATES,
            ),
            TerraBinarySensor(
                coordinator,
                "Plugged In",
                "plugged_in",
                PLUGGED_IN_STATES,
            ),
        ]
    )


class TerraBinarySensor(
    CoordinatorEntity[TerraDataUpdateCoordinator], BinarySensorEntity
):
    """Representation of a Terra Charger charging state binary sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TerraDataUpdateCoordinator,
        name: str,
        key: str,
        active_states: tuple[int, ...],
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_name = name
        self._active_states = active_states
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{key}"
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

    @property
    def is_on(self) -> bool | None:
        """Return True when the charging state is one of the active states."""
        if self.coordinator.data is None:
            return None
        value = self.coordinator.data.readings.charging_state
        if isinstance(value, int):
            value = value >> 8 & 0xFF
        return value in self._active_states

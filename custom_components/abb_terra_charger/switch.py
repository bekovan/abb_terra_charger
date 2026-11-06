"""Switch platform for ABB Terra Charger."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TerraDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    coordinator: TerraDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TerraChargingSwitch(coordinator)])


class TerraChargingSwitch(
    CoordinatorEntity[TerraDataUpdateCoordinator], SwitchEntity
):
    """Representation of a Terra Charger on/pause switch."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: TerraDataUpdateCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_name = "Charging"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_charging_switch"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)},
            "name": "ABB Terra Charger",
            "manufacturer": "ABB",
            "model": "Terra Charger",
            "sw_version": getattr(coordinator.data.readings, "firmware_version", None)
            if coordinator.data
            else None,
            "serial_number": getattr(coordinator.data.readings, "serial_number", None)
            if coordinator.data
            else None,
        }

    @property
    def is_on(self) -> bool | None:
        """Return true if charger is not paused (current limit > 0)."""
        if self.coordinator.data is None:
            return None
        try:
            return self.coordinator.data.settings.current_limit > 0
        except (AttributeError, TypeError):
            return None

    async def async_turn_on(self, **kwargs) -> None:
        """Start charging."""
        await self.coordinator.data.async_start_charging()
        if self.coordinator.data and self.coordinator.data.settings.current_limit == 0:
            await self.coordinator.data.async_write_current_limit(6)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Pause charging by setting current limit to 0."""
        await self.coordinator.data.async_write_current_limit(0)
        await self.coordinator.async_request_refresh()

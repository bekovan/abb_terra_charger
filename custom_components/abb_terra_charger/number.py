"""Number platform for ABB Terra Charger."""

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricCurrent
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
    """Set up the number platform."""
    coordinator: TerraDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            TerraCurrentLimitNumber(coordinator),
            TerraFallbackLimitNumber(coordinator),
        ]
    )


class TerraCurrentLimitNumber(
    CoordinatorEntity[TerraDataUpdateCoordinator], NumberEntity
):
    """Representation of a Terra Charger current limit number."""
    
    _attr_has_entity_name = True
    
    def __init__(self, coordinator: TerraDataUpdateCoordinator) -> None:
        """Initialize the number."""
        super().__init__(coordinator)
        self._attr_name = "Charging Current Limit"
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_native_min_value = 0.0
        self._attr_native_max_value = 32.0
        self._attr_native_step = 1.0
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_current_limit"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)},
            "name": "ABB Terra Charger",
            "manufacturer": "ABB",
            "model": "Terra Charger",
            "sw_version": getattr(coordinator.data.readings, "firmware_version", None) if coordinator.data else None,
            "serial_number": getattr(coordinator.data.readings, "serial_number", None) if coordinator.data else None,
        }

    @property
    def native_value(self):
        """Return the current value."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.settings.current_limit

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        await self.coordinator.data.async_write_current_limit(value)
        await self.coordinator.async_request_refresh()


class TerraFallbackLimitNumber(
    CoordinatorEntity[TerraDataUpdateCoordinator], NumberEntity
):
    """Representation of a Terra Charger fallback current limit number."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: TerraDataUpdateCoordinator) -> None:
        """Initialize the number."""
        super().__init__(coordinator)
        self._attr_name = "Fallback Current Limit"
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_native_min_value = 0.0
        self._attr_native_max_value = 32.0
        self._attr_native_step = 1.0
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_fallback_limit"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)},
            "name": "ABB Terra Charger",
            "manufacturer": "ABB",
            "model": "Terra Charger",
            "sw_version": getattr(coordinator.data.readings, "firmware_version", None) if coordinator.data else None,
            "serial_number": getattr(coordinator.data.readings, "serial_number", None) if coordinator.data else None,
        }

    @property
    def native_value(self):
        """Return the current value."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.settings.fallback_limit

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        await self.coordinator.data.async_write_fallback_limit(value)
        await self.coordinator.async_request_refresh()

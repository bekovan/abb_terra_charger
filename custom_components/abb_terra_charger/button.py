"""Button platform for ABB Terra Charger."""

from homeassistant.components.button import ButtonEntity
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
    """Set up the button platform."""
    coordinator: TerraDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
  #  coordinator: TerraDataUpdateCoordinator = entry.runtime_data
    async_add_entities(
        [
            TerraStartChargingButton(coordinator),
            TerraStopChargingButton(coordinator),
        ]
    )


class TerraStartChargingButton(
    CoordinatorEntity[TerraDataUpdateCoordinator], ButtonEntity
):
    """Representation of a Terra Charger start button."""
    
    _attr_has_entity_name = True
    
    def __init__(self, coordinator: TerraDataUpdateCoordinator) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_name = "Start Charging Session"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_start_charging"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)},
            "name": "ABB Terra Charger",
            "manufacturer": "ABB",
            "model": "Terra Charger",
            "sw_version": getattr(coordinator.data.readings, "firmware_version", None) if coordinator.data else None,
            "serial_number": getattr(coordinator.data.readings, "serial_number", None) if coordinator.data else None,
        }

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.data.async_start_charging()


class TerraStopChargingButton(
    CoordinatorEntity[TerraDataUpdateCoordinator], ButtonEntity
):
    """Representation of a Terra Charger stop button."""
    
    _attr_has_entity_name = True
    
    def __init__(self, coordinator: TerraDataUpdateCoordinator) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_name = "Stop Charging Session"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_stop_charging"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)},
            "name": "ABB Terra Charger",
            "manufacturer": "ABB",
            "model": "Terra Charger",
            "sw_version": getattr(coordinator.data.readings, "firmware_version", None) if coordinator.data else None,
            "serial_number": getattr(coordinator.data.readings, "serial_number", None) if coordinator.data else None,
        }

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.data.async_stop_charging()

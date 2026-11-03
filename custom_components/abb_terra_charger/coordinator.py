"""DataUpdateCoordinator for ABB Terra Charger."""

import asyncio
import logging
from datetime import timedelta

from homeassistant.components import modbus
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from modbus_connection import ModbusTcpParams

from .const import CONF_UNIT_ID, DOMAIN
from .vendor.modern import TerraCharger, UpdateReport

_LOGGER = logging.getLogger(__name__)

FIRST_CONNECT_TIMEOUT = 20  # seconds, only until the link has worked once


class TerraDataUpdateCoordinator(DataUpdateCoordinator[TerraCharger]):
    """Class to manage fetching data from the ABB Terra Charger."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=8),
        )
        self.entry = entry
        self.charger: TerraCharger | None = None
        self._connected = False
        self._ever_connected = False

    @property
    def endpoint(self) -> str:
        """Return the configured Modbus endpoint for log messages."""
        return f"{self.entry.data[CONF_HOST]}:{self.entry.data[CONF_PORT]}"

    def _connection_failed(self, err: Exception) -> UpdateFailed:
        """Log a lost connection once and return the error to raise."""
        self._connected = False
        reason = str(err) or f"no answer within {FIRST_CONNECT_TIMEOUT} seconds"
        # Log the first failure of an outage only, so a charger that stays
        # offline does not fill the log every update interval.
        if self.last_update_success:
            _LOGGER.error(
                "Cannot connect to the ABB Terra Charger at %s: %s",
                self.endpoint,
                reason,
            )
        return UpdateFailed(
            f"Cannot connect to the ABB Terra Charger at {self.endpoint}: {reason}"
        )

    def _raise_for_failed_report(self, report: UpdateReport) -> None:
        """Raise for a failed readings block, log the non-critical ones."""
        if "readings" in report.failed:
            if not self._connected:
                raise report.failed["readings"]
            raise UpdateFailed(f"Failed parsing blocks: {report.failed}")
        if report.failed:
            _LOGGER.debug("Non-critical Modbus read failures: %s", report.failed)

    async def _async_update_data(self) -> TerraCharger:
        """Update data via library."""
        try:
            if self.charger is None:
                params = ModbusTcpParams(
                    host=self.entry.data[CONF_HOST],
                    port=self.entry.data[CONF_PORT],
                )
                unit = modbus.async_get_unit(self.hass, self.entry, params, self.entry.data[CONF_UNIT_ID])
                self.charger = await TerraCharger.async_detect(unit)

            if self._connected:
                report = await self.charger.async_update()
            else:
                # Without a working link yet, bound the attempt so an
                # unreachable host errors out instead of hanging in silence.
                async with asyncio.timeout(FIRST_CONNECT_TIMEOUT):
                    report = await self.charger.async_update()

            # The device library stores read failures in the report instead of
            # raising them, so a connection that was never made ends up here.
            self._raise_for_failed_report(report)
        except UpdateFailed:
            raise
        except Exception as err:
            raise self._connection_failed(err) from err

        self._connected = True
        if not self._ever_connected:
            self._ever_connected = True
            _LOGGER.info("Connected to the ABB Terra Charger at %s", self.endpoint)
        elif not self.last_update_success:
            _LOGGER.info("Connection to the ABB Terra Charger at %s restored", self.endpoint)
        return self.charger

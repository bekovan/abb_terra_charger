"""Config flow for ABB Terra Charger."""

import asyncio
import logging

from modbus_connection import ModbusError, ModbusTcpParams
import probatio

from homeassistant import config_entries
from homeassistant.components import modbus
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT

from .const import CONF_UNIT_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)

CONNECT_TIMEOUT = 20


class TerraChargerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ABB Terra Charger."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await self._async_test_connection(user_input)
            except (ModbusError, TimeoutError, OSError) as err:
                # Connection failures are reported to the user as a form error.
                _LOGGER.error(
                    "Cannot connect to the ABB Terra Charger at %s:%s: %s",
                    user_input[CONF_HOST],
                    user_input[CONF_PORT],
                    err,
                )
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"ABB Terra Charger ({user_input[CONF_HOST]})",
                    data=user_input,
                )

        schema = probatio.Schema(
            {
                probatio.Required(CONF_HOST, default="192.168.x.x"): str,
                probatio.Required(CONF_PORT, default=502): int,
                probatio.Required(CONF_UNIT_ID, default=1): int,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def _async_test_connection(self, user_input: dict) -> None:
        """Prove the host, port and unit ID answer a read before saving."""
        params = ModbusTcpParams(
            host=user_input[CONF_HOST],
            port=user_input[CONF_PORT],
        )
        async with asyncio.timeout(CONNECT_TIMEOUT):
            async with modbus.async_get_temporary_unit(
                self.hass, params, user_input[CONF_UNIT_ID]
            ) as unit:
                await unit.read_input_registers(address=16396, count=1)

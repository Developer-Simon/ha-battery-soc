"""The battery_soc integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_extract_config_entry_ids
import voluptuous as vol

from .const import DOMAIN, PLATFORMS, SERVICE_SET_SOC, ATTR_STATE_OF_CHARGE, ATTR_BANK
from .coordinator import BatterySocCoordinator
from .battery_soc_core import set_state_of_charge

# Service schema for set_state_of_charge
SET_SOC_SCHEMA = cv.make_entity_service_schema({
    vol.Required(ATTR_STATE_OF_CHARGE): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
    vol.Optional(ATTR_BANK): vol.In(["a", "b"]),
})


def _make_set_soc_handler(hass: HomeAssistant):
    """Create a handler for the set_state_of_charge service."""
    async def _async_set_soc(call) -> None:
        """Handle the set_state_of_charge service call."""
        entry_ids = await async_extract_config_entry_ids(hass, call)
        for entry_id in entry_ids:
            coord = hass.data.get(DOMAIN, {}).get(entry_id)
            if coord is None:
                continue  # Target not ours

            # Determine unit_name based on topology
            if coord.params.topology == "parallel":
                unit_name = None
            else:  # series
                bank = call.data.get(ATTR_BANK)
                if not bank:
                    raise ServiceValidationError("bank is required for series topology")
                unit_name = f"bank_{bank}"

            # Set state of charge
            set_state_of_charge(
                coord.state,
                coord.params,
                call.data[ATTR_STATE_OF_CHARGE],
                unit_name=unit_name
            )
            coord._recalc()
            await coord._save()

    return _async_set_soc


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up battery_soc from a config entry."""
    coord = BatterySocCoordinator(hass, entry)
    await coord.async_load()
    coord.async_start_listeners()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coord
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Register service if not already registered
    if not hass.services.has_service(DOMAIN, SERVICE_SET_SOC):
        hass.services.async_register(
            DOMAIN, SERVICE_SET_SOC, _make_set_soc_handler(hass), schema=SET_SOC_SCHEMA
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        coord = hass.data[DOMAIN].pop(entry.entry_id)
        await coord.async_shutdown()

        # Unregister service if no more entries
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_SET_SOC)

    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload a config entry."""
    await hass.config_entries.async_reload(entry.entry_id)

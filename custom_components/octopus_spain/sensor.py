import logging
from datetime import timedelta
from typing import Mapping, Any

from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from .const import (
    CONF_PASSWORD,
    CONF_EMAIL, UPDATE_INTERVAL
)

from homeassistant.const import (
    CURRENCY_EURO,
)

from homeassistant.components.sensor import (
    STATE_CLASS_MEASUREMENT,
    DEVICE_CLASS_MONETARY,
    SensorEntityDescription, SensorEntity
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .lib.octopus_spain import OctopusSpain

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]

    sensors = []
    coordinator = OctopusCoordinator(hass, email, password)
    await coordinator.async_config_entry_first_refresh()

    accounts = coordinator.data.keys()
    for account in accounts:
        sensors.append(OctopusSolarWallet(account, coordinator, len(accounts) == 1))
        sensors.append(OctopusInvoice(account, coordinator, len(accounts) == 1))

    async_add_entities(sensors)


class OctopusCoordinator(DataUpdateCoordinator):

    def __init__(self, hass: HomeAssistant, email: str, password: str):
        super().__init__(hass, _LOGGER, name="Octopus Spain", update_interval=timedelta(seconds=UPDATE_INTERVAL))
        self._api = OctopusSpain(email, password)

    async def _async_update_data(self):
        data = {}
        await self._api.login()
        accounts = await self._api.accounts()
        for account in accounts:
            data[account] = await self._api.account(account)
        return data


class OctopusSolarWallet(CoordinatorEntity, SensorEntity):

    def __init__(self, account: str, coordinator, single: bool):
        super().__init__(coordinator=coordinator)
        self._state = None
        self._account = account
        self._attrs: Mapping[str, Any] = {}
        self._attr_name = "Solar Wallet" if single else f"Solar Wallet ({account})"
        self._attr_unique_id = f"solar_wallet_{account}"
        self.entity_description = SensorEntityDescription(
            key=f"solar_wallet_{account}",
            icon="mdi:piggy-bank-outline",
            native_unit_of_measurement=CURRENCY_EURO,
            device_class=DEVICE_CLASS_MONETARY,
            state_class=STATE_CLASS_MEASUREMENT
        )

    async def async_added_to_hass(self) -> None:
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._state = self.coordinator.data[self._account]['solar_wallet']
        self.async_write_ha_state()

    @property
    def native_value(self) -> StateType:
        return self._state


class OctopusInvoice(CoordinatorEntity, SensorEntity):

    def __init__(self, account: str, coordinator, single: bool):
        super().__init__(coordinator=coordinator)
        self._state = None
        self._account = account
        self._attrs: Mapping[str, Any] = {}
        self._attr_name = "Última Factura Octopus" if single else f"Última Factura Octopus ({account})"
        self._attr_unique_id = f"last_invoice_{account}"
        self.entity_description = SensorEntityDescription(
            key=f"last_invoice_{account}",
            icon="mdi:currency-eur",
            native_unit_of_measurement=CURRENCY_EURO,
            device_class=DEVICE_CLASS_MONETARY,
            state_class=STATE_CLASS_MEASUREMENT
        )

    async def async_added_to_hass(self) -> None:
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data[self._account]['last_invoice']
        self._state = data['amount']
        self._attrs = {
            'Inicio': data['start'],
            'Fin': data['end'],
            'Emitida': data['issued']
        }
        self.async_write_ha_state()

    @property
    def native_value(self) -> StateType:
        return self._state

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        return self._attrs

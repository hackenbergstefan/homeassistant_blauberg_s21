"""Support for climate device."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.components.climate.const import (
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pybls21.client import S21Client
from pybls21.models import HVACAction as BlS21HVACAction
from pybls21.models import HVACMode as BlS21HVACMode

from .const import DOMAIN

HA_TO_S21_HVACMODE = {
    HVACMode.OFF: BlS21HVACMode.OFF,
    HVACMode.HEAT: BlS21HVACMode.HEAT,
    HVACMode.COOL: BlS21HVACMode.COOL,
    HVACMode.AUTO: BlS21HVACMode.AUTO,
    HVACMode.FAN_ONLY: BlS21HVACMode.FAN_ONLY,
}

S21_TO_HA_HVACMODE = {v: k for k, v in HA_TO_S21_HVACMODE.items()}

S21_TO_HA_HVACACTION = {
    BlS21HVACAction.COOLING: HVACAction.COOLING,
    BlS21HVACAction.FAN: HVACAction.FAN,
    BlS21HVACAction.HEATING: HVACAction.HEATING,
    BlS21HVACAction.IDLE: HVACAction.IDLE,
    BlS21HVACAction.OFF: HVACAction.OFF,
}

S21_TO_HA_FAN_MODE = {1: FAN_LOW, 2: FAN_MEDIUM, 3: FAN_HIGH, 255: "custom"}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a Blauberg S21 climate entity."""
    client: S21Client = hass.data[DOMAIN][config_entry.entry_id]

    entities = [BlS21ClimateEntity(client, config_entry)]
    async_add_entities(entities, True)


class BlS21ClimateEntity(ClimateEntity):
    """Representation of a Blauberg S21 climate feature."""

    _attr_translation_key = "s21climate"

    def __init__(self, client: S21Client, config_entry: ConfigEntry) -> None:
        self._client = client
        self._config_entry = config_entry

    @property
    def available(self) -> bool:
        if self._client.device:
            return self._client.device.available
        return False

    @property
    def name(self) -> str | None:
        if self._client.device:
            return self._client.device.name

    @property
    def unique_id(self) -> str | None:
        if self._config_entry.unique_id:
            return self._config_entry.unique_id
        if self._client.device:
            return self._client.device.unique_id

    @property
    def temperature_unit(self) -> str:
        return UnitOfTemperature.CELSIUS

    @property
    def precision(self) -> float | None:
        if self._client.device:
            return self._client.device.precision

    @property
    def current_temperature(self) -> float | None:
        if self._client.device:
            return self._client.device.current_supply_temperature

    @property
    def target_temperature(self) -> float | None:
        if self._client.device:
            return self._client.device.target_temperature

    @property
    def target_temperature_step(self) -> float | None:
        if self._client.device:
            return self._client.device.target_temperature_step

    @property
    def max_temp(self) -> float | None:
        if self._client.device:
            return self._client.device.max_temp

    @property
    def min_temp(self) -> float | None:
        if self._client.device:
            return self._client.device.min_temp

    @property
    def current_humidity(self) -> float | None:
        if self._client.device:
            return self._client.device.current_humidity

    @property
    def hvac_mode(self) -> HVACMode | None:
        if self._client.device:
            return S21_TO_HA_HVACMODE.get(self._client.device.hvac_mode)

    @property
    def hvac_action(self) -> HVACAction | None:
        if self._client.device:
            return S21_TO_HA_HVACACTION.get(self._client.device.hvac_action)

    @property
    def hvac_modes(self) -> list[HVACMode] | None:
        if self._client.device:
            return [
                S21_TO_HA_HVACMODE[m]
                for m in self._client.device.hvac_modes
                if m in S21_TO_HA_HVACMODE
            ]

    @property
    def fan_mode(self) -> str | None:
        if self._client.device:
            if self._client.device.max_fan_level == 3:
                return S21_TO_HA_FAN_MODE.get(
                    self._client.device.fan_mode, str(self._client.device.fan_mode)
                )
            return str(self._client.device.fan_mode)

    @property
    def fan_modes(self) -> list[str] | None:
        if self._client.device:
            if self._client.device.max_fan_level == 3:
                return [
                    S21_TO_HA_FAN_MODE.get(m, str(m))
                    for m in self._client.device.fan_modes
                ]
            return [str(m) for m in self._client.device.fan_modes]

    @property
    def supported_features(self) -> ClimateEntityFeature:
        return ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return information used by Home Assistant to register the device."""
        unique_id = self.unique_id
        if not unique_id:
            return None

        name = self._config_entry.title
        manufacturer = None
        model = None
        sw_version = None

        if self._client.device:
            name = self._client.device.name or name
            manufacturer = self._client.device.manufacturer
            model = self._client.device.model
            sw_version = self._client.device.sw_version

        return DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            name=name,
            manufacturer=manufacturer,
            model=model,
            sw_version=sw_version,
        )

    @property
    def icon(self) -> str | None:
        if self._client.device:
            if not self._client.device.available:
                return "mdi:lan-disconnect"
            if self._client.device.is_boosting:
                return "mdi:fan-plus"
            if self._client.device.hvac_action == BlS21HVACAction.OFF:
                return "mdi:fan-off"
            if self._client.device.hvac_action == BlS21HVACAction.IDLE:
                return "mdi:fan-remove"
            if self._client.device.max_fan_level == 3:
                if self._client.device.fan_mode == 1:
                    return "mdi:fan-speed-1"
                if self._client.device.fan_mode == 2:
                    return "mdi:fan-speed-2"
                if self._client.device.fan_mode == 3:
                    return "mdi:fan-speed-3"
            if self._client.device.hvac_action == BlS21HVACAction.COOLING:
                return "mdi:fan-chevron-down"
            if self._client.device.hvac_action == BlS21HVACAction.HEATING:
                return "mdi:fan-chevron-up"
            if self._client.device.hvac_action == BlS21HVACAction.FAN:
                return "mdi:fan"
        return "mdi:fan"

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode not in HA_TO_S21_HVACMODE:
            return
        await self._client.set_hvac_mode(HA_TO_S21_HVACMODE[hvac_mode])

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        previous_fan_mode = self.fan_mode
        int_fan_mode = (
            255
            if fan_mode == "custom"
            else 1
            if fan_mode == FAN_LOW
            else 2
            if fan_mode == FAN_MEDIUM
            else 3
            if fan_mode == FAN_HIGH
            else int(fan_mode)
        )
        await self._client.set_fan_mode(int_fan_mode)
        await self._client.poll()
        self.async_write_ha_state()

        current_fan_mode = self.fan_mode
        if (
            self.hass
            and self.entity_id
            and previous_fan_mode is not None
            and current_fan_mode is not None
            and previous_fan_mode != current_fan_mode
        ):
            self.hass.bus.async_fire(
                "logbook_entry",
                {
                    "name": self.name or self._config_entry.title,
                    "message": f"Fan mode changed: {previous_fan_mode} -> {current_fan_mode}",
                    "entity_id": self.entity_id,
                    "domain": DOMAIN,
                },
            )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            await self._client.set_temperature(int(temperature))

    async def async_reset_filter_change_timer(self) -> None:
        await self._client.reset_filter_change_timer()

    async def async_reset_alarm(self) -> None:
        await self._client.reset_alarm()

    async def async_update(self) -> None:
        await self._client.poll()

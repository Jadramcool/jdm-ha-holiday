"""JDM Holiday 二元传感器平台定义。

该文件定义了提供布尔状态（On/Off）的传感器实体。
包括：
1. Is Holiday Today: 今天是否放假（On=放假/周末，Off=上班）。
2. Is Holiday Tomorrow: 明天是否放假。
"""

import logging
from datetime import timedelta

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN
from .holiday_engine import Holiday

_LOGGER = logging.getLogger(__name__)

# 定义扫描间隔，即每隔多久自动更新一次传感器状态
SCAN_INTERVAL = timedelta(hours=4)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """设置 Holiday 二元传感器平台。

    该函数由 __init__.py 中的 discovery 机制调用。

    Args:
        hass: Home Assistant 核心实例。
        config: 配置信息。
        async_add_entities: 用于添加实体到 HA 的回调函数。
        discovery_info: 发现信息，如果不是通过 discovery 加载则为 None。
    """
    if discovery_info is None:
        return

    # 从全局数据中获取 Holiday 引擎实例
    engine: Holiday = hass.data[DOMAIN]["engine"]

    # 实例化传感器列表
    sensors = [
        # 今天是否放假
        HolidayBinarySensor(engine, 0, "Is Holiday Today"),
        # 明天是否放假
        HolidayBinarySensor(engine, 1, "Is Holiday Tomorrow"),
    ]

    # 添加传感器
    async_add_entities(sensors, True)


class HolidayBinarySensor(BinarySensorEntity):
    """节假日二元传感器。

    如果当天是休息日或节假日，状态为 On；如果是工作日，状态为 Off。
    """

    def __init__(self, engine: Holiday, day_offset: int, name: str):
        """初始化传感器。

        Args:
            engine: Holiday 引擎实例。
            day_offset: 天数偏移量，0为今天，1为明天。
            name: 传感器显示的名称。
        """
        self._engine = engine
        self._day_offset = day_offset
        self._attr_name = name
        self._attr_unique_id = f"jdm_is_holiday_{day_offset}"
        self._attr_icon = "mdi:calendar-check"
        self._is_on = False

    @property
    def is_on(self):
        """返回传感器的当前状态（True=On, False=Off）。"""
        return self._is_on

    def update(self) -> None:
        """更新传感器状态。

        判断目标日期是否为“工作日”。如果不是工作日（即休息日或节假日），则 is_on 为 True。
        """
        try:
            # 检查是否需要更新数据
            self._engine.get_holidays_from_server()

            # 获取目标日期
            date = self._engine.day(self._day_offset)
            # 获取日期类型："工作日", "休息日", "节假日"
            status = self._engine.is_holiday(date)
            # 只要不是 "工作日"，就认为是放假状态 (On)
            self._is_on = status != "工作日"
        except Exception as e:
            _LOGGER.error("更新二元传感器失败: %s", e)

"""JDM Holiday 传感器平台定义。

该文件定义了提供详细节假日信息的传感器实体。
包括：
1. Nearest Holiday Info: 显示最近一次节假日安排的详细文本信息。
2. Today/Tomorrow Holiday Type: 显示今天和明天的具体日期类型（工作日/休息日/节假日）。
"""

import logging
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN
from .holiday_engine import Holiday

_LOGGER = logging.getLogger(__name__)

# 定义扫描间隔，即每隔多久自动更新一次传感器状态
# 设置为 4 小时，因为节假日数据变动频率极低
SCAN_INTERVAL = timedelta(hours=4)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """设置 Holiday 传感器平台。

    该函数由 __init__.py 中的 discovery 机制调用。

    Args:
        hass: Home Assistant 核心实例。
        config: 配置信息。
        async_add_entities: 用于添加实体到 HA 的回调函数。
        discovery_info: 发现信息，如果不是通过 discovery 加载则为 None。
    """
    # 处理自动发现
    if discovery_info is not None:
        engine: Holiday = hass.data[DOMAIN]["engine"]
    else:
        # 处理显式配置
        engine = Holiday(config.get("anniversaries", {}))

    # 实例化单一传感器
    sensors = [
        HolidayCombinedSensor(engine),
    ]

    # 将传感器添加到 Home Assistant
    # update_before_add=True 表示添加前先执行一次 update 以获取初始状态
    async_add_entities(sensors, True)


class HolidayTypeSensor(SensorEntity):
    """节假日类型传感器 (工作日/休息日/节假日)。

    该传感器根据偏移量（0表示今天，1表示明天等）显示对应日期的类型。
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
        # 设置唯一 ID，确保 HA 可以唯一标识该实体
        self._attr_unique_id = f"jdm_holiday_type_{day_offset}"
        self._attr_icon = "mdi:calendar-question"
        self._state = None

    @property
    def native_value(self):
        """返回传感器的当前状态值。"""
        return self._state

    def update(self) -> None:
        """更新传感器状态。

        该方法会被 HA 定期调用（根据 SCAN_INTERVAL）。
        注意：默认情况下 update 方法是在线程池（Executor）中运行的，
        所以这里可以直接调用可能阻塞的同步方法。
        """
        try:
            # 根据偏移量计算目标日期
            date = self._engine.day(self._day_offset)
            # 获取该日期的类型（工作日/休息日/节假日）
            self._state = self._engine.is_holiday(date)

            # 获取详细信息并添加到 attributes (农历、宜忌等)
            detail = self._engine.get_day_detail(date)
            if not detail:
                detail = {}

            # 获取自定义纪念日
            anniversaries = self._engine.get_anniversaries(date)
            if anniversaries:
                detail["anniversaries"] = anniversaries

            self._attr_extra_state_attributes = detail

        except Exception as e:
            _LOGGER.error("更新节假日类型失败: %s", e)


class HolidayCombinedSensor(SensorEntity):
    """整合所有节假日信息的单一传感器。

    该传感器整合了所有节假日信息，包括今天、明天的日期类型，
    最近的节假日安排，以及自定义纪念日。
    """

    def __init__(self, engine: Holiday):
        """初始化传感器。"""
        self._engine = engine
        self._attr_name = "jdm_holiday"
        self._attr_unique_id = "jdm_holiday"
        self._attr_icon = "mdi:calendar"
        self._state = "正常"
        self._attr_extra_state_attributes = {}

    @property
    def native_value(self):
        """返回传感器的当前状态值。"""
        return self._state

    def update(self) -> None:
        """更新传感器状态。

        整合所有节假日信息到属性中，方便前端使用。
        """
        try:
            # 获取今天和明天的日期
            today = self._engine.day(0)
            tomorrow = self._engine.day(1)

            # 获取今天的信息
            today_status = self._engine.is_holiday(today)
            today_detail = self._engine.get_day_detail(today) or {}
            today_anniversaries = self._engine.get_anniversaries(today)
            future_anniversaries = self._engine.get_future_anniversaries(today)

            # 获取明天的信息
            tomorrow_status = self._engine.is_holiday(tomorrow)
            tomorrow_detail = self._engine.get_day_detail(tomorrow) or {}
            tomorrow_anniversaries = self._engine.get_anniversaries(tomorrow)

            # 获取最近节假日信息
            nearest_info = self._engine.nearest_holiday_info()
            nearest_holiday = self._engine.get_nearest_holiday() or {}

            # 整合所有数据
            combined_data = {
                "today": {
                    "status": today_status,
                    "detail": today_detail,
                    "anniversaries": today_anniversaries,
                },
                "tomorrow": {
                    "status": tomorrow_status,
                    "detail": tomorrow_detail,
                    "anniversaries": tomorrow_anniversaries,
                },
                "nearest_info": nearest_info,
                "nearest_holiday": nearest_holiday,
                "anniversaries_future": future_anniversaries,
            }

            self._attr_extra_state_attributes = combined_data

        except Exception as e:
            _LOGGER.error("更新整合传感器失败: %s", e)

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

            # 1. 预先计算未来纪念日，供后续复用
            future_anniversaries = self._engine.get_future_anniversaries(today)

            # 2. 获取最近节假日信息 (复用纪念日数据)
            nearest_info = self._engine.nearest_holiday_info()
            nearest_holiday = self._engine.get_nearest_statutory_holiday() or {}
            # 优化：传入 future_anniversaries 避免重复计算
            nearest_festival = self._engine.get_nearest_festival(anniversaries=future_anniversaries) or {}
            nearest_jieqi = self._engine.get_nearest_jieqi() or {}

            # 3. 获取今天的信息
            today_status = self._engine.is_holiday(today)
            today_detail = self._engine.get_day_detail(today) or {}
            # 优化：直接从 detail 中获取 anniversaries，避免重复调用 get_anniversaries
            today_anniversaries = today_detail.get("anniversaries", [])

            # 4. 获取明天的信息
            tomorrow_status = self._engine.is_holiday(tomorrow)
            tomorrow_detail = self._engine.get_day_detail(tomorrow) or {}
            # 优化：直接从 detail 中获取 anniversaries
            tomorrow_anniversaries = tomorrow_detail.get("anniversaries", [])

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
                "nearest_festival": nearest_festival,
                "nearest_jieqi": nearest_jieqi,
                "anniversaries_future": future_anniversaries,
            }

            self._attr_extra_state_attributes = combined_data

        except Exception as e:
            _LOGGER.error("更新整合传感器失败: %s", e)

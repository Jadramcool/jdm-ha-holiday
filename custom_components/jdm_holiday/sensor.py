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
    # 如果 discovery_info 为 None，说明不是通过 discovery 加载的，直接返回
    if discovery_info is None:
        return

    # 从全局数据中获取 Holiday 引擎实例
    engine: Holiday = hass.data[DOMAIN]["engine"]
    
    # 实例化传感器列表
    sensors = [
        # 显示最近节假日详情的传感器
        HolidayInfoSensor(engine),
        # 显示今天日期类型的传感器
        HolidayTypeSensor(engine, 0, "Today Holiday Type"),
        # 显示明天日期类型的传感器
        HolidayTypeSensor(engine, 1, "Tomorrow Holiday Type"),
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
            if detail:
                self._attr_extra_state_attributes = detail
            else:
                self._attr_extra_state_attributes = {}
                
        except Exception as e:
            _LOGGER.error("更新节假日类型失败: %s", e)


class HolidayInfoSensor(SensorEntity):
    """节假日详情传感器。
    
    该传感器显示最近一次节假日的详细安排，包括放假时间、调休情况等。
    """

    def __init__(self, engine: Holiday):
        """初始化传感器。"""
        self._engine = engine
        self._attr_name = "Nearest Holiday Info"
        self._attr_unique_id = "jdm_holiday_nearest_info"
        self._attr_icon = "mdi:calendar-star"
        self._state = None
        self._attr_extra_state_attributes = {}

    @property
    def native_value(self):
        """返回传感器的当前状态值。"""
        return self._state

    def update(self) -> None:
        """更新传感器状态。
        
        获取最近的节假日信息。如果信息过长，State 中只存储摘要，
        完整信息存储在属性（attributes）中。
        """
        try:
            # 获取最近的节假日信息文本
            info = self._engine.nearest_holiday_info()
            
            # HA 数据库对 State 字段有 255 字符长度限制
            # 如果信息过长，截取前 250 个字符并添加省略号
            if len(info) > 255:
                self._state = info[:250] + "..."
            else:
                self._state = info
            
            # 将完整信息存储在实体的属性中
            self._attr_extra_state_attributes["full_info"] = info
            
        except Exception as e:
            _LOGGER.error("更新节假日详情失败: %s", e)

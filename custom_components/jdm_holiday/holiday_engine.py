#!/usr/local/bin/python3
# coding=utf-8
"""
Holiday 模块

核心逻辑：
1. 从服务端（API）获取节假日数据。
2. 将数据存入本地 JSON 文件进行缓存。
3. 提供查询接口，判断特定日期是否为节假日，或获取最近的节假日安排。
"""

import datetime
import json
import logging
import os
import sqlite3
import time
from datetime import datetime as datetime_class
from datetime import timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter

_LOGGER = logging.getLogger(__name__)

# 使用当前文件所在目录作为数据存储目录
DATA_DIR = os.path.dirname(os.path.realpath(__file__))
# JSON 缓存文件路径
HOLIDAY_DATA_FILE = os.path.join(DATA_DIR, "holiday.json")
# SQLite 数据库路径
HOLIDAY_DB_FILE = os.path.join(DATA_DIR, "data.db")
# API 地址
API_URL = "http://tool.bitefu.net/jiari/"

_SOLAR_FESTIVAL = {
    "0101": ["元旦节"],
    "0202": ["世界湿地日"],
    "0210": ["国际气象节"],
    "0214": ["情人节"],
    "0301": ["国际海豹日"],
    "0303": ["全国爱耳日"],
    "0305": ["学雷锋纪念日"],
    "0308": ["妇女节"],
    "0312": ["植树节", "孙中山逝世纪念日"],
    "0314": ["国际警察日"],
    "0315": ["消费者权益日"],
    "0317": ["中国国医节", "国际航海日"],
    "0321": ["世界森林日", "消除种族歧视国际日", "世界儿歌日"],
    "0322": ["世界水日"],
    "0323": ["世界气象日"],
    "0324": ["世界防治结核病日"],
    "0325": ["全国中小学生安全教育日"],
    "0330": ["巴勒斯坦国土日"],
    "0401": ["愚人节", "全国爱国卫生运动月(四月)", "税收宣传月(四月)"],
    "0407": ["世界卫生日"],
    "0422": ["世界地球日"],
    "0423": ["世界图书和版权日"],
    "0424": ["亚非新闻工作者日"],
    "0501": ["劳动节"],
    "0504": ["青年节"],
    "0505": ["碘缺乏病防治日"],
    "0508": ["世界红十字日"],
    "0512": ["国际护士节"],
    "0515": ["国际家庭日"],
    "0517": ["国际电信日"],
    "0518": ["国际博物馆日"],
    "0520": ["全国学生营养日"],
    "0523": ["国际牛奶日"],
    "0531": ["世界无烟日"],
    "0601": ["国际儿童节"],
    "0605": ["世界环境保护日"],
    "0606": ["全国爱眼日"],
    "0617": ["防治荒漠化和干旱日"],
    "0623": ["国际奥林匹克日"],
    "0625": ["全国土地日"],
    "0626": ["国际禁毒日"],
    "0701": ["中国共·产党诞辰", "香港回归纪念日", "世界建筑日"],
    "0702": ["国际体育记者日"],
    "0707": ["抗日战争纪念日"],
    "0711": ["世界人口日"],
    "0730": ["非洲妇女日"],
    "0801": ["建军节"],
    "0808": ["中国男子节(爸爸节)"],
    "0815": ["抗日战争胜利纪念"],
    "0908": ["国际扫盲日", "国际新闻工作者日"],
    "0909": ["毛·泽东逝世纪念"],
    "0910": ["中国教师节"],
    "0914": ["世界清洁地球日"],
    "0916": ["国际臭氧层保护日"],
    "0918": ["九·一八事变纪念日"],
    "0920": ["国际爱牙日"],
    "0927": ["世界旅游日"],
    "0928": ["孔子诞辰"],
    "1001": ["国庆节", "世界音乐日", "国际老人节"],
    "1002": ["国庆节假日", "国际和平与民主自由斗争日"],
    "1003": ["国庆节假日"],
    "1004": ["世界动物日"],
    "1006": ["老人节"],
    "1008": ["全国高血压日", "世界视觉日"],
    "1009": ["世界邮政日", "万国邮联日"],
    "1010": ["辛亥革命纪念日", "世界精神卫生日"],
    "1013": ["世界保健日", "国际教师节"],
    "1014": ["世界标准日"],
    "1015": ["国际盲人节(白手杖节)"],
    "1016": ["世界粮食日"],
    "1017": ["世界消除贫困日"],
    "1022": ["世界传统医药日"],
    "1024": ["联合国日"],
    "1031": ["世界勤俭日"],
    "1107": ["十月社会主义革命纪念日"],
    "1108": ["中国记者日"],
    "1109": ["全国消防安全宣传教育日"],
    "1110": ["世界青年节"],
    "1111": ["光棍节", "国际科学与和平周(本日所属的一周)"],
    "1112": ["孙中山诞辰纪念日"],
    "1114": ["世界糖尿病日"],
    "1116": ["国际宽容日"],
    "1117": ["国际大学生节", "世界学生节"],
    "1120": ["彝族年"],
    "1121": ["彝族年", "世界问候日", "世界电视日"],
    "1122": ["彝族年"],
    "1129": ["国际声援巴勒斯坦人民国际日"],
    "1201": ["世界艾滋病日"],
    "1203": ["世界残疾人日"],
    "1205": ["国际志愿人员日"],
    "1208": ["国际儿童电视日"],
    "1209": ["世界足球日"],
    "1210": ["世界人权日"],
    "1212": ["西安事变纪念日"],
    "1213": ["南京大屠杀(1937年)纪念日"],
    "1220": ["澳门回归纪念日"],
    "1221": ["国际篮球日"],
    "1224": ["平安夜"],
    "1225": ["圣诞节"],
    "1226": ["毛·泽东诞辰纪念日"],
}

_LUNAR_FESTIVAL = {
    "0101": ["春节"],
    "0115": ["元宵节"],
    "0202": ["春龙节"],
    "0505": ["端午节"],
    "0707": ["七夕情人节"],
    "0715": ["中元节"],
    "0815": ["中秋节"],
    "0909": ["重阳节"],
    "1208": ["腊八节"],
    "1223": ["小年"],
    "1229": ["除夕"],
}

_WEEKDAY_FESTIVAL = {
    "0150": ["世界防治麻风病日"],
    "0520": ["母亲节"],
    "0530": ["全国助残日"],
    "0630": ["父亲节"],
    "0730": ["被奴役国家周"],
    "0932": ["国际和平日"],
    "0940": ["国际聋人节", "世界儿童日"],
    "0950": ["世界海事日"],
    "1011": ["国际住房日"],
    "1013": ["国际减轻自然灾害日(减灾日)"],
    "1144": ["感恩节"],
}

_WEEKDAY_FESTIVAL_CACHE: Dict[int, Dict[str, List[str]]] = {}


def _festival_handle(params: Dict[str, List[str]], month: int, day: int) -> List[str]:
    key = "{:0>2d}{:0>2d}".format(month, day)
    return params.get(key, [])


def _build_weekday_festival(year: int) -> Dict[str, List[str]]:
    if year in _WEEKDAY_FESTIVAL_CACHE:
        return _WEEKDAY_FESTIVAL_CACHE[year]
    data: Dict[str, List[str]] = {}
    for key, value in _WEEKDAY_FESTIVAL.items():
        month = int(key[:2])
        w = int(key[3:])
        n = int(key[2])
        first = datetime.date(year, month, 1).weekday() + 1
        day = 1 + 7 - first + w + (n - 1) * 7
        if day > 30:
            day = day - 7
        date_key = "{:0>2d}{:0>2d}".format(month, day)
        data[date_key] = value
    _WEEKDAY_FESTIVAL_CACHE[year] = data
    return data


class LunarDate:
    _startDate = datetime.date(1900, 1, 31)

    @staticmethod
    def fromSolarDate(year, month, day):
        solarDate = datetime.date(year, month, day)
        offset = (solarDate - LunarDate._startDate).days
        return LunarDate._fromOffset(offset)

    @classmethod
    def toSolarDate(cls, year, month, day, isLeapMonth=False):
        """将农历日期转换为公历日期"""
        # 1. 计算从 1900 到目标年份之前所有年份的总天数
        offset = 0
        for y in range(1900, year):
            idx = y - 1900
            if idx < 0 or idx >= len(Info.yearInfos):
                raise ValueError(f"Year {y} out of range")
            offset += Info.yearInfo2yearDay(Info.yearInfos[idx])

        # 2. 计算目标年份中，目标月份之前的天数
        idx = year - 1900
        if idx < 0 or idx >= len(Info.yearInfos):
            raise ValueError(f"Year {year} out of range")
        yearInfo = Info.yearInfos[idx]
        
        found = False
        for m, d, is_leap in cls._enumMonth(yearInfo):
            if m == month and is_leap == isLeapMonth:
                found = True
                break
            offset += d
        
        if not found:
             raise ValueError(f"Invalid lunar date: {year}-{month}-{day} (leap={isLeapMonth})")

        # 3. 加上当月的天数 (day 是从1开始的)
        offset += (day - 1)
        
        return cls._startDate + timedelta(days=offset)

    @staticmethod
    def _enumMonth(yearInfo):
        months = [(i, 0) for i in range(1, 13)]
        leapMonth = yearInfo % 16
        if leapMonth == 0:
            pass
        elif leapMonth <= 12:
            months.insert(leapMonth, (leapMonth, 1))
        else:
            raise ValueError("yearInfo %r mod 16 should in [0, 12]" % yearInfo)

        for month, isLeapMonth in months:
            if isLeapMonth:
                days = (yearInfo >> 16) % 2 + 29
            else:
                days = (yearInfo >> (16 - month)) % 2 + 29
            yield month, days, isLeapMonth

    @classmethod
    def _fromOffset(cls, offset):
        def _calcMonthDay(yearInfo, offset):
            for month, days, isLeapMonth in cls._enumMonth(yearInfo):
                if offset < days:
                    break
                offset -= days
            return (month, offset + 1, isLeapMonth)

        offset = int(offset)

        for idx, yearDay in enumerate(Info.yearDays()):
            if offset < yearDay:
                break
            offset -= yearDay
        year = 1900 + idx

        yearInfo = Info.yearInfos[idx]
        month, day, isLeapMonth = _calcMonthDay(yearInfo, offset)
        return LunarDate(year, month, day, isLeapMonth)

    def __init__(self, year, month, day, isLeapMonth=False):
        self.year = year
        self.month = month
        self.day = day
        self.isLeapMonth = bool(isLeapMonth)


class Info:
    yearInfos = [
        0x04BD8,
        0x04AE0,
        0x0A570,
        0x054D5,
        0x0D260,
        0x0D950,
        0x16554,
        0x056A0,
        0x09AD0,
        0x055D2,
        0x04AE0,
        0x0A5B6,
        0x0A4D0,
        0x0D250,
        0x1D255,
        0x0B540,
        0x0D6A0,
        0x0ADA2,
        0x095B0,
        0x14977,
        0x04970,
        0x0A4B0,
        0x0B4B5,
        0x06A50,
        0x06D40,
        0x1AB54,
        0x02B60,
        0x09570,
        0x052F2,
        0x04970,
        0x06566,
        0x0D4A0,
        0x0EA50,
        0x06E95,
        0x05AD0,
        0x02B60,
        0x186E3,
        0x092E0,
        0x1C8D7,
        0x0C950,
        0x0D4A0,
        0x1D8A6,
        0x0B550,
        0x056A0,
        0x1A5B4,
        0x025D0,
        0x092D0,
        0x0D2B2,
        0x0A950,
        0x0B557,
        0x06CA0,
        0x0B550,
        0x15355,
        0x04DA0,
        0x0A5D0,
        0x14573,
        0x052D0,
        0x0A9A8,
        0x0E950,
        0x06AA0,
        0x0AEA6,
        0x0AB50,
        0x04B60,
        0x0AAE4,
        0x0A570,
        0x05260,
        0x0F263,
        0x0D950,
        0x05B57,
        0x056A0,
        0x096D0,
        0x04DD5,
        0x04AD0,
        0x0A4D0,
        0x0D4D4,
        0x0D250,
        0x0D558,
        0x0B540,
        0x0B5A0,
        0x195A6,
        0x095B0,
        0x049B0,
        0x0A974,
        0x0A4B0,
        0x0B27A,
        0x06A50,
        0x06D40,
        0x0AF46,
        0x0AB60,
        0x09570,
        0x04AF5,
        0x04970,
        0x064B0,
        0x074A3,
        0x0EA50,
        0x06B58,
        0x05AC0,
        0x0AB60,
        0x096D5,
        0x092E0,
        0x0C960,
        0x0D954,
        0x0D4A0,
        0x0DA50,
        0x07552,
        0x056A0,
        0x0ABB7,
        0x025D0,
        0x092D0,
        0x0CAB5,
        0x0A950,
        0x0B4A0,
        0x0BAA4,
        0x0AD50,
        0x055D9,
        0x04BA0,
        0x0A5B0,
        0x15176,
        0x052B0,
        0x0A930,
        0x07954,
        0x06AA0,
        0x0AD50,
        0x05B52,
        0x04B60,
        0x0A6E6,
        0x0A4E0,
        0x0D260,
        0x0EA65,
        0x0D530,
        0x05AA0,
        0x076A3,
        0x096D0,
        0x04AFB,
        0x04AD0,
        0x0A4D0,
        0x1D0B6,
        0x0D250,
        0x0D520,
        0x0DD45,
        0x0B5A0,
        0x056D0,
        0x055B2,
        0x049B0,
        0x0A577,
        0x0A4B0,
        0x0AA50,
        0x1B255,
        0x06D20,
        0x0ADA0,
    ]

    def yearInfo2yearDay(yearInfo):
        info = int(yearInfo)
        months = 12 + (1 if info % 16 else 0)
        return 29 * months + ((info // 16) & ((1 << months) - 1)).bit_count()

    def yearDays():
        return [Info.yearInfo2yearDay(x) for x in Info.yearInfos]


class HolidayDB:
    """简化的 SQLite 存储封装，用于数据备份。"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_table()

    def _get_conn(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _ensure_columns(self, conn, table_name: str, columns: Dict[str, str]):
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        existing = {row[1] for row in cursor.fetchall()}
        for name, col_type in columns.items():
            if name in existing:
                continue
            conn.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {name} {col_type}")

    def _init_table(self):
        """初始化全量数据表"""
        try:
            with self._get_conn() as conn:
                # 1. 创建元数据表
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS meta_info (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                """
                )

                # 2. 创建详细数据表 (字段一一对应)
                # day: 20260201
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS holiday_detail (
                        day TEXT PRIMARY KEY,
                        status INTEGER,
                        type INTEGER,
                        typename TEXT,
                        unixtime INTEGER,
                        yearname TEXT,
                        nonglicn TEXT,
                        nongli TEXT,
                        shengxiao TEXT,
                        jieqi TEXT,
                        weekcn TEXT,
                        week1 TEXT,
                        week2 TEXT,
                        week3 TEXT,
                        daynum INTEGER,
                        weeknum INTEGER,
                        avoid TEXT,
                        suit TEXT,
                        solar_festival TEXT,
                        lunar_festival TEXT,
                        festival TEXT
                    )
                """
                )
                self._ensure_columns(
                    conn,
                    "holiday_detail",
                    {
                        "solar_festival": "TEXT",
                        "lunar_festival": "TEXT",
                        "festival": "TEXT",
                    },
                )
                conn.commit()
        except Exception as e:
            _LOGGER.error("初始化数据库失败: %s", e)

    def save_full(self, data_list: List[Dict[str, Any]], update_time: str):
        """保存全量数据列表到数据库"""
        try:
            with self._get_conn() as conn:
                # 1. 保存更新时间
                conn.execute(
                    "REPLACE INTO meta_info (key, value) VALUES (?, ?)",
                    ("update_time", update_time),
                )

                # 2. 保存详细数据
                for item in data_list:
                    conn.execute(
                        """
                        REPLACE INTO holiday_detail (
                            day, status, type, typename, unixtime, yearname, 
                            nonglicn, nongli, shengxiao, jieqi, weekcn, 
                            week1, week2, week3, daynum, weeknum, avoid, suit,
                            solar_festival, lunar_festival, festival
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            item.get("day"),
                            item.get("status"),
                            item.get("type"),
                            item.get("typename"),
                            item.get("unixtime"),
                            item.get("yearname"),
                            item.get("nonglicn"),
                            item.get("nongli"),
                            item.get("shengxiao"),
                            item.get("jieqi"),
                            item.get("weekcn"),
                            item.get("week1"),
                            item.get("week2"),
                            item.get("week3"),
                            item.get("daynum"),
                            item.get("weeknum"),
                            item.get("avoid"),
                            item.get("suit"),
                            json.dumps(item.get("solar_festival")
                                       or [], ensure_ascii=False),
                            json.dumps(item.get("lunar_festival")
                                       or [], ensure_ascii=False),
                            json.dumps(item.get("festival")
                                       or [], ensure_ascii=False),
                        ),
                    )
                conn.commit()
        except Exception as e:
            _LOGGER.error("备份数据到数据库失败: %s", e)

    def load(self) -> Dict[str, Any]:
        """从数据库加载数据（重构为内存使用的格式）"""
        data = {}
        try:
            if not os.path.exists(self.db_path):
                return data

            with self._get_conn() as conn:
                conn.row_factory = sqlite3.Row  # 允许通过列名访问

                # 1. 加载更新时间
                cursor = conn.execute(
                    "SELECT value FROM meta_info WHERE key='update_time'"
                )
                row = cursor.fetchone()
                if row:
                    data["update_time"] = row[0]

                # 2. 加载节假日数据，重构为 {year: {mmdd: full_item_dict}} 格式
                cursor = conn.execute("SELECT * FROM holiday_detail")
                for row in cursor:
                    item = dict(row)  # 转换为字典
                    item["solar_festival"] = self._parse_json_list(
                        item.get("solar_festival")
                    )
                    item["lunar_festival"] = self._parse_json_list(
                        item.get("lunar_festival")
                    )
                    item["festival"] = self._parse_json_list(
                        item.get("festival"))
                    day_str = item.get("day")
                    if not day_str or len(day_str) != 8:
                        continue

                    year = day_str[:4]
                    date_short = day_str[4:]  # MMDD

                    if year not in data:
                        data[year] = {}

                    # 存储完整数据对象
                    data[year][date_short] = item

        except Exception as e:
            _LOGGER.error("从数据库加载数据失败: %s", e)
        return data

    def get_day_detail(self, day_str: str) -> Dict[str, Any]:
        try:
            if not os.path.exists(self.db_path):
                return {}
            with self._get_conn() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM holiday_detail WHERE day = ?", (day_str,)
                )
                row = cursor.fetchone()
                if not row:
                    return {}
                item = dict(row)
                item["solar_festival"] = self._parse_json_list(
                    item.get("solar_festival")
                )
                item["lunar_festival"] = self._parse_json_list(
                    item.get("lunar_festival")
                )
                item["festival"] = self._parse_json_list(item.get("festival"))
                return item
        except Exception as e:
            _LOGGER.error("从数据库获取日期详情失败: %s", e)
            return {}

    def _parse_json_list(self, value):
        if not value:
            return []
        try:
            data = json.loads(value)
            if isinstance(data, list):
                return data
            return []
        except Exception:
            return []


class Holiday:
    """节假日核心逻辑类。

    提供公共方法：
    - is_holiday(date): 判断某天是否为节日。
    - is_holiday_today(): 判断今天是否为节假日。
    - nearest_holiday_info(): 获取最近的节假日安排信息。
    """

    # 状态码映射
    STATUS_MAP = {0: "工作日", 1: "休息日", 2: "节假日"}

    def __init__(self, anniversaries=None):
        """初始化 Holiday 类。"""
        self._holiday_json: Dict[str, Any] = {}
        self._anniversaries = anniversaries or {}  # 自定义纪念日
        self.db = HolidayDB(HOLIDAY_DB_FILE)  # 初始化数据库备份

        self.session = requests.Session()
        # 设置重试策略和 Headers
        adapter = HTTPAdapter(max_retries=3)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )

        # 初始化时尝试从本地磁盘加载缓存的节假日数据
        self.get_holidays_from_disk()

    @classmethod
    def day(cls, n: int) -> datetime.datetime:
        """获取相对于今天的第 n 天的日期对象。

        Args:
            n: 天数偏移量。1 表示明天，-1 表示昨天。

        Returns:
            datetime: 计算后的日期对象（UTC+8）。
        """
        # 使用 timezone-aware 对象获取 UTC 时间，然后转换为北京时间
        utc_now = datetime_class.now(timezone.utc)
        return utc_now + timedelta(hours=8) + timedelta(hours=n * 24)

    @classmethod
    def today(cls) -> datetime.datetime:
        """获取今天的日期对象。"""
        return Holiday.day(0)

    @classmethod
    def tomorrow(cls) -> datetime.datetime:
        """获取明天的日期对象。"""
        return Holiday.day(1)

    def _collect_holiday_candidates(
        self, today: datetime.datetime
    ) -> List[datetime.datetime]:
        """收集所有符合条件的节假日候选日期。

        Args:
            today: 今天的日期对象

        Returns:
            List[datetime]: 排序后的节假日日期列表
        """
        current_year = str(today.year)
        next_year = str(today.year + 1)
        target_years = [y for y in self._holiday_json if y in (
            current_year, next_year)]
        candidates = []

        # 将 timezone-aware 的 today 转换为 naive datetime 以便比较
        if today.tzinfo is not None:
            today_naive = today.replace(tzinfo=None)
        else:
            today_naive = today

        for y in target_years:
            dates = self._holiday_json[y]
            if not isinstance(dates, dict):
                continue
            for m_d, item in dates.items():
                if self._is_holiday_item(item):
                    date = self._parse_holiday_date(item, y, m_d)
                    if date and (date - today_naive).days >= 0:
                        candidates.append(date)

        candidates.sort()
        return candidates

    def _is_holiday_item(self, item: Any) -> bool:
        """判断是否为法定节假日。

        Args:
            item: 节假日数据项

        Returns:
            bool: 是否为法定节假日
        """
        type_val = 0
        if isinstance(item, dict):
            # 兼容处理：typename 存在即认为是节日，或者 type=2
            # 实际上有些数据 type=2 是法定节假日，type=1 是周末
            # 原始逻辑只判断 type==2
            type_val = int(item.get("type", 0))
        else:
            type_val = int(item)
        return type_val == 2

    def _parse_holiday_date(
        self, item: Any, year: str, month_day: str
    ) -> Optional[datetime.datetime]:
        """解析节假日日期。

        Args:
            item: 节假日数据项
            year: 年份字符串
            month_day: 月日字符串 (MMDD)

        Returns:
            Optional[datetime]: 解析后的日期对象，失败返回 None
        """
        try:
            if isinstance(item, dict) and "day" in item:
                d_str = item["day"]
                return datetime_class.strptime(d_str, "%Y%m%d")
            d_str = "{}-{}-{}".format(year, month_day[0:2], month_day[2:])
            return datetime_class.strptime(d_str, "%Y-%m-%d")
        except ValueError:
            return None

    def nearest_holiday_info(self, min_days: int = 0, max_days: int = 60) -> str:
        """计算并获取最近一次节假日的详细安排。

        Args:
            min_days: 最小查找天数范围。
            max_days: 最大查找天数范围。

        Returns:
            str: 格式化后的节假日信息文本。
        """
        today = Holiday.today()
        if not self._holiday_json:
            self.get_holidays_from_server()

        candidates = self._collect_holiday_candidates(today)

        # 将 timezone-aware 的 today 转换为 naive datetime 以便比较
        if today.tzinfo is not None:
            today_naive = today.replace(tzinfo=None)
        else:
            today_naive = today

        for date in candidates:
            days_diff = (date - today_naive).days
            if not (min_days <= days_diff <= max_days):
                continue

            start, end = self._find_holiday_range(date)
            before_workdays = self._find_surrounding_workdays(
                start, look_back=True)
            after_workdays = self._find_surrounding_workdays(
                end, look_back=False)

            return self._format_holiday_info(
                today_naive, start, end, before_workdays, after_workdays
            )

        return "无最近节假日信息"

    def get_nearest_statutory_holiday(
        self, min_days: int = 0, max_days: int = 60
    ) -> Optional[Dict[str, Any]]:
        """获取最近一次法定节假日的详细信息对象。

        Args:
            min_days: 最小查找天数范围。
            max_days: 最大查找天数范围。

        Returns:
            Optional[Dict]: 包含节假日详细信息的字典，无结果时返回 None。
        """
        today = Holiday.today()
        if not self._holiday_json:
            self.get_holidays_from_server()

        # 将 timezone-aware 的 today 转换为 naive datetime 以便比较
        if today.tzinfo is not None:
            today_naive = today.replace(tzinfo=None)
        else:
            today_naive = today

        candidates = self._collect_holiday_candidates(today)

        for date in candidates:
            days_diff = (date - today_naive).days
            if not (min_days <= days_diff <= max_days):
                continue

            # 查找节假日的完整信息
            year = str(date.year)
            month_day = date.strftime("%m%d")
            if year in self._holiday_json and month_day in self._holiday_json[year]:
                holiday_item = self._holiday_json[year][month_day]
                return {
                    "date": date,
                    "name": holiday_item.get("typename", "未知节假日"),
                    "days_diff": days_diff,
                    "full_info": holiday_item,
                }
        return None

    def get_nearest_festival(
        self, min_days: int = 0, max_days: int = 60, anniversaries: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[Dict[str, Any]]:
        """获取最近一次节日（含法定、公历、农历、纪念日）的详细信息对象。

        Args:
            min_days: 最小查找天数范围。
            max_days: 最大查找天数范围。
            anniversaries: 可选的预计算纪念日列表，避免重复计算。

        Returns:
            Optional[Dict]: 包含节假日详细信息的字典，无结果时返回 None。
        """
        today = Holiday.today()
        if not self._holiday_json:
            self.get_holidays_from_server()

        # 将 timezone-aware 的 today 转换为 naive datetime 以便比较
        if today.tzinfo is not None:
            today_naive = today.replace(tzinfo=None)
        else:
            today_naive = today

        all_candidates = []

        # 1. 收集法定节假日候选日期 (priority=1)
        statutory_candidates = self._collect_holiday_candidates(today)
        for date in statutory_candidates:
            days_diff = (date - today_naive).days
            if not (min_days <= days_diff <= max_days):
                continue
            
            year = str(date.year)
            month_day = date.strftime("%m%d")
            if year in self._holiday_json and month_day in self._holiday_json[year]:
                holiday_item = self._holiday_json[year][month_day]
                all_candidates.append({
                    "date": date,
                    "name": holiday_item.get("typename", "未知节假日"),
                    "days_diff": days_diff,
                    "full_info": holiday_item,
                    "priority": 1
                })

        # 2. 收集公历节日 (priority=2)
        for date_str, names in _SOLAR_FESTIVAL.items():
            month = int(date_str[:2])
            day = int(date_str[2:])
            try:
                # 尝试今年
                d = datetime_class(today_naive.year, month, day)
                if d < today_naive:
                    # 如果已过，尝试明年
                    d = datetime_class(today_naive.year + 1, month, day)
                
                days_diff = (d - today_naive).days
                if min_days <= days_diff <= max_days:
                    all_candidates.append({
                        "date": d,
                        "name": names[0],
                        "days_diff": days_diff,
                        "full_info": {"festival": names},
                        "priority": 2
                    })
            except ValueError:
                continue

        # 3. 收集农历节日 (priority=2)
        for date_str, names in _LUNAR_FESTIVAL.items():
            month = int(date_str[:2])
            day = int(date_str[2:])
            try:
                # 获取今天的农历年份
                ld_today = LunarDate.fromSolarDate(today_naive.year, today_naive.month, today_naive.day)
                
                # 尝试今年的农历日期
                d = LunarDate.toSolarDate(ld_today.year, month, day)
                d_dt = datetime_class(d.year, d.month, d.day)
                
                if d_dt < today_naive:
                    # 如果已过，尝试明年
                    d = LunarDate.toSolarDate(ld_today.year + 1, month, day)
                    d_dt = datetime_class(d.year, d.month, d.day)
                
                days_diff = (d_dt - today_naive).days
                if min_days <= days_diff <= max_days:
                    all_candidates.append({
                        "date": d_dt,
                        "name": names[0],
                        "days_diff": days_diff,
                        "full_info": {"festival": names},
                        "priority": 2
                    })
            except Exception:
                continue

        # 4. 收集自定义纪念日 (priority=0)
        if anniversaries is None:
            anniversaries = self.get_future_anniversaries(today)
            
        for item in anniversaries:
            try:
                d_dt = datetime_class.strptime(item['date'], "%Y-%m-%d")
                days_diff = item['days_diff']
                if min_days <= days_diff <= max_days:
                    all_candidates.append({
                        "date": d_dt,
                        "name": item['name'],
                        "days_diff": days_diff,
                        "full_info": {"festival": [item['name']]},
                        "priority": 0
                    })
            except Exception:
                continue

        if not all_candidates:
            return None

        # 排序：先按天数差（从小到大），再按优先级（从小到大，越小越高）
        all_candidates.sort(key=lambda x: (x['days_diff'], x['priority']))

        return all_candidates[0]

    def get_anniversaries(self, date: datetime.datetime) -> List[str]:
        """获取指定日期的自定义纪念日。

        支持的配置格式（key）：
        - "YYYY-MM-DD": 公历一次性纪念日（仅在该日期触发）
        - "MM-DD": 公历每年纪念日
        - "nYYYY-MM-DD": 农历一次性纪念日
        - "nMM-DD": 农历每年纪念日
        """
        anniversaries = []

        # 公历部分
        g_year = date.year
        g_month = date.month
        g_day = date.day

        # 农历部分
        ld = LunarDate.fromSolarDate(g_year, g_month, g_day)
        l_year = ld.year
        l_month = ld.month
        l_day = ld.day

        for key, value in self._anniversaries.items():
            if not key:
                continue

            # 判断 Key 类型
            is_lunar = key.startswith('n')
            clean_key = key[1:] if is_lunar else key

            try:
                parts = [int(p) for p in clean_key.split('-')]
            except ValueError:
                continue

            if is_lunar:
                # 农历匹配
                if len(parts) == 3:  # nYYYY-MM-DD
                    if parts[0] == l_year and parts[1] == l_month and parts[2] == l_day:
                        anniversaries.append(value)
                elif len(parts) == 2:  # nMM-DD
                    if parts[0] == l_month and parts[1] == l_day:
                        anniversaries.append(value)
            else:
                # 公历匹配
                if len(parts) == 3:  # YYYY-MM-DD
                    if parts[0] == g_year and parts[1] == g_month and parts[2] == g_day:
                        anniversaries.append(value)
                elif len(parts) == 2:  # MM-DD
                    if parts[0] == g_month and parts[1] == g_day:
                        anniversaries.append(value)

        return anniversaries

    def get_future_anniversaries(
        self, date: datetime.datetime
    ) -> List[Dict[str, Any]]:
        today = date.date()
        items: List[Dict[str, Any]] = []

        # 获取今天的农历年份，用于计算每年重复的农历纪念日
        try:
            ld_today = LunarDate.fromSolarDate(today.year, today.month, today.day)
            current_lunar_year = ld_today.year
        except Exception:
            current_lunar_year = today.year  # Fallback

        for key, value in self._anniversaries.items():
            if not value:
                continue
            try:
                target_date = None

                # 处理农历配置 (以 'n' 开头)
                if key.startswith('n'):
                    clean_key = key[1:]
                    parts = [int(p) for p in clean_key.split('-')]

                    if len(parts) == 3:  # nYYYY-MM-DD (一次性)
                        l_year, l_month, l_day = parts
                        try:
                            target_date = LunarDate.toSolarDate(
                                l_year, l_month, l_day)
                            if target_date < today:
                                continue
                        except ValueError:
                            continue

                    elif len(parts) == 2:  # nMM-DD (每年)
                        l_month, l_day = parts
                        # 尝试今年的农历日期
                        try:
                            t1 = LunarDate.toSolarDate(
                                current_lunar_year, l_month, l_day)
                            if t1 >= today:
                                target_date = t1
                            else:
                                # 如果今年的已经过了，计算明年的
                                target_date = LunarDate.toSolarDate(
                                    current_lunar_year + 1, l_month, l_day)
                        except ValueError:
                            continue

                # 处理公历配置
                elif len(key) == 5 and key[2] == "-":  # MM-DD (每年)
                    month, day = key.split("-")
                    target_year = today.year
                    target_date = datetime.date(
                        target_year, int(month), int(day)
                    )
                    if target_date < today:
                        target_date = datetime.date(
                            target_year + 1, int(month), int(day)
                        )
                else:  # YYYY-MM-DD (一次性)
                    target_date = datetime_class.strptime(
                        key, "%Y-%m-%d").date()
                    if target_date < today:
                        continue

                if target_date:
                    items.append(
                        {
                            "name": value,
                            "date": target_date.strftime("%Y-%m-%d"),
                            "days_diff": (target_date - today).days,
                        }
                    )
            except Exception:
                continue
        items.sort(key=lambda x: x["days_diff"])
        return items

    def _find_holiday_range(
        self, date: datetime.datetime
    ) -> Tuple[datetime.datetime, datetime.datetime]:
        """查找连续假期的开始和结束日期。"""
        start = date
        end = date
        # 向前查找
        while self.is_holiday_status(start - timedelta(days=1)) != 0:
            start -= timedelta(days=1)
        # 向后查找
        while self.is_holiday_status(end + timedelta(days=1)) != 0:
            end += timedelta(days=1)
        return start, end

    def _find_surrounding_workdays(
        self, date: datetime.datetime, look_back: bool = True
    ) -> List[Dict[str, Any]]:
        """查找节假日周边连续的工作日（调休）。"""
        workdays = []
        current = date - \
            timedelta(days=1) if look_back else date + timedelta(days=1)
        step = -1 if look_back else 1

        while self.is_holiday_status(current) == 0:
            # 判断是否为调休（即本该是周末但变成了工作日）
            is_weekend = current.weekday() in (5, 6)
            # 记录工作日信息
            workdays.append({"date": current, "invert": is_weekend})
            current += timedelta(days=step)

        if look_back:
            workdays.reverse()
        return workdays

    def _format_holiday_info(
        self,
        today: datetime.datetime,
        start: datetime.datetime,
        end: datetime.datetime,
        before_workdays: List[Dict],
        after_workdays: List[Dict],
    ) -> str:
        """格式化节假日信息字符串。"""

        def format_workdays(workdays):
            res = ""
            for item in workdays:
                d = item["date"]
                res += " {}/{}".format(d.month, d.day)
                if item["invert"]:
                    res += "(串休日，周{})".format(d.weekday() + 1)
            return res

        before_str = format_workdays(before_workdays)
        after_str = format_workdays(after_workdays)

        # 计算各种天数
        total_days = (end - start).days + 1

        # 修正逻辑：直接用工作日列表长度来表示连续工作天数
        days_worked_before = len(before_workdays)
        days_worked_after = len(after_workdays)

        info = (
            "{}(周{})-{} 放假 共{}天\n据上一次休息{}天 {} \n据下一次休息{}天 {}".format(
                start.strftime("%m/%d"),
                start.weekday() + 1,
                end.strftime("%m/%d"),
                total_days,
                days_worked_before,
                before_str,
                days_worked_after,
                after_str,
            )
        )
        return info

    def get_holidays_from_disk(self) -> None:
        """从本地加载节假日数据。

        优先从 SQLite 数据库加载，如果数据库为空，再尝试从 JSON 文件加载。
        """
        loaded = False

        # 1. 优先尝试从数据库加载
        try:
            db_data = self.db.load()
            if db_data:
                self._holiday_json = db_data
                loaded = True
                _LOGGER.debug("从 SQLite 数据库加载数据成功")
        except Exception as e:
            _LOGGER.error("从 SQLite 数据库加载数据失败: %s", e)

        # 2. 如果数据库没有数据，尝试从 JSON 文件加载
        if not loaded:
            try:
                if os.path.exists(HOLIDAY_DATA_FILE):
                    with open(HOLIDAY_DATA_FILE, "r", encoding="utf-8") as f:
                        self._holiday_json = json.load(f)
                        loaded = True
                        _LOGGER.info("从 JSON 文件加载数据成功")
            except Exception as e:
                _LOGGER.error("加载本地 JSON 数据失败: %s", e)
                self._holiday_json = {}

    def get_holidays_from_server(self, days: int = 15) -> None:
        """从服务器获取节假日数据。

        Args:
            days: 缓存有效期天数。
        """
        os.makedirs(os.path.dirname(HOLIDAY_DATA_FILE), exist_ok=True)

        # 检查是否需要更新
        last_update_str = self._holiday_json.get("update_time", "2020-01-01")
        try:
            last_update = datetime_class.strptime(last_update_str, "%Y-%m-%d")
        except ValueError:
            last_update = datetime_class(2020, 1, 1)

        today = Holiday.today()
        # 将 timezone-aware 的 today 转换为 naive datetime 以便比较
        if today.tzinfo is not None:
            today_naive = today.replace(tzinfo=None)
        else:
            today_naive = today
        interval = (today_naive - last_update).days

        # 检查是否包含当前年份的数据，如果没有数据，即使时间没过期也应该更新
        current_year_str = str(today.year)
        has_data = (
            current_year_str in self._holiday_json
            and self._holiday_json[current_year_str]
        )

        _LOGGER.debug(
            "距上次更新 %s 天, 阈值 %s 天, 是否有当前年份数据: %s",
            interval,
            days,
            has_data,
        )

        if interval <= days and days != 0 and has_data:
            _LOGGER.debug("无需更新")
            return

        # 执行更新
        _LOGGER.info("开始更新节假日数据(强制刷新)...")
        new_data = self._holiday_json.copy()
        update_time_str = today.strftime("%Y-%m-%d")
        new_data["update_time"] = update_time_str

        # 用于收集全量数据以便存入数据库
        full_data_items: List[Dict[str, Any]] = []

        # 获取当前月及未来 5 个月的数据
        for i in range(6):
            # 计算年月
            y, m = self._get_year_month(today, i)

            y_str = str(y)
            if y_str not in new_data:
                new_data[y_str] = {}

            # 获取数据，并填充 simple dict 和 full list
            self._fetch_month_data(y, m, new_data[y_str], full_data_items)
            time.sleep(0.5)  # 礼貌延时，避免触发API频率限制

        # 保存数据
        try:
            # 1. 保存到 JSON (仅包含简略信息，保持兼容)
            with open(HOLIDAY_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(new_data, f, ensure_ascii=False, indent=2)

            # 2. 备份到 SQLite (包含全量信息)
            self.db.save_full(full_data_items, update_time_str)

            self._holiday_json = new_data
            _LOGGER.info("节假日数据更新完成 (JSON + SQLite)")
        except Exception as e:
            _LOGGER.error("保存数据失败: %s", e)

    def _get_year_month(
        self, start_date: datetime.datetime, offset_month: int
    ) -> Tuple[int, int]:
        """计算偏移后的年月"""
        m = start_date.month + offset_month
        y = start_date.year
        while m > 12:
            m -= 12
            y += 1
        return y, m

    def _fetch_month_data(
        self,
        year: int,
        month: int,
        year_dict: Dict[str, Any],
        full_data_list: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """获取指定月份数据并填充到字典中。

        Args:
            year: 年份
            month: 月份
            year_dict: 用于内存使用的字典 {day: full_item_dict}
            full_data_list: 用于数据库存储的全量数据列表
        """
        d = "{}{:0>2d}".format(year, month)
        params = {"d": d, "info": 1}

        try:
            resp = self.session.get(API_URL, params=params, timeout=10)
            if resp.status_code != 200:
                _LOGGER.warning("API请求失败: %s", resp.status_code)
                return

            data = resp.json()
            if d not in data:
                return

            for day_key, item in data[d].items():
                try:
                    if not isinstance(item, dict):
                        continue

                    # 1. 基础校验逻辑
                    t = int(item.get("type", 0))
                    w = item.get("week", item.get("week2", 0))
                    try:
                        w = int(w)
                    except (ValueError, TypeError):
                        w = 0

                    # 确保 item 中包含 day 字段 (数据库和内存都可能需要)
                    day_key_str = str(day_key)
                    day_int = int(
                        day_key_str[-2:]) if len(day_key_str) > 2 else int(day_key_str)
                    if "day" not in item:
                        item["day"] = "{}{:0>2d}{:0>2d}".format(
                            year, month, day_int
                        )

                    date_obj = datetime_class(year, month, day_int)
                    item.update(self.get_festival_info(date_obj))

                    # 只要是 休息日(1)、节假日(2) 或 调休上班日(周末且type=0)
                    if t in (1, 2) or (t == 0 and w in (6, 7)):
                        # 修改：存储完整对象，保持 JSON 和 数据库 一致
                        year_dict[day_key] = item

                    # 2. 收集全量数据 (数据库用)
                    if full_data_list is not None:
                        full_data_list.append(item)

                except Exception as e:
                    _LOGGER.debug("解析日期 %s 失败: %s", day_key, e)

        except Exception as e:
            _LOGGER.error("获取 %s 数据失败: %s", d, e)

    def get_day_detail(self, date: datetime.datetime) -> Dict[str, Any]:
        """获取某天的完整详细信息（农历、宜忌等）。"""
        if not self._holiday_json:
            self.get_holidays_from_server()

        day_key = date.strftime("%Y%m%d")

        y_str = str(date.year)
        m_d_key = "{:0>2d}{:0>2d}".format(date.month, date.day)

        detail: Dict[str, Any] = {}
        if y_str in self._holiday_json:
            if (
                isinstance(self._holiday_json[y_str], dict)
                and m_d_key in self._holiday_json[y_str]
            ):
                item = self._holiday_json[y_str][m_d_key]
                if isinstance(item, dict):
                    detail = dict(item)

        if not detail:
            detail = self.db.get_day_detail(day_key) or detail

        festival_info = self.get_festival_info(date)
        detail.update(festival_info)
        return detail

    def get_festival_info(self, date: datetime.datetime) -> Dict[str, Any]:
        solar = _festival_handle(_SOLAR_FESTIVAL, date.month, date.day)
        weekday_map = _build_weekday_festival(date.year)
        weekday_key = "{:0>2d}{:0>2d}".format(date.month, date.day)
        weekday = weekday_map.get(weekday_key, [])
        solar_all = solar + weekday

        lunar = LunarDate.fromSolarDate(date.year, date.month, date.day)
        lunar_festival = _festival_handle(
            _LUNAR_FESTIVAL, lunar.month, lunar.day)

        # 获取自定义纪念日
        anniversaries = self.get_anniversaries(date)

        combined = []
        # 将纪念日也加入到总节日列表中
        for name in solar_all + lunar_festival + anniversaries:
            if name not in combined:
                combined.append(name)

        return {
            "solar_festival": solar_all,
            "lunar_festival": lunar_festival,
            "anniversaries": anniversaries,
            "festival": combined,
        }

    def is_holiday_status(self, date: datetime.datetime) -> int:
        """获取某天的状态码。

        Returns:
            int: 0=工作日, 1=休息日/周末, 2=节假日
        """
        # 懒加载
        if not self._holiday_json:
            self.get_holidays_from_server()

        y_str = str(date.year)
        m_d_key = "{:0>2d}{:0>2d}".format(date.month, date.day)

        # 优先查表
        if y_str in self._holiday_json:
            if (
                isinstance(self._holiday_json[y_str], dict)
                and m_d_key in self._holiday_json[y_str]
            ):
                item = self._holiday_json[y_str][m_d_key]
                # 兼容处理：如果是字典，取type字段；如果是数字，直接返回
                if isinstance(item, dict):
                    return int(item.get("type", 0))
                return int(item)

        # 查不到则默认按星期判断
        if date.weekday() >= 5:  # 5=Sat, 6=Sun
            return 1
        return 0

    def is_holiday(self, date: datetime.datetime) -> str:
        """获取某天的状态描述文本。"""
        status = self.is_holiday_status(date)
        return self.STATUS_MAP.get(status, "未知")

    def is_holiday_today(self) -> str:
        """判断今天是否是节假日/休息日。"""
        return self.is_holiday(Holiday.today())

    def is_holiday_tomorrow(self) -> str:
        """判断明天是否是节假日/休息日。"""
        return self.is_holiday(Holiday.tomorrow())


if __name__ == "__main__":
    # 本地测试代码
    logging.basicConfig(level=logging.DEBUG)
    h = Holiday()

    # 强制更新数据（传入 days=0）
    # print("正在强制拉取最新数据...")
    # h.get_holidays_from_server(days=0)
    # print(h.get_day_detail(datetime.datetime.now()))
    # print("今天是否节假日:", h.is_holiday_today())
    # print("明天是否节假日:", h.is_holiday_tomorrow())
    # print("最近节假日信息:", h.nearest_holiday_info())
    # print("最近节假日信息:", h.get_nearest_holiday())

"""
八字排盘核心算法（纯Python实现）
支持阳历输入，精确计算节气、干支、十神、大运
"""

import math
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional

# 城市定位支持
try:
    from .city_location import city_to_longitude, get_coordinates, search_city
except ImportError:
    from city_location import city_to_longitude, get_coordinates, search_city

# ========== 基础数据 ==========
TIANGAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
DIZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# 天干五行
WUXING_GAN = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
    "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"
}

# 地支五行（本气）
WUXING_ZHI = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
    "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水"
}

# 阴阳
YINYANG = {
    "甲": "阳", "乙": "阴", "丙": "阳", "丁": "阴", "戊": "阳",
    "己": "阴", "庚": "阳", "辛": "阴", "壬": "阳", "癸": "阴",
    "子": "阳", "丑": "阴", "寅": "阳", "卯": "阴", "辰": "阳",
    "巳": "阴", "午": "阳", "未": "阴", "申": "阳", "酉": "阴",
    "戌": "阳", "亥": "阴"
}

# 地支藏干
ZHI_CANGGAN = {
    "子": ["癸"],
    "丑": ["己", "癸", "辛"],
    "寅": ["甲", "丙", "戊"],
    "卯": ["乙"],
    "辰": ["戊", "乙", "癸"],
    "巳": ["丙", "庚", "戊"],
    "午": ["丁", "己"],
    "未": ["己", "丁", "乙"],
    "申": ["庚", "壬", "戊"],
    "酉": ["辛"],
    "戌": ["戊", "辛", "丁"],
    "亥": ["壬", "甲"]
}

# 节气名（按顺序）
JIEQI_NAMES = [
    "小寒", "大寒", "立春", "雨水", "惊蛰", "春分",
    "清明", "谷雨", "立夏", "小满", "芒种", "夏至",
    "小暑", "大暑", "立秋", "处暑", "白露", "秋分",
    "寒露", "霜降", "立冬", "小雪", "大雪", "冬至"
]

# 节令（月柱分界点）：立春、惊蛰、清明、立夏、芒种、小暑、立秋、白露、寒露、立冬、大雪、小寒
JIELING_NAMES = ["立春", "惊蛰", "清明", "立夏", "芒种", "小暑",
                 "立秋", "白露", "寒露", "立冬", "大雪", "小寒"]

# 节气近似日期（月,日）- 用于初始猜测
JIEQI_APPROX = {
    285: (1, 6),   # 小寒
    300: (1, 20),  # 大寒
    315: (2, 4),   # 立春
    330: (2, 19),  # 雨水
    345: (3, 6),   # 惊蛰
    0:   (3, 21),  # 春分
    15:  (4, 5),   # 清明
    30:  (4, 20),  # 谷雨
    45:  (5, 6),   # 立夏
    60:  (5, 21),  # 小满
    75:  (6, 6),   # 芒种
    90:  (6, 21),  # 夏至
    105: (7, 7),   # 小暑
    120: (7, 23),  # 大暑
    135: (8, 8),   # 立秋
    150: (8, 23),  # 处暑
    165: (9, 8),   # 白露
    180: (9, 23),  # 秋分
    195: (10, 8),  # 寒露
    210: (10, 24), # 霜降
    225: (11, 8),  # 立冬
    240: (11, 22), # 小雪
    255: (12, 7),  # 大雪
    270: (12, 22), # 冬至
}

# 十神名称映射
SHISHEN_MAP = {
    ("same", "same"): "比肩",      # 同我同阴阳
    ("same", "diff"): "劫财",      # 同我异阴阳
    ("produce", "diff"): "食神",   # 我生异阴阳
    ("produce", "same"): "伤官",   # 我生同阴阳
    ("overcome", "diff"): "正财",  # 我克异阴阳
    ("overcome", "same"): "偏财",  # 我克同阴阳
    ("overcome_by", "same"): "正官",  # 克我同阴阳
    ("overcome_by", "diff"): "七杀",  # 克我异阴阳
    ("produce_by", "same"): "正印",   # 生我同阴阳
    ("produce_by", "diff"): "偏印",   # 生我异阴阳
}

# 五行生克关系
WUXING_SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
WUXING_KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}


class BaziCore:
    """八字排盘核心类"""

    def __init__(self, city: str = None, longitude: float = 116.4, use_beijing_time: bool = True):
        """
        Args:
            city: 出生地城市名称（如"北京"、"上海"），优先使用城市解析经度
            longitude: 出生地经度（东经为正，西经为负），默认北京经度116.4°
                       当city参数提供时，此参数会被覆盖
            use_beijing_time: 是否使用北京时间（UTC+8）。True=北京时间，False=UTC
        """
        # 如果提供了城市名称，优先解析城市经度
        if city:
            city_longitude = city_to_longitude(city)
            if city_longitude is not None:
                self.longitude = city_longitude
                self.city = city
            else:
                self.longitude = longitude
                self.city = None
        else:
            self.longitude = longitude
            self.city = None
        
        self.use_beijing_time = use_beijing_time
        self.tz_offset = 8 if use_beijing_time else 0
        # 基准日：2024年1月1日 = 甲子日（经万年历验证确认）
        self.base_jiazi = datetime(2024, 1, 1)

    # ========== 天文计算 ==========

    def _to_utc(self, dt: datetime) -> datetime:
        """将当地时间转为UTC"""
        return dt - timedelta(hours=self.tz_offset)

    def _from_utc(self, dt: datetime) -> datetime:
        """将UTC转为当地时间"""
        return dt + timedelta(hours=self.tz_offset)

    def _julian_day(self, dt: datetime) -> float:
        """
        计算儒略日（对UTC时间）
        """
        year, month = dt.year, dt.month
        day = dt.day + dt.hour / 24.0 + dt.minute / 1440.0 + dt.second / 86400.0

        if month <= 2:
            year -= 1
            month += 12

        A = int(year / 100)
        B = 2 - A + int(A / 4)

        jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + B - 1524.5
        return jd

    def _jd_to_datetime(self, jd: float) -> datetime:
        """儒略日转UTC datetime"""
        jd += 0.5
        Z = int(jd)
        F = jd - Z

        if Z < 2299161:
            A = Z
        else:
            alpha = int((Z - 1867216.25) / 36524.25)
            A = Z + 1 + alpha - int(alpha / 4)

        B = A + 1524
        C = int((B - 122.1) / 365.25)
        D = int(365.25 * C)
        E = int((B - D) / 30.6001)

        day = B - D - int(30.6001 * E) + F

        if E < 14:
            month = E - 1
        else:
            month = E - 13

        if month > 2:
            year = C - 4716
        else:
            year = C - 4715

        d = int(day)
        hour_frac = (day - d) * 24
        hour = int(hour_frac)
        minute_frac = (hour_frac - hour) * 60
        minute = int(minute_frac)
        second = int((minute_frac - minute) * 60)

        return datetime(year, month, d, hour, minute, second)

    def _sun_longitude(self, jd: float) -> float:
        """
        计算太阳视黄经（度），对UTC儒略日
        精度约0.01度，对应节气时间误差约10-20分钟
        """
        T = (jd - 2451545.0) / 36525.0

        # 几何平黄经
        L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T * T

        # 平近点角
        M = 357.52911 + 35999.05029 * T - 0.0001537 * T * T

        # 离心率
        e = 0.016708634 - 0.000042037 * T - 0.0000001267 * T * T

        # 中心差
        M_rad = math.radians(M)
        C = (1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(M_rad)
        C += (0.019993 - 0.000101 * T) * math.sin(2 * M_rad)
        C += 0.000289 * math.sin(3 * M_rad)

        # 真黄经
        sun_lon = L0 + C

        # 章动修正（简化）
        omega = 125.04 - 1934.136 * T
        sun_lon -= 0.00569 + 0.00478 * math.sin(math.radians(omega))

        # 光行差
        sun_lon -= 20.4898 / 3600.0

        return sun_lon % 360

    def _equation_of_time(self, jd: float) -> float:
        """
        计算均时差（Equation of Time，单位：分钟）
        均时差 = 真太阳时 - 平太阳时
        """
        T = (jd - 2451545.0) / 36525.0

        # 平近点角
        M = 357.52911 + 35999.05029 * T - 0.0001537 * T * T
        M_rad = math.radians(M)

        # 太阳平黄经
        L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T * T

        # 离心率
        e = 0.016708634 - 0.000042037 * T - 0.0000001267 * T * T

        # 中心差
        C = (1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(M_rad)
        C += (0.019993 - 0.000101 * T) * math.sin(2 * M_rad)
        C += 0.000289 * math.sin(3 * M_rad)

        # 太阳真黄经
        sun_lon = L0 + C

        # 均时差计算（简化公式）
        eot = -7.65 * math.sin(math.radians(M))
        eot += 9.87 * math.sin(math.radians(2 * (sun_lon - 280.46646)))

        return eot  # 单位：分钟

    def _true_solar_time(self, dt: datetime) -> datetime:
        """
        计算真太阳时
        真太阳时 = 平太阳时 + 经度修正 + 均时差
        经度修正：(当地经度 - 120°) × 4分钟
        """
        # 转UTC
        dt_utc = self._to_utc(dt)
        jd = self._julian_day(dt_utc)

        # 均时差（分钟）
        eot = self._equation_of_time(jd)

        # 经度修正（分钟）
        # 北京时间基准是东经120°
        lon_correction = (self.longitude - 120.0) * 4.0

        # 总修正（分钟）
        total_correction = eot + lon_correction

        # 应用修正
        dt_true = dt + timedelta(minutes=total_correction)

        return dt_true

    def _find_jieqi(self, year: int, target_lon: int) -> datetime:
        """
        查找某年太阳黄经达到target_lon的当地时间（北京时间）
        使用迭代法精确计算
        """
        # 获取近似日期
        month, day = JIEQI_APPROX.get(target_lon, (1, 1))

        # 处理冬至可能在12月22日或次年1月初的情况
        dt_approx = datetime(year, month, day, 12, 0)
        dt_utc = self._to_utc(dt_approx)
        jd = self._julian_day(dt_utc)

        # 牛顿迭代法
        for _ in range(30):
            lon = self._sun_longitude(jd)
            diff = target_lon - lon

            # 处理360度环绕
            while diff > 180:
                diff -= 360
            while diff < -180:
                diff += 360

            if abs(diff) < 1e-6:
                break

            # 太阳平均速度 ~ 0.985647度/天，考虑离心率微调
            speed = 0.985647  # 度/天
            jd += diff / speed

        dt_result_utc = self._jd_to_datetime(jd)
        return self._from_utc(dt_result_utc)

    def get_all_jieqi(self, year: int) -> Dict[str, datetime]:
        """获取某年全部24节气的时间（当地时间）"""
        result = {}
        lons = [285, 300, 315, 330, 345, 0, 15, 30, 45, 60, 75, 90,
                105, 120, 135, 150, 165, 180, 195, 210, 225, 240, 255, 270]

        for i, lon in enumerate(lons):
            dt = self._find_jieqi(year, lon)
            result[JIEQI_NAMES[i]] = dt

        return result

    # ========== 干支计算 ==========

    def get_year_ganzhi(self, dt: datetime) -> Tuple[str, str]:
        """
        计算年柱（以立春为年分界）
        立春前出生，年柱算上一年
        """
        year = dt.year

        # 获取当年立春
        lichun = self._find_jieqi(year, 315)

        if dt < lichun:
            # 立春前，算上一年
            year -= 1

        # 年干 = (year - 4) % 10
        # 年支 = (year - 4) % 12
        gan_idx = (year - 4) % 10
        zhi_idx = (year - 4) % 12

        return TIANGAN[gan_idx], DIZHI[zhi_idx]

    def get_month_ganzhi(self, dt: datetime, year_gan: str) -> Tuple[str, str]:
        """
        计算月柱（以节令为月分界）
        十二节令：立春、惊蛰、清明、立夏、芒种、小暑、立秋、白露、寒露、立冬、大雪、小寒
        """
        # 节令对应的太阳黄经
        jieling_lons = [315, 345, 15, 45, 75, 105, 135, 165, 195, 225, 255, 285]
        jieling_months = ["寅", "卯", "辰", "巳", "午", "未",
                          "申", "酉", "戌", "亥", "子", "丑"]

        year = dt.year

        # 确定八字年：以立春为界
        lichun = self._find_jieqi(year, 315)
        if dt >= lichun:
            # 在当年立春之后，属于该八字年
            ref_year = year
        else:
            # 在当年立春之前，属于上一年
            ref_year = year - 1

        # 构建该八字年（ref_year立春 ~ ref_year+1立春）的完整节令序列
        jieqi_times = []
        lichun_ref = self._find_jieqi(ref_year, 315)
        for lon in jieling_lons:
            # 先用ref_year查找
            t = self._find_jieqi(ref_year, lon)
            # 如果找到的节令在ref_year立春之前（如小寒在1月），
            # 说明实际属于下一公历年的同一节令
            if t < lichun_ref:
                t = self._find_jieqi(ref_year + 1, lon)
            jieqi_times.append(t)

        # 倒序查找出生时间所在的节令区间
        month_zhi = "丑"  # 兜底：立春前算上一年的丑月
        for i in range(len(jieqi_times) - 1, -1, -1):
            if dt >= jieqi_times[i]:
                month_zhi = jieling_months[i]
                break

        # 月干由年干决定（五虎遁）
        # 甲己之年丙作首, 乙庚之岁戊为头,
        # 丙辛之岁寻庚起, 丁壬壬位顺行流,
        # 戊癸之年何方发, 甲寅之上好追求.
        wuhu = {
            "甲": "丙", "己": "丙",
            "乙": "戊", "庚": "戊",
            "丙": "庚", "辛": "庚",
            "丁": "壬", "壬": "壬",
            "戊": "甲", "癸": "甲"
        }

        start_gan = wuhu[year_gan]
        start_idx = TIANGAN.index(start_gan)
        zhi_idx = DIZHI.index(month_zhi)

        # 正月起寅，所以寅月的天干就是start_gan，然后顺推
        # 地支偏移（寅=0, 卯=1, ..., 丑=11）
        offset = (zhi_idx - 2) % 12
        gan_idx = (start_idx + offset) % 10

        return TIANGAN[gan_idx], month_zhi

    def get_day_ganzhi(self, dt: datetime) -> Tuple[str, str]:
        """
        计算日柱
        注意：子时（23:00-01:00）日柱的计算
        传统上23:00起算第二天
        """
        # 调整日期：23点及以后算第二天
        adjusted_dt = dt
        if dt.hour >= 23:
            adjusted_dt = dt + timedelta(days=1)

        # 计算与基准日的天数差
        base = datetime(self.base_jiazi.year, self.base_jiazi.month, self.base_jiazi.day)
        target = datetime(adjusted_dt.year, adjusted_dt.month, adjusted_dt.day)
        days_diff = (target - base).days

        gan_idx = days_diff % 10
        zhi_idx = days_diff % 12

        # 处理负数
        if gan_idx < 0:
            gan_idx += 10
        if zhi_idx < 0:
            zhi_idx += 12

        return TIANGAN[gan_idx], DIZHI[zhi_idx]

    def get_hour_ganzhi(self, dt: datetime, day_gan: str) -> Tuple[str, str]:
        """
        计算时柱
        地支由时辰确定，天干由日干遁出（五鼠遁）
        """
        hour = dt.hour

        # 时辰地支
        # 23-1 子时, 1-3 丑时, ...
        if hour >= 23 or hour < 1:
            zhi = "子"
        elif hour < 3:
            zhi = "丑"
        elif hour < 5:
            zhi = "寅"
        elif hour < 7:
            zhi = "卯"
        elif hour < 9:
            zhi = "辰"
        elif hour < 11:
            zhi = "巳"
        elif hour < 13:
            zhi = "午"
        elif hour < 15:
            zhi = "未"
        elif hour < 17:
            zhi = "申"
        elif hour < 19:
            zhi = "酉"
        elif hour < 21:
            zhi = "戌"
        else:
            zhi = "亥"

        # 五鼠遁
        # 甲己日起甲子时, 乙庚日起丙子时,
        # 丙辛日起戊子时, 丁壬日起庚子时, 戊癸日起壬子时
        wushu = {
            "甲": "甲", "己": "甲",
            "乙": "丙", "庚": "丙",
            "丙": "戊", "辛": "戊",
            "丁": "庚", "壬": "庚",
            "戊": "壬", "癸": "壬"
        }

        start_gan = wushu[day_gan]
        start_idx = TIANGAN.index(start_gan)
        zhi_idx = DIZHI.index(zhi)

        gan_idx = (start_idx + zhi_idx) % 10

        return TIANGAN[gan_idx], zhi

    # ========== 十神计算 ==========

    def get_shishen(self, day_gan: str, target: str) -> str:
        """
        计算十神
        day_gan: 日干
        target: 目标天干或地支（本气）
        """
        if target in WUXING_GAN:
            target_wx = WUXING_GAN[target]
            target_yy = YINYANG[target]
        elif target in WUXING_ZHI:
            # 用地支本气
            canggan = ZHI_CANGGAN[target]
            target = canggan[0]  # 本气
            target_wx = WUXING_GAN[target]
            target_yy = YINYANG[target]
        else:
            return "未知"

        day_wx = WUXING_GAN[day_gan]
        day_yy = YINYANG[day_gan]

        # 确定关系
        if WUXING_SHENG.get(day_wx) == target_wx:
            # 我生
            relation = "produce"
        elif WUXING_SHENG.get(target_wx) == day_wx:
            # 生我
            relation = "produce_by"
        elif WUXING_KE.get(day_wx) == target_wx:
            # 我克
            relation = "overcome"
        elif WUXING_KE.get(target_wx) == day_wx:
            # 克我
            relation = "overcome_by"
        else:
            # 同我
            relation = "same"

        # 阴阳关系
        yy_relation = "same" if day_yy == target_yy else "diff"

        return SHISHEN_MAP.get((relation, yy_relation), "未知")

    def get_shishen_for_ganzhi(self, day_gan: str, gan: str, zhi: str) -> Dict:
        """获取某柱的十神信息"""
        result = {
            "天干十神": self.get_shishen(day_gan, gan),
            "地支十神": self.get_shishen(day_gan, zhi),
            "地支藏干": []
        }
        for cg in ZHI_CANGGAN[zhi]:
            result["地支藏干"].append({
                "藏干": cg,
                "十神": self.get_shishen(day_gan, cg)
            })
        return result

    # ========== 大运计算 ==========

    def calc_dayun(self, year_gz: Tuple[str, str], month_gz: Tuple[str, str],
                   birth_dt: datetime, gender: str, num_yun: int = 8) -> List[Dict]:
        """
        计算大运
        Args:
            year_gz: 年柱
            month_gz: 月柱（起运基准）
            birth_dt: 出生时间
            gender: '男' or '女'
            num_yun: 返回几个大运（默认8个）
        """
        year_gan, year_zhi = year_gz
        month_gan, month_zhi = month_gz

        # 判断顺逆
        # 阳男阴女顺行，阴男阳女逆行
        year_yy = YINYANG[year_gan]

        if (year_yy == "阳" and gender == "男") or (year_yy == "阴" and gender == "女"):
            direction = "顺"  # 顺排
        else:
            direction = "逆"  # 逆排

        # 计算起运岁数
        # 顺行：从出生时刻到下一个节令的时间
        # 逆行：从出生时刻到上一个节令的时间
        # 三天折合一岁，一天折合四个月

        # 节令（用于大运的"节"）
        jieling_lons = [315, 345, 15, 45, 75, 105, 135, 165, 195, 225, 255, 285]

        if direction == "顺":
            # 找出生后的第一个节令
            nearest_jieqi = None
            for lon in jieling_lons:
                # 优先当年，如果当年已过则从下一年开始
                for y in [birth_dt.year, birth_dt.year + 1]:
                    try:
                        jq = self._find_jieqi(y, lon)
                        if jq > birth_dt:
                            if nearest_jieqi is None or jq < nearest_jieqi:
                                nearest_jieqi = jq
                            break
                    except:
                        continue
        else:
            # 找出生前的最后一个节令
            nearest_jieqi = None
            for lon in reversed(jieling_lons):
                for y in [birth_dt.year, birth_dt.year - 1]:
                    try:
                        jq = self._find_jieqi(y, lon)
                        if jq <= birth_dt:
                            if nearest_jieqi is None or jq > nearest_jieqi:
                                nearest_jieqi = jq
                            break
                    except:
                        continue

        if nearest_jieqi is None:
            raise ValueError("无法计算起运岁数：找不到对应的节令")

        # 计算时间差
        delta = abs(nearest_jieqi - birth_dt)
        total_hours = delta.total_seconds() / 3600

        # 三天 = 72小时 = 1岁
        # 所以 total_hours / 72 = 起运岁数
        qiyun_age = total_hours / 72.0

        # 生成大运
        dayun_list = []

        month_gan_idx = TIANGAN.index(month_gan)
        month_zhi_idx = DIZHI.index(month_zhi)

        for i in range(num_yun):
            if direction == "顺":
                new_gan_idx = (month_gan_idx + i + 1) % 10
                new_zhi_idx = (month_zhi_idx + i + 1) % 12
            else:
                new_gan_idx = (month_gan_idx - i - 1) % 10
                new_zhi_idx = (month_zhi_idx - i - 1) % 12

            start_age = qiyun_age + i * 10
            end_age = start_age + 10

            dayun_list.append({
                "大运": TIANGAN[new_gan_idx] + DIZHI[new_zhi_idx],
                "起运年龄": round(start_age, 2),
                "止运年龄": round(end_age, 2),
                "起运年份": birth_dt.year + int(start_age),
                "干支": (TIANGAN[new_gan_idx], DIZHI[new_zhi_idx])
            })

        return {
            "起运岁数": round(qiyun_age, 2),
            "顺逆": direction,
            "大运列表": dayun_list
        }

    # ========== 主排盘函数 ==========

    def solar_to_bazi(self, year: int, month: int, day: int,
                      hour: int, minute: int, gender: str) -> Dict:
        """
        根据阳历出生时间排八字
        Args:
            year, month, day: 阳历日期
            hour, minute: 出生时间（24小时制，当地时间/北京时间）
            gender: '男' or '女'
        """
        birth_dt = datetime(year, month, day, hour, minute)

        # 计算真太阳时（用于时柱）
        birth_dt_true = self._true_solar_time(birth_dt)

        # 四柱
        year_gan, year_zhi = self.get_year_ganzhi(birth_dt)
        month_gan, month_zhi = self.get_month_ganzhi(birth_dt, year_gan)
        day_gan, day_zhi = self.get_day_ganzhi(birth_dt)
        hour_gan, hour_zhi = self.get_hour_ganzhi(birth_dt_true, day_gan)  # 使用真太阳时

        # 十神
        shishen = {
            "年柱": self.get_shishen_for_ganzhi(day_gan, year_gan, year_zhi),
            "月柱": self.get_shishen_for_ganzhi(day_gan, month_gan, month_zhi),
            "日柱": self.get_shishen_for_ganzhi(day_gan, day_gan, day_zhi),
            "时柱": self.get_shishen_for_ganzhi(day_gan, hour_gan, hour_zhi)
        }

        # 大运
        dayun = self.calc_dayun(
            (year_gan, year_zhi),
            (month_gan, month_zhi),
            birth_dt, gender
        )

        # 节气信息
        jieqi_info = self.get_all_jieqi(year)
        lichun = jieqi_info.get("立春")

        # 由月支反推当前节令（月柱计算已确保正确）
        zhu_to_jieling = {
            "寅": "立春", "卯": "惊蛰", "辰": "清明", "巳": "立夏",
            "午": "芒种", "未": "小暑", "申": "立秋", "酉": "白露",
            "戌": "寒露", "亥": "立冬", "子": "大雪", "丑": "小寒"
        }
        current_jieling = zhu_to_jieling.get(month_zhi)

        # 神煞分析
        all_zhi = [year_zhi, month_zhi, day_zhi, hour_zhi]
        shensha = ShenSha.analyze_all(day_gan, day_zhi, all_zhi)

        # 自坐分析
        zizuo = ZizuoAnalysis.analyze(day_gan, day_zhi)

        # 副星/杂气分析
        fuxing = self._analyze_fuxing(day_gan, year_zhi, month_zhi, day_zhi, hour_zhi)

        return {
            "出生时间": birth_dt.strftime("%Y-%m-%d %H:%M"),
            "真太阳时": birth_dt_true.strftime("%Y-%m-%d %H:%M"),
            "出生地": self.city if self.city else f"{self.longitude}°E",
            "出生地经度": f"{self.longitude}°E" if self.longitude > 0 else f"{abs(self.longitude)}°W",
            "性别": gender,
            "年柱": year_gan + year_zhi,
            "月柱": month_gan + month_zhi,
            "日柱": day_gan + day_zhi,
            "时柱": hour_gan + hour_zhi,
            "四柱": {
                "年柱": {"干": year_gan, "支": year_zhi},
                "月柱": {"干": month_gan, "支": month_zhi},
                "日柱": {"干": day_gan, "支": day_zhi},
                "时柱": {"干": hour_gan, "支": hour_zhi}
            },
            "日干": day_gan,
            "十神": shishen,
            "大运": dayun,
            "节气信息": {
                "当年立春": lichun.strftime("%Y-%m-%d %H:%M") if lichun else None,
                "当前节令": current_jieling
            },
            "神煞": shensha,
            "自坐": zizuo,
            "副星": fuxing
        }

    def _analyze_fuxing(self, day_gan: str, year_zhi: str, month_zhi: str, 
                        day_zhi: str, hour_zhi: str) -> dict:
        """分析副星/杂气"""
        result = {}
        
        # 天德贵人
        tiande = {"丁": "亥", "丙": "寅", "乙": "卯", "甲": "寅",
                  "戊": "申", "己": "申", "庚": "亥", "辛": "巳",
                  "壬": "亥", "癸": "巳"}
        if day_gan in tiande:
            if tiande[day_gan] in [year_zhi, month_zhi, day_zhi, hour_zhi]:
                result["天德贵人"] = tiande[day_gan]
        
        # 月德贵人
        yuede = {"丙": "甲", "丁": "乙", "戊": "丙", "己": "丁",
                 "庚": "戊", "辛": "己", "壬": "庚", "癸": "辛",
                 "甲": "壬", "乙": "癸"}
        if day_gan in yuede:
            moon_gan = yuede[day_gan]
            # 检查月干是否为月德
            result["月德贵人"] = moon_gan
        
        # 魁罡
        kuigang = ["庚辰", "庚戌", "壬辰", "戊戌"]
        if day_gan + day_zhi in kuigang:
            result["魁罡"] = True
        
        # 孤辰寡宿
        guchen = {"寅": "巳", "卯": "午", "辰": "未", "巳": "申",
                  "午": "酉", "未": "戌", "申": "亥", "酉": "子",
                  "戌": "丑", "亥": "寅", "子": "卯", "丑": "辰"}
        guaxiu = {"寅": "亥", "卯": "子", "辰": "丑", "巳": "寅",
                  "午": "卯", "未": "辰", "申": "巳", "酉": "午",
                  "戌": "未", "亥": "申", "子": "酉", "丑": "戌"}
        if day_zhi in guchen:
            result["孤辰"] = guchen[day_zhi]
        if day_zhi in guaxiu:
            result["寡宿"] = guaxiu[day_zhi]
        
        return result

    def format_output(self, result: Dict) -> str:
        """格式化输出八字排盘结果"""
        lines = []
        lines.append("=" * 50)
        lines.append(f"八字排盘结果")
        lines.append("=" * 50)
        lines.append(f"出生时间: {result['出生时间']}  性别: {result['性别']}")
        if "真太阳时" in result:
            lines.append(f"出生地: {result['出生地']}")
            lines.append(f"真太阳时: {result['真太阳时']}")
        lines.append("")

        # 四柱
        lines.append("【四柱】")
        sizhu = result["四柱"]
        lines.append(f"  年柱: {sizhu['年柱']['干']}{sizhu['年柱']['支']}")
        lines.append(f"  月柱: {sizhu['月柱']['干']}{sizhu['月柱']['支']}")
        lines.append(f"  日柱: {sizhu['日柱']['干']}{sizhu['日柱']['支']}  (日主: {result['日干']})")
        lines.append(f"  时柱: {sizhu['时柱']['干']}{sizhu['时柱']['支']}")
        lines.append("")

        # 十神
        lines.append("【十神分析】")
        for zhu_name, zhu_info in result["十神"].items():
            cg_info = ", ".join([f"{c['藏干']}({c['十神']})" for c in zhu_info["地支藏干"]])
            lines.append(f"  {zhu_name}: 天干{zhu_info['天干十神']} | 地支{zhu_info['地支十神']} | 藏干[{cg_info}]")
        lines.append("")

        # 大运
        dayun = result["大运"]
        lines.append(f"【大运】起运岁数: {dayun['起运岁数']}岁  方向: {dayun['顺逆']}行")
        for dy in dayun["大运列表"][:6]:
            lines.append(f"  {dy['大运']}: {dy['起运年龄']}岁 ~ {dy['止运年龄']}岁 (约{dy['起运年份']}年)")
        lines.append("")

        # 节气
        jq = result["节气信息"]
        lines.append(f"【节气】当年立春: {jq['当年立春']}  出生时节令: {jq['当前节令']}")
        lines.append("=" * 50)

        return "\n".join(lines)

# ========== 神煞系统 ==========

# 天乙贵人（最尊贵的吉神）
TIANYI_GUIREN = {
    "甲": ["丑", "未"],
    "乙": ["子", "申"],
    "丙": ["子", "申"],
    "丁": ["酉", "亥"],
    "戊": ["丑", "未"],
    "己": ["丑", "未"],
    "庚": ["寅", "午"],
    "辛": ["寅", "午"],
    "壬": ["卯", "巳"],
    "癸": ["卯", "巳"]
}

# 华盖（艺术、宗教、孤独）
HUAGAI = {
    "子": ["辰"],
    "丑": ["辰"],
    "寅": ["戌"],
    "卯": ["戌"],
    "辰": ["丑", "辰", "未"],
    "巳": ["丑", "辰", "未"],
    "午": ["戌"],
    "未": ["丑", "辰", "未"],
    "申": ["丑", "辰", "未"],
    "酉": ["戌"],
    "戌": ["戌"],
    "亥": ["辰"]
}

# 文昌（学业、才华）
WENCHANG = {
    "甲": ["巳"],
    "乙": ["午"],
    "丙": ["申"],
    "丁": ["酉"],
    "戊": ["申"],
    "己": ["酉"],
    "庚": ["亥"],
    "辛": ["子"],
    "壬": ["寅"],
    "癸": ["卯"]
}

# 驿马（走动、迁移）
YIMA = {
    "申": ["寅"],
    "子": ["申"],
    "辰": ["子"],
    "寅": ["申"],
    "午": ["寅"],
    "戌": ["午"],
    "亥": ["巳"],
    "卯": ["亥"],
    "未": ["卯"],
    "巳": ["亥"],
    "酉": ["巳"],
    "丑": ["酉"]
}

# 桃花/咸池（感情、社交）
TAOHUA = {
    "申子辰": ["酉"],
    "亥卯未": ["子"],
    "寅午戌": ["卯"],
    "巳酉丑": ["午"]
}

# 将星（权威、领导力）
JIANGXING = {
    "寅": ["午"],
    "午": ["寅"],
    "戌": ["午"],
    "亥": ["卯"],
    "卯": ["亥"],
    "未": ["卯"],
    "申": ["子"],
    "子": ["申"],
    "辰": ["子"],
    "巳": ["酉"],
    "酉": ["巳"],
    "丑": ["酉"]
}


class ShenSha:
    """神煞分析类"""
    
    @staticmethod
    def get_tianyi(day_gan: str, all_zhi: list) -> list:
        """获取天乙贵人"""
        result = []
        if day_gan in TIANYI_GUIREN:
            for zhi in TIANYI_GUIREN[day_gan]:
                if zhi in all_zhi:
                    result.append(f"天乙贵人({zhi})")
        return result
    
    @staticmethod
    def get_huagai(day_zhi: str) -> list:
        """获取华盖"""
        result = []
        if day_zhi in HUAGAI:
            for zhi in HUAGAI[day_zhi]:
                result.append(f"华盖({zhi})")
        return result
    
    @staticmethod
    def get_wenchang(day_gan: str) -> list:
        """获取文昌"""
        result = []
        if day_gan in WENCHANG:
            for zhi in WENCHANG[day_gan]:
                result.append(f"文昌({zhi})")
        return result
    
    @staticmethod
    def get_yima(day_zhi: str) -> list:
        """获取驿马"""
        result = []
        if day_zhi in YIMA:
            for zhi in YIMA[day_zhi]:
                result.append(f"驿马({zhi})")
        return result
    
    @staticmethod
    def get_taohua(day_zhi: str, all_zhi: list) -> list:
        """获取桃花"""
        result = []
        for group, taohua_zhi in TAOHUA.items():
            if day_zhi in group:
                for zhi in taohua_zhi:
                    if zhi in all_zhi:
                        result.append(f"桃花({zhi})")
        return result
    
    @staticmethod
    def get_jiangxing(day_zhi: str) -> list:
        """获取将星"""
        result = []
        if day_zhi in JIANGXING:
            for zhi in JIANGXING[day_zhi]:
                result.append(f"将星({zhi})")
        return result
    
    @staticmethod
    def analyze_all(day_gan: str, day_zhi: str, all_zhi: list) -> dict:
        """分析所有神煞"""
        return {
            "天乙贵人": ShenSha.get_tianyi(day_gan, all_zhi),
            "华盖": ShenSha.get_huagai(day_zhi),
            "文昌": ShenSha.get_wenchang(day_gan),
            "驿马": ShenSha.get_yima(day_zhi),
            "桃花": ShenSha.get_taohua(day_zhi, all_zhi),
            "将星": ShenSha.get_jiangxing(day_zhi)
        }


# ========== 自坐分析 ==========

# 日主与地支的关系
RIZHU_RELATION = {
    # 日主在地支的状态
    "长生": ["甲亥", "丙寅", "戊寅", "庚辰", "壬申", "癸卯"],
    "沐浴": ["甲子", "丁卯", "己卯", "辛巳", "癸酉", "甲辰"],
    "冠带": ["甲寅", "戊辰", "庚午", "壬戌", "乙丑", "丁未"],
    "临官": ["甲辰", "丙辰", "戊辰", "庚辰", "壬辰", "乙巳", 
            "丁巳", "己巳", "辛巳", "癸巳", "甲午", "丙午", 
            "戊午", "庚午", "壬午", "乙未", "丁未", "己未", 
            "辛未", "癸未", "甲申", "丙申", "戊申", "庚申", 
            "壬申", "乙酉", "丁酉", "己酉", "辛酉", "癸酉",
            "甲戌", "丙戌", "戊戌", "庚戌", "壬戌", "乙亥",
            "丁亥", "己亥", "辛亥", "癸亥"],
    "帝旺": ["甲寅", "乙卯", "丙午", "丁巳", "戊午", "己未",
            "庚申", "辛酉", "壬子", "癸亥"],
    "衰": ["乙酉", "丁亥", "己丑", "辛卯", "癸巳", "乙未"],
    "病": ["丙子", "戊子", "庚子", "壬子", "丁卯", "己卯"],
    "死": ["甲戌", "丙戌", "戊戌", "庚戌", "乙丑", "丁丑"],
    "墓": ["乙未", "丁未", "己未", "辛未", "癸酉", "癸卯"],
    "绝": ["甲申", "丙申", "戊申", "庚申", "乙亥", "丁亥"],
    "胎": ["甲午", "丙午", "戊午", "庚午", "辛未", "癸未"],
    "养": ["甲辰", "丙辰", "戊辰", "庚辰", "壬辰", "乙巳"]
}

# 地支与日主的十神关系
ZHI_SHISHEN = {
    "子": {"壬": "劫财", "癸": "比肩"},
    "丑": {"己": "正财", "辛": "食神", "癸": "比肩"},
    "寅": {"甲": "比肩", "丙": "偏财", "戊": "正官"},
    "卯": {"乙": "劫财"},
    "辰": {"戊": "正官", "乙": "劫财", "癸": "比肩"},
    "巳": {"丙": "偏财", "戊": "正官", "庚": "七杀"},
    "午": {"丁": "正财", "己": "食神"},
    "未": {"己": "食神", "丁": "正财", "乙": "劫财"},
    "申": {"庚": "七杀", "壬": "正印", "戊": "正官"},
    "酉": {"辛": "伤官"},
    "戌": {"戊": "正官", "辛": "伤官", "丁": "正财"},
    "亥": {"壬": "正印", "甲": "比肩"}
}


class ZizuoAnalysis:
    """自坐分析类"""
    
    @staticmethod
    def get_status(day_gan: str, day_zhi: str) -> str:
        """获取日主在地支的状态（长生十二宫）"""
        ganzhi = day_gan + day_zhi
        for status, ganzhi_list in RIZHU_RELATION.items():
            if ganzhi in ganzhi_list:
                return status
        return "未知"
    
    @staticmethod
    def get_zizuo_shishen(day_gan: str, day_zhi: str) -> dict:
        """获取自坐十神"""
        result = []
        if day_zhi in ZHI_CANGGAN:
            for cg in ZHI_CANGGAN[day_zhi]:
                shishen = BaziCore().get_shishen(day_gan, cg)
                result.append({"藏干": cg, "十神": shishen})
        return result
    
    @staticmethod
    def analyze(day_gan: str, day_zhi: str) -> dict:
        """完整的自坐分析"""
        return {
            "日主": day_gan,
            "日支": day_zhi,
            "状态": ZizuoAnalysis.get_status(day_gan, day_zhi),
            "自坐十神": ZizuoAnalysis.get_zizuo_shishen(day_gan, day_zhi),
            "五行": WUXING_ZHI.get(day_zhi, "未知"),
            "阴阳": YINYANG.get(day_zhi, "未知")
        }


# ========== 流年计算 ==========

class LiunianAnalysis:
    """流年分析类"""
    
    @staticmethod
    def calc_liunian(bazi_result: dict, target_year: int) -> dict:
        """计算某一年的流年"""
        year_gan, year_zhi = BaziCore().get_year_ganzhi(datetime(target_year, 1, 1))
        
        # 获取当前大运
        dayun_list = bazi_result["大运"]["大运列表"]
        current_dayun = None
        for dy in dayun_list:
            if dy["起运年龄"] <= bazi_result.get("当前年龄", 0) < dy["止运年龄"]:
                current_dayun = dy
                break
        
        # 流年与四柱的关系分析
        relations = {}
        sizhu = bazi_result["四柱"]
        for zhu_name, zhu_info in sizhu.items():
            zhu_gan = zhu_info["干"]
            zhu_zhi = zhu_info["支"]
            
            # 天干关系
            gan_relation = BaziCore().get_shishen(zhu_gan, year_gan)
            
            # 地支关系
            zhi_relation = LiunianAnalysis._get_zhi_relation(zhu_zhi, year_zhi)
            
            relations[zhu_name] = {
                "流年天干关系": gan_relation,
                "流年地支关系": zhi_relation
            }
        
        return {
            "年份": target_year,
            "流年柱": year_gan + year_zhi,
            "天干": year_gan,
            "地支": year_zhi,
            "当前大运": current_dayun,
            "与四柱关系": relations
        }
    
    @staticmethod
    def _get_zhi_relation(zhi1: str, zhi2: str) -> str:
        """获取两个地支的关系"""
        # 地支六合
        liuhe = {"子丑": "六合", "寅亥": "六合", "卯戌": "六合", 
                 "辰酉": "六合", "巳申": "六合", "午未": "六合"}
        if zhi1 + zhi2 in liuhe:
            return liuhe[zhi1 + zhi2]
        if zhi2 + zhi1 in liuhe:
            return liuhe[zhi2 + zhi1]
        
        # 地支三合
        sanhe = {"申子辰": "三合水", "亥卯未": "三合木", 
                 "寅午戌": "三合火", "巳酉丑": "三合金"}
        for group, name in sanhe.items():
            if zhi1 in group and zhi2 in group:
                return f"{name}(半合)"
        
        # 地支相冲
        xiangchong = {"子午": "相冲", "丑未": "相冲", "寅申": "相冲",
                      "卯酉": "相冲", "辰戌": "相冲", "巳亥": "相冲"}
        if zhi1 + zhi2 in xiangchong:
            return xiangchong[zhi1 + zhi2]
        if zhi2 + zhi1 in xiangchong:
            return xiangchong[zhi2 + zhi1]
        
        # 地支相刑
        xiangxing = {"寅巳申": "相刑", "丑未戌": "相刑", "子卯": "相刑"}
        for group, name in xiangxing.items():
            if zhi1 in group and zhi2 in group:
                return name
        
        # 地支相害
        xianghai = {"子未": "相害", "丑午": "相害", "寅巳": "相害",
                    "卯辰": "相害", "申亥": "相害", "酉戌": "相害"}
        if zhi1 + zhi2 in xianghai:
            return xianghai[zhi1 + zhi2]
        if zhi2 + zhi1 in xianghai:
            return xianghai[zhi2 + zhi1]
        
        return "无特殊关系"


# ========== 辅助函数：农历转阳历 ==========

def lunar_to_solar(lunar_year: int, lunar_month: int, lunar_day: int,
                   is_leap: bool = False) -> Optional[Tuple[int, int, int]]:
    """
    农历转阳历
    需要安装 zhdate 库: pip install zhdate
    """
    try:
        from zhdate import ZhDate
        zh = ZhDate(lunar_year, lunar_month, lunar_day, leap=is_leap)
        solar = zh.to_datetime()
        return solar.year, solar.month, solar.day
    except ImportError:
        print("[提示] 如需农历转阳历，请安装 zhdate: pip install zhdate")
        return None
    except Exception as e:
        print(f"[错误] 农历转换失败: {e}")
        return None


def main():
    """命令行测试入口"""
    import sys

    # 解析参数：年 月 日 时 分 [性别] [经度]
    if len(sys.argv) >= 6:
        year = int(sys.argv[1])
        month = int(sys.argv[2])
        day = int(sys.argv[3])
        hour = int(sys.argv[4])
        minute = int(sys.argv[5])
        gender = sys.argv[6] if len(sys.argv) > 6 else "男"
        
        # 解析最后一个参数：如果是数字则为经度，否则为城市名
        city = None
        longitude = 116.4
        if len(sys.argv) > 7:
            last_arg = sys.argv[7]
            try:
                longitude = float(last_arg)
            except ValueError:
                # 不是数字，作为城市名处理
                city = last_arg
    else:
        # 默认测试用例
        year, month, day, hour, minute = 1990, 5, 15, 10, 30
        gender = "男"
        city = None
        longitude = 116.4
        print(f"用法: python bazi_core.py <年> <月> <日> <时> <分> [性别] [城市|经度]")
        print(f"使用默认测试: {year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d} {gender} 北京\n")

    bazi = BaziCore(city=city, longitude=longitude)
    result = bazi.solar_to_bazi(year, month, day, hour, minute, gender)
    print(bazi.format_output(result))

    # 同时打印节气对照
    print("\n【当年节气时刻】")
    jieqi = bazi.get_all_jieqi(year)
    for name, dt in jieqi.items():
        print(f"  {name}: {dt.strftime('%m-%d %H:%M')}")


if __name__ == "__main__":
    main()

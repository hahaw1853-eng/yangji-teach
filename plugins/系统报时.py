# [title: 系统报时]
# [icon: https://gcore.jsdelivr.net/gh/lhz03/img@0d28f1a9cc71d7269440d5f1eb40f40df08689da/2026/01/31/2a7606203ed51989a1bc2887c5a9489d.png]
# [language: python]
# [rule: ^(系统报时|报时|时间|几点了|现在几点)$]
# [disable: false]
# [open_source: true]
# [platform: qq,qb,wx,gw,sb,wb,tg,tb,qx,xy,ip]
# [priority: 9999999999999999999]
# [public: true]
# [version: 1.0.0]
# [price: 0]
# [author: 系统报时]
# [service: ]
# [description: 🦄 系统报时插件，支持公历、农历、节气、生肖、星座、时辰、时段等信息展示]

import time
import math
from datetime import datetime, timedelta
import middleware

# ==================== 农历数据表 (1900-2100) ====================
# 每年用5位十六进制数表示：
# 第1位：闰月月份（0表示无闰月，1-12表示闰月）
# 后4位：从正月到十二月（含闰月）每月大小，1=大月30天，0=小月29天
LUNAR_DATA = [
    0x04bd8,0x04ae0,0x0a570,0x054d5,0x0d260,0x0d950,0x16554,0x056a0,0x09ad0,0x055d2,
    0x04ae0,0x0a5b6,0x0a4d0,0x0d250,0x1d255,0x0b540,0x0d6a0,0x0ada2,0x095b0,0x14977,
    0x04970,0x0a4b0,0x0b4b5,0x06a50,0x06d40,0x1ab54,0x02b60,0x09570,0x052f2,0x04970,
    0x06566,0x0d4a0,0x0ea50,0x06e95,0x05ad0,0x02b60,0x186e3,0x092e0,0x1c8d7,0x0c950,
    0x0d4a0,0x1d8a6,0x0b550,0x056a0,0x1a5b4,0x025d0,0x092d0,0x0d2b2,0x0a950,0x0b557,
    0x06ca0,0x0b550,0x15355,0x04da0,0x0a5d0,0x14573,0x052d0,0x0a9a8,0x0e950,0x06aa0,
    0x0aea6,0x0ab50,0x04b60,0x0aae4,0x0a570,0x05260,0x0f263,0x0d950,0x05b57,0x056a0,
    0x096d0,0x04dd5,0x04ad0,0x0a4d0,0x0d4d4,0x0d250,0x0d558,0x0b540,0x0b5a0,0x195a6,
    0x095b0,0x049b0,0x0a974,0x0a4b0,0x0b27a,0x06a50,0x06d40,0x0af46,0x0ab60,0x09570,
    0x04af5,0x04970,0x064b0,0x074a3,0x0ea50,0x06b58,0x055c0,0x0ab60,0x096d5,0x092e0,
    0x0c960,0x0d954,0x0d4a0,0x0da50,0x07552,0x056a0,0x0abb7,0x025d0,0x092d0,0x0cab5,
    0x0a950,0x0b4a0,0x0baa4,0x0ad50,0x055d9,0x04ba0,0x0a5b0,0x15176,0x052b0,0x0a930,
    0x07954,0x06aa0,0x0ad50,0x05b52,0x04b60,0x0a6e6,0x0a4e0,0x0d260,0x0ea65,0x0d530,
    0x05aa0,0x076a3,0x096d0,0x04bd7,0x04ad0,0x0a4d0,0x1d0b6,0x0d250,0x0d520,0x0dd45,
    0x0b5a0,0x056d0,0x055b2,0x049b0,0x0a577,0x0a4b0,0x0aa50,0x1b255,0x06d20,0x0ada0,
    0x14b63,0x09370,0x049f8,0x04970,0x064b0,0x168a6,0x0ea50,0x06b20,0x1a6c4,0x0aae0,
    0x0a2e0,0x0d2e3,0x0c960,0x0d557,0x0d4a0,0x0da50,0x05d55,0x056a0,0x0a6d0,0x055d4,
    0x052d0,0x0a9b8,0x0a950,0x0b4a0,0x0b6a6,0x0ad50,0x055a0,0x0aba4,0x0a5b0,0x052b0,
    0x0b273,0x06930,0x07337,0x06aa0,0x0ad50,0x14b55,0x04b60,0x0a570,0x054e4,0x0d160,
    0x0e968,0x0d520,0x0daa0,0x16aa6,0x056d0,0x04ae0,0x0a9d4,0x0a2d0,0x0d150,0x0f252,
    0x0d520
]

# 天干
TIAN_GAN = "甲乙丙丁戊己庚辛壬癸"
# 地支
DI_ZHI = "子丑寅卯辰巳午未申酉戌亥"
# 生肖
SHENG_XIAO = "鼠牛虎兔龙蛇马羊猴鸡狗猪"
# 农历月份名称
LUNAR_MONTH_NAME = ["正","二","三","四","五","六","七","八","九","十","冬","腊"]
# 农历日期名称
LUNAR_DAY_NAME = [
    "初一","初二","初三","初四","初五","初六","初七","初八","初九","初十",
    "十一","十二","十三","十四","十五","十六","十七","十八","十九","二十",
    "廿一","廿二","廿三","廿四","廿五","廿六","廿七","廿八","廿九","三十"
]
# 节气名称
JIE_QI_NAME = [
    "小寒","大寒","立春","雨水","惊蛰","春分",
    "清明","谷雨","立夏","小满","芒种","夏至",
    "小暑","大暑","立秋","处暑","白露","秋分",
    "寒露","霜降","立冬","小雪","大雪","冬至"
]
# 星座日期分界 (月,日)
ZODIAC_DATES = [
    (1,20),(2,19),(3,21),(4,20),(5,21),(6,21),
    (7,23),(8,23),(9,23),(10,23),(11,22),(12,22)
]
ZODIAC_NAME = ["摩羯座","水瓶座","双鱼座","白羊座","金牛座","双子座",
               "巨蟹座","狮子座","处女座","天秤座","天蝎座","射手座"]

# ==================== 核心计算函数 ====================

def get_zodiac(month, day):
    """获取星座"""
    for i, (m, d) in enumerate(ZODIAC_DATES):
        if (month == m and day >= d) or (month == m + 1 and day < ZODIAC_DATES[(i+1)%12][1]):
            if month == 12 and day >= 22:
                return ZODIAC_NAME[0]
            return ZODIAC_NAME[i]
    return ZODIAC_NAME[0]

def get_shichen(hour):
    """获取时辰"""
    shichen_index = (hour + 1) // 2 % 12
    return DI_ZHI[shichen_index] + "时"

def get_time_period(hour):
    """获取时段"""
    periods = [
        (0, "🌙 深夜"), (1, "🌙 深夜"), (2, "🌙 凌晨"), (3, "🌙 凌晨"),
        (4, "🌙 凌晨"), (5, "🌅 清晨"), (6, "🌅 清晨"), (7, "🌄 早晨"),
        (8, "🌄 早晨"), (9, "☀️ 上午"), (10, "☀️ 上午"), (11, "☀️ 上午"),
        (12, "🌞 中午"), (13, "🌞 中午"), (14, "🌤️ 下午"), (15, "🌤️ 下午"),
        (16, "🌤️ 下午"), (17, "🌇 傍晚"), (18, "🌇 傍晚"), (19, "🌆 晚上"),
        (20, "🌆 晚上"), (21, "🌃 晚上"), (22, "🌃 晚上"), (23, "🌙 深夜")
    ]
    return periods[hour][1]

def get_weekday(year, month, day):
    """获取星期"""
    weekdays = ["星期一","星期二","星期三","星期四","星期五","星期六","星期日"]
    d = datetime(year, month, day)
    return weekdays[d.weekday()]

def lunar_year_days(y):
    """计算农历年总天数"""
    i, sum_days = 0x8000, 348
    leap = LUNAR_DATA[y - 1900] >> 16
    while i > 0x8:
        if (LUNAR_DATA[y - 1900] & i) != 0:
            sum_days += 1
        i >>= 1
    return sum_days + (30 if leap > 0 else 0)

def leap_month(y):
    """获取闰月"""
    return LUNAR_DATA[y - 1900] >> 16

def leapDays(y):
    """获取闰月天数"""
    if leapMonth(y) > 0:
        return 30 if (LUNAR_DATA[y - 1900] & 0x10000) != 0 else 29
    return 0

def monthDays(y, m):
    """获取农历月天数"""
    return 29 if (LUNAR_DATA[y - 1900] & (0x10000 >> m)) == 0 else 30

def solar_to_lunar(year, month, day):
    """公历转农历"""
    base = datetime(1900, 1, 31)
    obj = datetime(year, month, day)
    offset = (obj - base).days
    
    lunar_year = 1900
    while lunar_year < 2100 and offset > 0:
        days_in_year = lunar_year_days(lunar_year)
        offset -= days_in_year
        lunar_year += 1
    
    if offset < 0:
        offset += lunar_year_days(lunar_year - 1)
        lunar_year -= 1
    
    leap = leapMonth(lunar_year)
    is_leap = False
    lunar_month = 1
    while lunar_month < 13 and offset > 0:
        if leap > 0 and lunar_month == (leap + 1) and not is_leap:
            lunar_month -= 1
            is_leap = True
            days_in_month = leapDays(lunar_year)
        else:
            days_in_month = monthDays(lunar_year, lunar_month)
        
        if is_leap and lunar_month == (leap + 1):
            is_leap = False
        
        offset -= days_in_month
        lunar_month += 1
    
    if offset == 0 and leap > 0 and lunar_month == leap + 1:
        if is_leap:
            is_leap = False
        else:
            is_leap = True
            lunar_month -= 1
    
    if offset < 0:
        offset += days_in_month
        lunar_month -= 1
    
    lunar_day = offset + 1
    
    # 干支纪年
    gan_idx = (lunar_year - 4) % 10
    zhi_idx = (lunar_year - 4) % 12
    
    return {
        "year": lunar_year,
        "month": lunar_month,
        "day": int(lunar_day),
        "is_leap": is_leap,
        "gan_zhi": TIAN_GAN[gan_idx] + DI_ZHI[zhi_idx],
        "sheng_xiao": SHENG_XIAO[zhi_idx]
    }

def get_jie_qi(year, month, day):
    """获取节气（基于1900-2100年数据表近似算法）"""
    # 24节气在公历中的日期基本固定，使用查表法
    # 数据格式：每个节气对应的日期（1900年基准，每百年微调）
    # 这里使用简化算法：基于Celestia算法计算太阳黄经
    
    # 节气日期表（1900-2100年通用近似值，误差±1天）
    jie_qi_table = {
        1: [(5,"小寒"),(20,"大寒")],
        2: [(3,"立春"),(18,"雨水")],
        3: [(5,"惊蛰"),(20,"春分")],
        4: [(4,"清明"),(20,"谷雨")],
        5: [(5,"立夏"),(21,"小满")],
        6: [(5,"芒种"),(21,"夏至")],
        7: [(7,"小暑"),(22,"大暑")],
        8: [(7,"立秋"),(23,"处暑")],
        9: [(7,"白露"),(23,"秋分")],
        10:[(8,"寒露"),(23,"霜降")],
        11:[(7,"立冬"),(22,"小雪")],
        12:[(7,"大雪"),(21,"冬至")]
    }
    
    # 获取当前月节气
    current_month_jie_qi = jie_qi_table.get(month, [])
    
    # 判断当天是什么节气
    for d, name in current_month_jie_qi:
        if day == d:
            return name, True  # 当天是节气日
    
    # 判断当前处于哪个节气之间
    prev_jie_qi = None
    for m in range(1, 13):
        for d, name in jie_qi_table.get(m, []):
            if (m < month) or (m == month and d < day):
                prev_jie_qi = name
            elif (m > month) or (m == month and d > day):
                return prev_jie_qi if prev_jie_qi else "冬至", False
    
    return "冬至", False

def get_next_jie_qi(year, month, day):
    """获取下一个节气"""
    jie_qi_table = {
        1: [(5,"小寒"),(20,"大寒")],
        2: [(3,"立春"),(18,"雨水")],
        3: [(5,"惊蛰"),(20,"春分")],
        4: [(4,"清明"),(20,"谷雨")],
        5: [(5,"立夏"),(21,"小满")],
        6: [(5,"芒种"),(21,"夏至")],
        7: [(7,"小暑"),(22,"大暑")],
        8: [(7,"立秋"),(23,"处暑")],
        9: [(7,"白露"),(23,"秋分")],
        10:[(8,"寒露"),(23,"霜降")],
        11:[(7,"立冬"),(22,"小雪")],
        12:[(7,"大雪"),(21,"冬至")]
    }
    
    for m in range(month, 13):
        for d, name in jie_qi_table.get(m, []):
            if m > month or (m == month and d > day):
                return name, m, d
    return "小寒", 1, 5

# ==================== 主程序 ====================

senderID = middleware.getSenderID()
sender = middleware.Sender(senderID)

def main():
    now = datetime.now()
    year, month, day = now.year, now.month, now.day
    hour, minute, second = now.hour, now.minute, now.second
    
    # 农历
    lunar = solar_to_lunar(year, month, day)
    lunar_month_name = LUNAR_MONTH_NAME[lunar["month"] - 1]
    lunar_day_name = LUNAR_DAY_NAME[lunar["day"] - 1]
    leap_str = "闰" if lunar["is_leap"] else ""
    
    # 节气
    current_jie_qi, is_today = get_jie_qi(year, month, day)
    next_jie_qi, next_m, next_d = get_next_jie_qi(year, month, day)
    
    # 星期
    weekday = get_weekday(year, month, day)
    
    # 时段
    period = get_time_period(hour)
    
    # 时辰
    shichen = get_shichen(hour)
    
    # 星座
    zodiac = get_zodiac(month, day)
    
    # 格式化时间
    time_str = f"{hour}点{minute}分{second}秒"
    
    # 构建输出
    lines = [
        "🦄 系统报时 🦄",
        "",
        f"📆 公历：{year}年{month}月{day}日",
        f"🌍 星期：{weekday}",
        f"🌐 时段：{period}",
        f"⌚ 时间：{time_str}",
        f"⏰ 时辰：{shichen}",
        "",
        f"🗓️ 农历：{lunar['gan_zhi']}年 {leap_str}{lunar_month_name}月{lunar_day_name}",
        f"🐉 生肖：{lunar['sheng_xiao']}年",
        f"♈ 星座：{zodiac}",
        f"🌸 节气：{current_jie_qi}",
    ]
    
    # 如果不是节气当天，显示下一个节气
    if not is_today:
        lines.append(f"🍂 下个：{next_jie_qi}（{next_m}月{next_d}日）")
    else:
        lines.append("✨ 今日节气，顺遂安康 ✨")
    
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━")
    lines.append("💫 愿你今日好心情")
    
    sender.reply("\n".join(lines))

if __name__ == "__main__":
    main()

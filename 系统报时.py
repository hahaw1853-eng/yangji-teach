# [title: 系统报时]
# [icon: https://gcore.jsdelivr.net/gh/lhz03/img@0d28f1a9cc71d7269440d5f1eb40f40df08689da/2026/01/31/2a7606203ed51989a1bc2887c5a9489d.png]
# [language: python]
# [rule: ^(系统报时|报时|时间|几点了|现在几点|开启报时|关闭报时|设置报时|报时时间|报时设置)$]
# [disable: false]
# [open_source: true]
# [platform: qq,qb,wx,gw,sb,wb,tg,tb,qx,xy,ip]
# [priority: 9999999999999999999]
# [public: true]
# [version: 1.1.0]
# [price: 0]
# [author: 系统报时]
# [service: ]
# [description: 🦄 系统报时插件，支持手动报时 + 自动定时报时。指令：系统报时/开启报时/关闭报时/设置报时 8:00/报时设置]

import time
import json
import re
from datetime import datetime, timedelta
import middleware

# ==================== 农历数据表 (1900-2100) ====================
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

TIAN_GAN = "甲乙丙丁戊己庚辛壬癸"
DI_ZHI = "子丑寅卯辰巳午未申酉戌亥"
SHENG_XIAO = "鼠牛虎兔龙蛇马羊猴鸡狗猪"
LUNAR_MONTH_NAME = ["正","二","三","四","五","六","七","八","九","十","冬","腊"]
LUNAR_DAY_NAME = [
    "初一","初二","初三","初四","初五","初六","初七","初八","初九","初十",
    "十一","十二","十三","十四","十五","十六","十七","十八","十九","二十",
    "廿一","廿二","廿三","廿四","廿五","廿六","廿七","廿八","廿九","三十"
]
JIE_QI_NAME = [
    "小寒","大寒","立春","雨水","惊蛰","春分",
    "清明","谷雨","立夏","小满","芒种","夏至",
    "小暑","大暑","立秋","处暑","白露","秋分",
    "寒露","霜降","立冬","小雪","大雪","冬至"
]
ZODIAC_DATES = [
    (1,20),(2,19),(3,21),(4,20),(5,21),(6,21),
    (7,23),(8,23),(9,23),(10,23),(11,22),(12,22)
]
ZODIAC_NAME = ["摩羯座","水瓶座","双鱼座","白羊座","金牛座","双子座",
               "巨蟹座","狮子座","处女座","天秤座","天蝎座","射手座"]

BUCKET_NAME = "system_time"

# ==================== 核心计算函数 ====================

def get_zodiac(month, day):
    for i, (m, d) in enumerate(ZODIAC_DATES):
        if (month == m and day >= d) or (month == m + 1 and day < ZODIAC_DATES[(i+1)%12][1]):
            if month == 12 and day >= 22:
                return ZODIAC_NAME[0]
            return ZODIAC_NAME[i]
    return ZODIAC_NAME[0]

def get_shichen(hour):
    shichen_index = (hour + 1) // 2 % 12
    return DI_ZHI[shichen_index] + "时"

def get_time_period(hour):
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
    weekdays = ["星期一","星期二","星期三","星期四","星期五","星期六","星期日"]
    d = datetime(year, month, day)
    return weekdays[d.weekday()]

def lunar_year_days(y):
    i, sum_days = 0x8000, 348
    leap = leap_month(y)
    while i > 0x8:
        if (LUNAR_DATA[y - 1900] & i) != 0:
            sum_days += 1
        i >>= 1
    return sum_days + (30 if leap > 0 else 0)

def leap_month(y):
    return LUNAR_DATA[y - 1900] >> 16

def leap_days(y):
    lm = leap_month(y)
    if lm > 0:
        return 30 if (LUNAR_DATA[y - 1900] & 0x10000) != 0 else 29
    return 0

def month_days(y, m):
    return 29 if (LUNAR_DATA[y - 1900] & (0x10000 >> m)) == 0 else 30

def solar_to_lunar(year, month, day):
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
    
    leap = leap_month(lunar_year)
    is_leap = False
    lunar_month = 1
    while lunar_month < 13 and offset > 0:
        if leap > 0 and lunar_month == (leap + 1) and not is_leap:
            lunar_month -= 1
            is_leap = True
            days_in_month = leap_days(lunar_year)
        else:
            days_in_month = month_days(lunar_year, lunar_month)
        
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
    
    current_month_jie_qi = jie_qi_table.get(month, [])
    for d, name in current_month_jie_qi:
        if day == d:
            return name, True
    
    prev_jie_qi = None
    for m in range(1, 13):
        for d, name in jie_qi_table.get(m, []):
            if (m < month) or (m == month and d < day):
                prev_jie_qi = name
            elif (m > month) or (m == month and d > day):
                return prev_jie_qi if prev_jie_qi else "冬至", False
    
    return "冬至", False

def get_next_jie_qi(year, month, day):
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

# ==================== 报时内容生成 ====================

def generate_time_report():
    now = datetime.now()
    year, month, day = now.year, now.month, now.day
    hour, minute, second = now.hour, now.minute, now.second
    
    lunar = solar_to_lunar(year, month, day)
    lunar_month_name = LUNAR_MONTH_NAME[lunar["month"] - 1]
    lunar_day_name = LUNAR_DAY_NAME[lunar["day"] - 1]
    leap_str = "闰" if lunar["is_leap"] else ""
    
    current_jie_qi, is_today = get_jie_qi(year, month, day)
    next_jie_qi, next_m, next_d = get_next_jie_qi(year, month, day)
    
    weekday = get_weekday(year, month, day)
    period = get_time_period(hour)
    shichen = get_shichen(hour)
    zodiac = get_zodiac(month, day)
    time_str = f"{hour}点{minute}分{second}秒"
    
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
    
    if not is_today:
        lines.append(f"🍂 下个：{next_jie_qi}（{next_m}月{next_d}日）")
    else:
        lines.append("✨ 今日节气，顺遂安康 ✨")
    
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━")
    lines.append("💫 愿你今日好心情")
    
    return "\n".join(lines)

# ==================== 存储管理 ====================

def get_groups():
    """获取所有开启自动报时的群配置"""
    data = middleware.bucketGet(BUCKET_NAME, "groups")
    if not data:
        return []
    try:
        return json.loads(data)
    except:
        return []

def save_groups(groups):
    middleware.bucketSet(BUCKET_NAME, "groups", json.dumps(groups, ensure_ascii=False))

def get_last_notify(group_id):
    """获取该群最后一次报时的日期"""
    return middleware.bucketGet(BUCKET_NAME, f"last_{group_id}") or ""

def set_last_notify(group_id, date_str):
    middleware.bucketSet(BUCKET_NAME, f"last_{group_id}", date_str)

def find_group(groups, group_id):
    for g in groups:
        if g.get("group_id") == group_id:
            return g
    return None

# ==================== 指令处理 ====================

senderID = middleware.getSenderID()
sender = middleware.Sender(senderID)
imtype = sender.getImtype()

def manual_report():
    """手动报时"""
    sender.reply(generate_time_report())

def enable_auto():
    """开启当前群自动报时"""
    group_id = sender.getGroupID()
    if not group_id:
        sender.reply("❌ 请在群聊中使用此指令")
        return
    
    groups = get_groups()
    existing = find_group(groups, group_id)
    
    if existing:
        sender.reply(f"✅ 本群已开启自动报时\n⏰ 当前时间：{existing.get('time','08:00')}\n💡 发送「设置报时 8:00」可修改时间")
        return
    
    groups.append({
        "group_id": group_id,
        "imtype": imtype,
        "time": "08:00"
    })
    save_groups(groups)
    sender.reply("✅ 已开启自动报时\n⏰ 默认每天 08:00 推送\n💡 发送「设置报时 9:00」可修改时间")

def disable_auto():
    """关闭当前群自动报时"""
    group_id = sender.getGroupID()
    if not group_id:
        sender.reply("❌ 请在群聊中使用此指令")
        return
    
    groups = get_groups()
    new_groups = [g for g in groups if g.get("group_id") != group_id]
    
    if len(new_groups) == len(groups):
        sender.reply("❌ 本群未开启自动报时")
        return
    
    save_groups(new_groups)
    # 清理该群的 last_notify
    try:
        middleware.bucketDel(BUCKET_NAME, f"last_{group_id}")
    except:
        pass
    
    sender.reply("✅ 已关闭本群自动报时")

def set_time(msg):
    """设置报时时间"""
    group_id = sender.getGroupID()
    if not group_id:
        sender.reply("❌ 请在群聊中使用此指令")
        return
    
    # 解析时间，支持：设置报时 8:00 / 设置报时 0800 / 设置报时 8点
    match = re.search(r'(\d{1,2})[:：\s]?(\d{2})?', msg)
    if not match:
        match = re.search(r'(\d{1,2})点', msg)
    
    if not match:
        sender.reply("❌ 时间格式错误\n💡 正确示例：设置报时 8:00 / 设置报时 9:30")
        return
    
    hour = int(match.group(1))
    minute = int(match.group(2)) if match.group(2) else 0
    
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        sender.reply("❌ 时间范围错误，小时 0-23，分钟 0-59")
        return
    
    time_str = f"{hour:02d}:{minute:02d}"
    
    groups = get_groups()
    existing = find_group(groups, group_id)
    
    if not existing:
        sender.reply("❌ 本群未开启自动报时，请先发送「开启报时」")
        return
    
    existing["time"] = time_str
    save_groups(groups)
    sender.reply(f"✅ 报时时间已设置为每天 {time_str}")

def show_settings():
    """查看当前群设置"""
    group_id = sender.getGroupID()
    if not group_id:
        sender.reply("❌ 请在群聊中使用此指令")
        return
    
    groups = get_groups()
    existing = find_group(groups, group_id)
    
    if not existing:
        sender.reply("❌ 本群未开启自动报时\n💡 发送「开启报时」即可开启")
        return
    
    time_setting = existing.get("time", "08:00")
    last = get_last_notify(group_id)
    
    msg = f"""=====报时设置=====
📍 群ID：{group_id}
⏰ 报时时间：每天 {time_setting}
📅 上次报时：{last if last else "暂无"}
✅ 状态：已开启
==================
💡 指令列表：
「开启报时」- 开启自动报时
「关闭报时」- 关闭自动报时
「设置报时 8:00」- 修改报时时间
「系统报时」- 手动报时一次"""
    sender.reply(msg)

# ==================== 定时任务 ====================

def cron_task():
    """定时任务：每分钟检查是否需要自动报时"""
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    
    groups = get_groups()
    if not groups:
        return
    
    for g in groups:
        group_id = g.get("group_id")
        set_time = g.get("time", "08:00")
        g_imtype = g.get("imtype", "qq")
        
        if not group_id:
            continue
        
        # 检查时间是否匹配（允许1分钟误差）
        if current_time != set_time:
            continue
        
        # 检查今天是否已经报过
        last = get_last_notify(group_id)
        if last == today_str:
            continue
        
        # 推送报时
        try:
            report = generate_time_report()
            middleware.push(g_imtype, group_id, "", "", report)
            set_last_notify(group_id, today_str)
        except Exception as e:
            print(f"[系统报时] 推送失败 {group_id}: {e}")

# ==================== 主入口 ====================

def main():
    msg = sender.getMessage().strip()
    
    if msg in ["系统报时", "报时", "时间", "几点了", "现在几点"]:
        manual_report()
    elif msg == "开启报时":
        enable_auto()
    elif msg == "关闭报时":
        disable_auto()
    elif msg == "报时设置":
        show_settings()
    elif msg.startswith("设置报时") or msg.startswith("报时时间"):
        set_time(msg)
    else:
        sender.setContinue()

if __name__ == "__main__":
    if imtype == 'fake':
        cron_task()
    else:
        main()

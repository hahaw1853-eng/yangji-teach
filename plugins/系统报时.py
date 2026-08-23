# [title: 系统报时]
# [icon: https://gcore.jsdelivr.net/gh/lhz03/img@0d28f1a9cc71d7269440d5f1eb40f40df08689da/2026/01/31/2a7606203ed51989a1bc2887c5a9489d.png]
# [language: python]
# [rule: ^(系统报时|报时|时间|几点了|现在几点|开启报时|关闭报时|报时设置|设置报时.*|报时时间.*|删除报时.*|取消报时.*)$]
# [disable: false]
# [open_source: true]
# [platform: qq,qb,wx,gw,sb,wb,tg,tb,qx,xy,ip]
# [priority: 9999999999999999999]
# [public: true]
# [version: 1.3.1]
# [price: 0]
# [author: 系统报时]
# [service: ]
# [cron: * * * * *]
# [description: 🦄 系统报时插件，支持多时间点自动报时。指令：系统报时/开启报时/关闭报时/设置报时 8:00/删除报时 8:00/报时设置]

import json
import re
import requests
from datetime import datetime, timedelta
import middleware

BUCKET_NAME = "system_time"
API_BASE = "https://api.530.news/api/lunar"

# 24节气公历日期表（2020-2030年精确数据）
JIE_QI_TABLE = {
    2020: { (1,6):"小寒",(1,20):"大寒",(2,4):"立春",(2,19):"雨水",(3,5):"惊蛰",(3,20):"春分",
            (4,4):"清明",(4,19):"谷雨",(5,5):"立夏",(5,20):"小满",(6,5):"芒种",(6,21):"夏至",
            (7,6):"小暑",(7,22):"大暑",(8,7):"立秋",(8,22):"处暑",(9,7):"白露",(9,22):"秋分",
            (10,8):"寒露",(10,23):"霜降",(11,7):"立冬",(11,22):"小雪",(12,7):"大雪",(12,21):"冬至" },
    2021: { (1,5):"小寒",(1,20):"大寒",(2,3):"立春",(2,18):"雨水",(3,5):"惊蛰",(3,20):"春分",
            (4,4):"清明",(4,20):"谷雨",(5,5):"立夏",(5,21):"小满",(6,5):"芒种",(6,21):"夏至",
            (7,7):"小暑",(7,22):"大暑",(8,7):"立秋",(8,23):"处暑",(9,7):"白露",(9,23):"秋分",
            (10,8):"寒露",(10,23):"霜降",(11,7):"立冬",(11,22):"小雪",(12,7):"大雪",(12,21):"冬至" },
    2022: { (1,5):"小寒",(1,20):"大寒",(2,4):"立春",(2,19):"雨水",(3,5):"惊蛰",(3,20):"春分",
            (4,5):"清明",(4,20):"谷雨",(5,5):"立夏",(5,21):"小满",(6,6):"芒种",(6,21):"夏至",
            (7,7):"小暑",(7,23):"大暑",(8,7):"立秋",(8,23):"处暑",(9,7):"白露",(9,23):"秋分",
            (10,8):"寒露",(10,23):"霜降",(11,7):"立冬",(11,22):"小雪",(12,7):"大雪",(12,22):"冬至" },
    2023: { (1,5):"小寒",(1,20):"大寒",(2,4):"立春",(2,19):"雨水",(3,6):"惊蛰",(3,21):"春分",
            (4,5):"清明",(4,20):"谷雨",(5,6):"立夏",(5,21):"小满",(6,6):"芒种",(6,21):"夏至",
            (7,7):"小暑",(7,23):"大暑",(8,8):"立秋",(8,23):"处暑",(9,8):"白露",(9,23):"秋分",
            (10,8):"寒露",(10,24):"霜降",(11,8):"立冬",(11,22):"小雪",(12,7):"大雪",(12,22):"冬至" },
    2024: { (1,6):"小寒",(1,20):"大寒",(2,4):"立春",(2,19):"雨水",(3,5):"惊蛰",(3,20):"春分",
            (4,4):"清明",(4,19):"谷雨",(5,5):"立夏",(5,20):"小满",(6,5):"芒种",(6,21):"夏至",
            (7,6):"小暑",(7,22):"大暑",(8,7):"立秋",(8,22):"处暑",(9,7):"白露",(9,22):"秋分",
            (10,8):"寒露",(10,23):"霜降",(11,7):"立冬",(11,22):"小雪",(12,6):"大雪",(12,21):"冬至" },
    2025: { (1,5):"小寒",(1,20):"大寒",(2,3):"立春",(2,18):"雨水",(3,5):"惊蛰",(3,20):"春分",
            (4,4):"清明",(4,20):"谷雨",(5,5):"立夏",(5,21):"小满",(6,5):"芒种",(6,21):"夏至",
            (7,7):"小暑",(7,22):"大暑",(8,7):"立秋",(8,23):"处暑",(9,7):"白露",(9,23):"秋分",
            (10,8):"寒露",(10,23):"霜降",(11,7):"立冬",(11,22):"小雪",(12,7):"大雪",(12,21):"冬至" },
    2026: { (1,5):"小寒",(1,20):"大寒",(2,4):"立春",(2,18):"雨水",(3,5):"惊蛰",(3,20):"春分",
            (4,5):"清明",(4,20):"谷雨",(5,5):"立夏",(5,21):"小满",(6,5):"芒种",(6,21):"夏至",
            (7,7):"小暑",(7,22):"大暑",(8,7):"立秋",(8,23):"处暑",(9,7):"白露",(9,23):"秋分",
            (10,8):"寒露",(10,23):"霜降",(11,7):"立冬",(11,22):"小雪",(12,7):"大雪",(12,21):"冬至" },
    2027: { (1,5):"小寒",(1,20):"大寒",(2,4):"立春",(2,19):"雨水",(3,6):"惊蛰",(3,21):"春分",
            (4,5):"清明",(4,20):"谷雨",(5,6):"立夏",(5,21):"小满",(6,6):"芒种",(6,21):"夏至",
            (7,7):"小暑",(7,23):"大暑",(8,8):"立秋",(8,23):"处暑",(9,8):"白露",(9,23):"秋分",
            (10,8):"寒露",(10,23):"霜降",(11,7):"立冬",(11,22):"小雪",(12,7):"大雪",(12,22):"冬至" },
    2028: { (1,6):"小寒",(1,20):"大寒",(2,4):"立春",(2,19):"雨水",(3,5):"惊蛰",(3,20):"春分",
            (4,4):"清明",(4,20):"谷雨",(5,5):"立夏",(5,20):"小满",(6,5):"芒种",(6,21):"夏至",
            (7,6):"小暑",(7,22):"大暑",(8,7):"立秋",(8,22):"处暑",(9,7):"白露",(9,22):"秋分",
            (10,8):"寒露",(10,23):"霜降",(11,7):"立冬",(11,22):"小雪",(12,6):"大雪",(12,21):"冬至" },
    2029: { (1,5):"小寒",(1,20):"大寒",(2,3):"立春",(2,18):"雨水",(3,5):"惊蛰",(3,20):"春分",
            (4,4):"清明",(4,20):"谷雨",(5,5):"立夏",(5,21):"小满",(6,5):"芒种",(6,21):"夏至",
            (7,7):"小暑",(7,22):"大暑",(8,7):"立秋",(8,23):"处暑",(9,7):"白露",(9,23):"秋分",
            (10,8):"寒露",(10,23):"霜降",(11,7):"立冬",(11,22):"小雪",(12,7):"大雪",(12,21):"冬至" },
    2030: { (1,5):"小寒",(1,20):"大寒",(2,4):"立春",(2,19):"雨水",(3,6):"惊蛰",(3,21):"春分",
            (4,5):"清明",(4,20):"谷雨",(5,6):"立夏",(5,21):"小满",(6,6):"芒种",(6,21):"夏至",
            (7,7):"小暑",(7,23):"大暑",(8,8):"立秋",(8,23):"处暑",(9,8):"白露",(9,23):"秋分",
            (10,8):"寒露",(10,23):"霜降",(11,7):"立冬",(11,22):"小雪",(12,7):"大雪",(12,22):"冬至" },
}

TIAN_GAN = "甲乙丙丁戊己庚辛壬癸"
DI_ZHI = "子丑寅卯辰巳午未申酉戌亥"
SHENG_XIAO = "鼠牛虎兔龙蛇马羊猴鸡狗猪"
LUNAR_DAY_NAME = ["初一","初二","初三","初四","初五","初六","初七","初八","初九","初十",
    "十一","十二","十三","十四","十五","十六","十七","十八","十九","二十",
    "廿一","廿二","廿三","廿四","廿五","廿六","廿七","廿八","廿九","三十"]


senderID = middleware.getSenderID()
sender = middleware.Sender(senderID)
imtype = sender.getImtype()

# ==================== 工具函数 ====================

ZODIAC_DATES = [20, 19, 21, 20, 21, 21, 23, 23, 23, 23, 22, 22]
ZODIAC_NAME = ["摩羯座","水瓶座","双鱼座","白羊座","金牛座","双子座",
               "巨蟹座","狮子座","处女座","天秤座","天蝎座","射手座"]
ZODIAC_EMOJI = ["♑","♒","♓","♈","♉","♊","♋","♌","♍","♎","♏","♐"]

def get_zodiac(month, day):
    idx = month - 1
    if day >= ZODIAC_DATES[idx]:
        idx = (idx + 1) % 12
    return ZODIAC_NAME[idx], ZODIAC_EMOJI[idx]

def get_shichen(hour):
    return DI_ZHI[(hour + 1) // 2 % 12] + "时"

def get_time_period(hour):
    periods = [(0,"🌙 深夜"),(1,"🌙 深夜"),(2,"🌙 凌晨"),(3,"🌙 凌晨"),(4,"🌙 凌晨"),
               (5,"🌅 清晨"),(6,"🌅 清晨"),(7,"🌄 早晨"),(8,"🌄 早晨"),(9,"☀️ 上午"),(10,"☀️ 上午"),(11,"☀️ 上午"),
               (12,"🌞 中午"),(13,"🌞 中午"),(14,"🌤️ 下午"),(15,"🌤️ 下午"),(16,"🌤️ 下午"),
               (17,"🌇 傍晚"),(18,"🌇 傍晚"),(19,"🌆 晚上"),(20,"🌆 晚上"),(21,"🌃 晚上"),(22,"🌃 晚上"),(23,"🌙 深夜")]
    return periods[hour][1]

def get_weekday(d):
    return ["星期一","星期二","星期三","星期四","星期五","星期六","星期日"][d.weekday()]

def get_jie_qi(year, month, day):
    table = JIE_QI_TABLE.get(year, JIE_QI_TABLE.get(2026, {}))
    if (month, day) in table:
        return table[(month, day)], True
    prev = None
    for (m, d), name in sorted(table.items()):
        if (m < month) or (m == month and d < day):
            prev = name
        elif (m > month) or (m == month and d > day):
            return prev or "冬至", False
    return prev or "冬至", False

def get_next_jie_qi(year, month, day):
    table = JIE_QI_TABLE.get(year, JIE_QI_TABLE.get(2026, {}))
    for (m, d), name in sorted(table.items()):
        if m > month or (m == month and d > day):
            return name, m, d
    return "小寒", 1, 5

def fetch_lunar(date_str=None):
    try:
        url = f"{API_BASE}?date={date_str or 'today'}&timezone=8"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("code") == 200:
                return data.get("data", {})
    except Exception:
        pass
    return {}

def generate_time_report():
    now = datetime.now()
    y, m, d = now.year, now.month, now.day
    h, mi, s = now.hour, now.minute, now.second

    api_data = fetch_lunar(f"{y}-{m:02d}-{d:02d}")

    lunar_year = api_data.get("lunarYear", y)
    lunar_month = api_data.get("lunarMonth", 1)
    lunar_day = api_data.get("lunarDay", 1)
    lunar_month_name = api_data.get("lunarMonthName", f"{lunar_month}月")
    lunar_day_name = api_data.get("lunarDayName", f"{lunar_day}日")
    is_leap = api_data.get("isLeap", False)
    year_gz = api_data.get("yearInGanZhi", "")
    zodiac = api_data.get("zodiac", "")

    if not year_gz:
        year_gz = TIAN_GAN[(lunar_year - 4) % 10] + DI_ZHI[(lunar_year - 4) % 12]
    if not zodiac:
        zodiac = SHENG_XIAO[(lunar_year - 4) % 12]

    leap_str = "闰" if is_leap else ""

    jie_qi, is_today = get_jie_qi(y, m, d)
    next_jq, next_m, next_d = get_next_jie_qi(y, m, d)

    weekday = api_data.get("weekDay") or get_weekday(now)
    period = get_time_period(h)
    shichen = get_shichen(h)
    zodiac_sign, zodiac_emoji = get_zodiac(m, d)
    time_str = f"{h}点{mi}分{s}秒"

    lines = [
        "🦄 系统报时 🦄",
        "",
        f"📆 公历：{y}年{m}月{d}日",
        f"🌍 星期：{weekday}",
        f"🌐 时段：{period}",
        f"⌚ 时间：{time_str}",
        f"⏰ 时辰：{shichen}",
        "",
        f"🗓️ 农历：{year_gz}年 {leap_str}{lunar_month_name}{lunar_day_name}",
        f"🐉 生肖：{zodiac}年",
        f"{zodiac_emoji} 星座：{zodiac_sign}",
        f"🌸 节气：{jie_qi}",
    ]

    if not is_today:
        lines.append(f"🍂 下个：{next_jq}（{next_m}月{next_d}日）")
    else:
        lines.append("✨ 今日节气，顺遂安康 ✨")

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━")
    # 每日段子
    try:
        duanzi_resp = requests.get("https://tmini.net/api/duanzi", timeout=5)
        if duanzi_resp.status_code == 200:
            duanzi_data = duanzi_resp.json()
            if duanzi_data.get("success") and duanzi_data.get("quote"):
                lines.append("")
                lines.append(f"😄 每日段子：{duanzi_data['quote']}")
    except Exception:
        pass

    lines.append("💫 愿你今日好心情")

    return "\n".join(lines)

# ==================== 存储管理 ====================

def get_groups():
    data = middleware.bucketGet(BUCKET_NAME, "groups")
    if not data:
        return []
    try:
        return json.loads(data)
    except:
        return []

def save_groups(groups):
    middleware.bucketSet(BUCKET_NAME, "groups", json.dumps(groups, ensure_ascii=False))

def get_last_notify(chat_id, time_str):
    """获取该群某个时间点的最后报时日期"""
    return middleware.bucketGet(BUCKET_NAME, f"last_{chat_id}_{time_str}") or ""

def set_last_notify(chat_id, time_str, date_str):
    middleware.bucketSet(BUCKET_NAME, f"last_{chat_id}_{time_str}", date_str)

def find_group(groups, chat_id):
    for g in groups:
        if g.get("chat_id") == chat_id:
            return g
    return None

def migrate_old_data(groups):
    """兼容旧数据：单时间 -> 时间列表"""
    changed = False
    for g in groups:
        if "time" in g and isinstance(g["time"], str):
            g["times"] = [g["time"]]
            del g["time"]
            changed = True
        elif "times" not in g:
            g["times"] = ["08:00"]
            changed = True
    if changed:
        save_groups(groups)
    return groups

# ==================== 指令处理 ====================

def manual_report():
    sender.reply(generate_time_report())

def enable_auto():
    chat_id = sender.getChatID()
    user_id = sender.getUserID()
    if not chat_id or chat_id == user_id:
        sender.reply("❌ 请在群聊中使用此指令")
        return

    groups = get_groups()
    groups = migrate_old_data(groups)
    existing = find_group(groups, chat_id)
    if existing:
        times = existing.get("times", ["08:00"])
        times_str = "、".join(times)
        sender.reply(f"✅ 本群已开启自动报时\n⏰ 当前时间：{times_str}\n💡 发送「设置报时 8:00」可添加时间\n💡 发送「删除报时 8:00」可删除时间")
        return

    groups.append({"chat_id": chat_id, "imtype": imtype, "times": ["08:00"]})
    save_groups(groups)
    sender.reply("✅ 已开启自动报时\n⏰ 默认每天 08:00 推送\n💡 发送「设置报时 9:00」可添加更多时间")

def disable_auto():
    chat_id = sender.getChatID()
    user_id = sender.getUserID()
    if not chat_id or chat_id == user_id:
        sender.reply("❌ 请在群聊中使用此指令")
        return

    groups = get_groups()
    new_groups = [g for g in groups if g.get("chat_id") != chat_id]
    if len(new_groups) == len(groups):
        sender.reply("❌ 本群未开启自动报时")
        return

    save_groups(new_groups)
    # 清理所有该群的 last_notify
    try:
        keys = middleware.bucketKeys(BUCKET_NAME)
        for k in keys:
            if k.startswith(f"last_{chat_id}_"):
                middleware.bucketDel(BUCKET_NAME, k)
    except:
        pass
    sender.reply("✅ 已关闭本群自动报时")

def parse_time(time_part):
    """解析时间字符串，返回 HH:MM 或 None"""
    if not time_part:
        return None
    patterns = [
        r'(\d{1,2})[:：\s](\d{2})',
        r'(\d{1,2})点(\d{1,2})分?',
        r'(\d{1,2})(\d{2})',
        r'(\d{1,2})',
    ]
    for pat in patterns:
        m = re.search(pat, time_part)
        if m:
            hour = int(m.group(1))
            minute_str = m.group(2) if len(m.groups()) >= 2 else None
            minute = int(minute_str) if minute_str and minute_str.strip() else 0
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return f"{hour:02d}:{minute:02d}"
    return None

def set_time(msg):
    chat_id = sender.getChatID()
    user_id = sender.getUserID()
    if not chat_id or chat_id == user_id:
        sender.reply("❌ 请在群聊中使用此指令")
        return

    # 去掉指令前缀
    time_part = msg
    for prefix in ["设置报时", "报时时间"]:
        if time_part.startswith(prefix):
            time_part = time_part[len(prefix):].strip()
            break

    if not time_part:
        sender.reply("⏰ 请带上时间哦\n💡 示例：设置报时 8:00 / 设置报时 9:30 / 设置报时 20点")
        return

    time_str = parse_time(time_part)
    if not time_str:
        sender.reply("❌ 时间格式错误\n💡 示例：设置报时 8:00 / 设置报时 9:30 / 设置报时 20点")
        return

    groups = get_groups()
    groups = migrate_old_data(groups)
    existing = find_group(groups, chat_id)
    if not existing:
        sender.reply("❌ 本群未开启自动报时，请先发送「开启报时」")
        return

    times = existing.get("times", [])
    if time_str in times:
        sender.reply(f"⏰ 时间 {time_str} 已存在，无需重复添加")
        return

    times.append(time_str)
    times.sort()
    existing["times"] = times
    save_groups(groups)
    sender.reply(f"✅ 已添加报时时间 {time_str}\n⏰ 当前报时时间：{'、'.join(times)}")

def delete_time(msg):
    chat_id = sender.getChatID()
    user_id = sender.getUserID()
    if not chat_id or chat_id == user_id:
        sender.reply("❌ 请在群聊中使用此指令")
        return

    time_part = msg
    for prefix in ["删除报时", "取消报时"]:
        if time_part.startswith(prefix):
            time_part = time_part[len(prefix):].strip()
            break

    if not time_part:
        sender.reply("⏰ 请带上要删除的时间\n💡 示例：删除报时 8:00")
        return

    time_str = parse_time(time_part)
    if not time_str:
        sender.reply("❌ 时间格式错误\n💡 示例：删除报时 8:00")
        return

    groups = get_groups()
    groups = migrate_old_data(groups)
    existing = find_group(groups, chat_id)
    if not existing:
        sender.reply("❌ 本群未开启自动报时")
        return

    times = existing.get("times", [])
    if time_str not in times:
        sender.reply(f"❌ 时间 {time_str} 不在报时列表中\n⏰ 当前报时时间：{'、'.join(times)}")
        return

    times.remove(time_str)
    existing["times"] = times
    save_groups(groups)

    # 清理该时间的 last_notify
    try:
        middleware.bucketDel(BUCKET_NAME, f"last_{chat_id}_{time_str}")
    except:
        pass

    if not times:
        sender.reply(f"✅ 已删除时间 {time_str}\n⚠️ 报时列表已空，将恢复默认 08:00")
        existing["times"] = ["08:00"]
        save_groups(groups)
    else:
        sender.reply(f"✅ 已删除时间 {time_str}\n⏰ 当前报时时间：{'、'.join(times)}")

def show_settings():
    chat_id = sender.getChatID()
    user_id = sender.getUserID()
    if not chat_id or chat_id == user_id:
        sender.reply("❌ 请在群聊中使用此指令")
        return

    groups = get_groups()
    groups = migrate_old_data(groups)
    existing = find_group(groups, chat_id)
    if not existing:
        sender.reply("❌ 本群未开启自动报时\n💡 发送「开启报时」即可开启")
        return

    times = existing.get("times", ["08:00"])
    times_str = "、".join(times)

    # 获取每个时间的上次报时
    last_info = []
    for t in times:
        last = get_last_notify(chat_id, t)
        last_info.append(f"  {t}：{last if last else '暂无'}")

    sender.reply(f"""=====报时设置=====
📍 群ID：{chat_id}
⏰ 报时时间：{times_str}
📅 上次报时：
{'\n'.join(last_info)}
✅ 状态：已开启
==================
💡 指令列表：
「开启报时」- 开启自动报时
「关闭报时」- 关闭自动报时
「设置报时 8:00」- 添加报时时间
「删除报时 8:00」- 删除报时时间
「系统报时」- 手动报时一次""")

# ==================== 定时任务 ====================

def cron_task():
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")

    groups = get_groups()
    groups = migrate_old_data(groups)
    if not groups:
        return

    for g in groups:
        chat_id = g.get("chat_id")
        times = g.get("times", ["08:00"])
        g_imtype = g.get("imtype", "qq")
        if not chat_id:
            continue
        if current_time not in times:
            continue
        if get_last_notify(chat_id, current_time) == today_str:
            continue
        try:
            report = generate_time_report()
            middleware.push(g_imtype, chat_id, "", "", report)
            set_last_notify(chat_id, current_time, today_str)
        except Exception as e:
            print(f"[系统报时] 推送失败 {chat_id}: {e}")

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
    elif msg.startswith("删除报时") or msg.startswith("取消报时"):
        delete_time(msg)
    else:
        sender.setContinue()

if __name__ == "__main__":
    if imtype == 'fake':
        cron_task()
    else:
        main()

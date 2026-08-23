# [title: 系统报时]
# [icon: https://gcore.jsdelivr.net/gh/lhz03/img@0d28f1a9cc71d7269440d5f1eb40f40df08689da/2026/01/31/2a7606203ed51989a1bc2887c5a9489d.png]
# [language: python]
# [rule: ^(系统报时|报时|时间|几点了|现在几点|开启报时|关闭报时|报时设置|设置报时.*|报时时间.*)$]
# [disable: false]
# [open_source: true]
# [platform: qq,qb,wx,gw,sb,wb,tg,tb,qx,xy,ip]
# [priority: 9999999999999999999]
# [public: true]
# [version: 1.2.2]
# [price: 0]
# [author: 系统报时]
# [service: ]
# [cron: * * * * *]
# [description: 🦄 系统报时插件，支持手动报时 + 自动定时报时。指令：系统报时/开启报时/关闭报时/设置报时 8:00/报时设置]

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
ZODIAC_DATES = [(1,20),(2,19),(3,21),(4,20),(5,21),(6,21),(7,23),(8,23),(9,23),(10,23),(11,22),(12,22)]
ZODIAC_NAME = ["摩羯座","水瓶座","双鱼座","白羊座","金牛座","双子座",
               "巨蟹座","狮子座","处女座","天秤座","天蝎座","射手座"]

senderID = middleware.getSenderID()
sender = middleware.Sender(senderID)
imtype = sender.getImtype()

# ==================== 工具函数 ====================

def get_zodiac(month, day):
    for i, (m, d) in enumerate(ZODIAC_DATES):
        if (month == m and day >= d) or (month == m + 1 and day < ZODIAC_DATES[(i+1)%12][1]):
            if month == 12 and day >= 22:
                return ZODIAC_NAME[0]
            return ZODIAC_NAME[i]
    return ZODIAC_NAME[0]

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
    zodiac_sign = get_zodiac(m, d)
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
        f"♈ 星座：{zodiac_sign}",
        f"🌸 节气：{jie_qi}",
    ]

    if not is_today:
        lines.append(f"🍂 下个：{next_jq}（{next_m}月{next_d}日）")
    else:
        lines.append("✨ 今日节气，顺遂安康 ✨")

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━")
    # 每日一言
    try:
        yiyan_resp = requests.get("https://v.api.aa1.cn/api/yiyan/index.php", timeout=5)
        if yiyan_resp.status_code == 200:
            yiyan_match = re.search(r'<p>(.*?)</p>', yiyan_resp.text)
            if yiyan_match:
                lines.append("")
                lines.append(f"📖 每日一言：{yiyan_match.group(1)}")
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

def get_last_notify(chat_id):
    return middleware.bucketGet(BUCKET_NAME, f"last_{chat_id}") or ""

def set_last_notify(chat_id, date_str):
    middleware.bucketSet(BUCKET_NAME, f"last_{chat_id}", date_str)

def find_group(groups, chat_id):
    for g in groups:
        if g.get("chat_id") == chat_id:
            return g
    return None

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
    existing = find_group(groups, chat_id)
    if existing:
        sender.reply(f"✅ 本群已开启自动报时\n⏰ 当前时间：{existing.get('time','08:00')}\n💡 发送「设置报时 8:00」可修改时间")
        return

    groups.append({"chat_id": chat_id, "imtype": imtype, "time": "08:00"})
    save_groups(groups)
    sender.reply("✅ 已开启自动报时\n⏰ 默认每天 08:00 推送\n💡 发送「设置报时 9:00」可修改时间")

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
    try:
        middleware.bucketDel(BUCKET_NAME, f"last_{chat_id}")
    except:
        pass
    sender.reply("✅ 已关闭本群自动报时")

def set_time(msg):
    chat_id = sender.getChatID()
    user_id = sender.getUserID()
    if not chat_id or chat_id == user_id:
        sender.reply("❌ 请在群聊中使用此指令")
        return

    # 去掉指令前缀，只保留时间部分
    time_part = msg
    for prefix in ["设置报时", "报时时间"]:
        if time_part.startswith(prefix):
            time_part = time_part[len(prefix):].strip()
            break

    # 如果没输入时间
    if not time_part:
        sender.reply("⏰ 请带上时间哦\n💡 示例：设置报时 8:00 / 设置报时 9:30 / 设置报时 20点")
        return

    # 匹配时间格式：8:00 / 8：00 / 0800 / 8点 / 8点30 / 8点30分 / 8:30
    match = None
    patterns = [
        r'(\d{1,2})[:：\s](\d{2})',      # 8:00 / 8：00 / 8 00
        r'(\d{1,2})点(\d{1,2})分?',       # 8点 / 8点30 / 8点30分
        r'(\d{1,2})(\d{2})',             # 0800 / 830
        r'(\d{1,2})',                       # 8
    ]
    for pat in patterns:
        m = re.search(pat, time_part)
        if m:
            match = m
            break

    if not match:
        sender.reply("❌ 时间格式错误\n💡 示例：设置报时 8:00 / 设置报时 9:30 / 设置报时 20点")
        return

    hour = int(match.group(1))
    minute_str = match.group(2) if len(match.groups()) >= 2 else None
    minute = int(minute_str) if minute_str and minute_str.strip() else 0

    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        sender.reply("❌ 时间范围错误，小时 0-23，分钟 0-59")
        return

    time_str = f"{hour:02d}:{minute:02d}"
    groups = get_groups()
    existing = find_group(groups, chat_id)
    if not existing:
        sender.reply("❌ 本群未开启自动报时，请先发送「开启报时」")
        return

    existing["time"] = time_str
    save_groups(groups)
    sender.reply(f"✅ 报时时间已设置为每天 {time_str}")

def show_settings():
    chat_id = sender.getChatID()
    user_id = sender.getUserID()
    if not chat_id or chat_id == user_id:
        sender.reply("❌ 请在群聊中使用此指令")
        return

    groups = get_groups()
    existing = find_group(groups, chat_id)
    if not existing:
        sender.reply("❌ 本群未开启自动报时\n💡 发送「开启报时」即可开启")
        return

    time_setting = existing.get("time", "08:00")
    last = get_last_notify(chat_id)
    sender.reply(f"""=====报时设置=====
📍 群ID：{chat_id}
⏰ 报时时间：每天 {time_setting}
📅 上次报时：{last if last else "暂无"}
✅ 状态：已开启
==================
💡 指令列表：
「开启报时」- 开启自动报时
「关闭报时」- 关闭自动报时
「设置报时 8:00」- 修改报时时间
「系统报时」- 手动报时一次""")

# ==================== 定时任务 ====================

def cron_task():
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")

    groups = get_groups()
    if not groups:
        return

    for g in groups:
        chat_id = g.get("chat_id")
        set_time = g.get("time", "08:00")
        g_imtype = g.get("imtype", "qq")
        if not chat_id:
            continue
        if current_time != set_time:
            continue
        if get_last_notify(chat_id) == today_str:
            continue
        try:
            report = generate_time_report()
            middleware.push(g_imtype, chat_id, "", "", report)
            set_last_notify(chat_id, today_str)
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
    else:
        sender.setContinue()

if __name__ == "__main__":
    if imtype == 'fake':
        cron_task()
    else:
        main()

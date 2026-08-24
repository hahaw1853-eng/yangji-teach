# [title: 摸鱼日历]
# [icon: https://gcore.jsdelivr.net/gh/lhz03/img@0d28f1a9cc71d7269440d5f1eb40f40df08689da/2026/01/31/2a7606203ed51989a1bc2887c5a9489d.png]
# [language: python]
# [rule: ^(摸鱼日历|摸鱼|开启摸鱼|关闭摸鱼|摸鱼设置|设置摸鱼.*|删除摸鱼.*|取消摸鱼.*)$]
# [disable: false]
# [open_source: true]
# [platform: qq,qb,wx,gw,sb,wb,tg,tb,qx,xy,ip]
# [priority: 9999999999999999999]
# [public: true]
# [version: 1.0.1]
# [price: 0]
# [author: 摸鱼日历]
# [service: ]
# [cron: * * * * *]
# [description: 🐟 摸鱼日历插件，支持自定义时间自动推送摸鱼日历图片。指令：摸鱼日历/开启摸鱼/关闭摸鱼/设置摸鱼 9:00/删除摸鱼 9:00/摸鱼设置]

import json
import re
from datetime import datetime
import middleware

BUCKET_NAME = "moyu_calendar"
API_URL = "https://api.shanhe.kim/API/%E6%91%B8%E9%B1%BC%E6%97%A5%E5%8E%86.php?style=3&apikey=440082e19ecab4cc608aa18ffc68641e0cee4bd5a975b8b83dfb11130e64ed64"

senderID = middleware.getSenderID()
sender = middleware.Sender(senderID)
imtype = sender.getImtype()

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
    return middleware.bucketGet(BUCKET_NAME, f"last_{chat_id}_{time_str}") or ""

def set_last_notify(chat_id, time_str, date_str):
    middleware.bucketSet(BUCKET_NAME, f"last_{chat_id}_{time_str}", date_str)

def find_group(groups, chat_id):
    for g in groups:
        if g.get("chat_id") == chat_id:
            return g
    return None

def migrate_old_data(groups):
    changed = False
    for g in groups:
        if "time" in g and isinstance(g["time"], str):
            g["times"] = [g["time"]]
            del g["time"]
            changed = True
        elif "times" not in g:
            g["times"] = ["09:00"]
            changed = True
    if changed:
        save_groups(groups)
    return groups

# ==================== 核心功能 ====================

def get_image_cq():
    """获取图片CQ码，直接用URL发送"""
    return f"[CQ:image,file={API_URL}]"

def send_calendar():
    """发送摸鱼日历"""
    sender.reply(get_image_cq())

# ==================== 指令处理 ====================

def manual_send():
    send_calendar()

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
        times = existing.get("times", ["09:00"])
        times_str = "、".join(times)
        sender.reply(f"✅ 本群已开启摸鱼日历\n⏰ 当前时间：{times_str}\n💡 发送「设置摸鱼 9:00」可添加时间")
        return

    groups.append({"chat_id": chat_id, "imtype": imtype, "times": ["09:00"]})
    save_groups(groups)
    sender.reply("✅ 已开启摸鱼日历\n⏰ 默认每天 09:00 推送\n💡 发送「设置摸鱼 14:00」可添加更多时间")

def disable_auto():
    chat_id = sender.getChatID()
    user_id = sender.getUserID()
    if not chat_id or chat_id == user_id:
        sender.reply("❌ 请在群聊中使用此指令")
        return

    groups = get_groups()
    new_groups = [g for g in groups if g.get("chat_id") != chat_id]
    if len(new_groups) == len(groups):
        sender.reply("❌ 本群未开启摸鱼日历")
        return

    save_groups(new_groups)
    try:
        keys = middleware.bucketKeys(BUCKET_NAME)
        for k in keys:
            if k.startswith(f"last_{chat_id}_"):
                middleware.bucketDel(BUCKET_NAME, k)
    except:
        pass
    sender.reply("✅ 已关闭本群摸鱼日历")

def parse_time(time_part):
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

    time_part = msg
    for prefix in ["设置摸鱼", "摸鱼时间"]:
        if time_part.startswith(prefix):
            time_part = time_part[len(prefix):].strip()
            break

    if not time_part:
        sender.reply("⏰ 请带上时间哦\n💡 示例：设置摸鱼 9:00 / 设置摸鱼 14:00 / 设置摸鱼 9点30")
        return

    time_str = parse_time(time_part)
    if not time_str:
        sender.reply("❌ 时间格式错误\n💡 示例：设置摸鱼 9:00 / 设置摸鱼 14:00 / 设置摸鱼 9点30")
        return

    groups = get_groups()
    groups = migrate_old_data(groups)
    existing = find_group(groups, chat_id)
    if not existing:
        sender.reply("❌ 本群未开启摸鱼日历，请先发送「开启摸鱼」")
        return

    times = existing.get("times", [])
    if time_str in times:
        sender.reply(f"⏰ 时间 {time_str} 已存在")
        return

    times.append(time_str)
    times.sort()
    existing["times"] = times
    save_groups(groups)
    sender.reply(f"✅ 已添加摸鱼时间 {time_str}\n⏰ 当前摸鱼时间：{'、'.join(times)}")

def delete_time(msg):
    chat_id = sender.getChatID()
    user_id = sender.getUserID()
    if not chat_id or chat_id == user_id:
        sender.reply("❌ 请在群聊中使用此指令")
        return

    time_part = msg
    for prefix in ["删除摸鱼", "取消摸鱼"]:
        if time_part.startswith(prefix):
            time_part = time_part[len(prefix):].strip()
            break

    if not time_part:
        sender.reply("⏰ 请带上要删除的时间\n💡 示例：删除摸鱼 9:00")
        return

    time_str = parse_time(time_part)
    if not time_str:
        sender.reply("❌ 时间格式错误\n💡 示例：删除摸鱼 9:00")
        return

    groups = get_groups()
    groups = migrate_old_data(groups)
    existing = find_group(groups, chat_id)
    if not existing:
        sender.reply("❌ 本群未开启摸鱼日历")
        return

    times = existing.get("times", [])
    if time_str not in times:
        sender.reply(f"❌ 时间 {time_str} 不在列表中\n⏰ 当前摸鱼时间：{'、'.join(times)}")
        return

    times.remove(time_str)
    existing["times"] = times
    save_groups(groups)

    try:
        middleware.bucketDel(BUCKET_NAME, f"last_{chat_id}_{time_str}")
    except:
        pass

    if not times:
        sender.reply(f"✅ 已删除时间 {time_str}\n⚠️ 列表已空，恢复默认 09:00")
        existing["times"] = ["09:00"]
        save_groups(groups)
    else:
        sender.reply(f"✅ 已删除时间 {time_str}\n⏰ 当前摸鱼时间：{'、'.join(times)}")

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
        sender.reply("❌ 本群未开启摸鱼日历\n💡 发送「开启摸鱼」即可开启")
        return

    times = existing.get("times", ["09:00"])
    times_str = "、".join(times)
    last_info = []
    for t in times:
        last = get_last_notify(chat_id, t)
        last_info.append(f"  {t}：{last if last else '暂无'}")

    sender.reply(f"""=====摸鱼设置=====
📍 群ID：{chat_id}
⏰ 推送时间：{times_str}
📅 上次推送：
{'\n'.join(last_info)}
✅ 状态：已开启
==================
💡 指令列表：
「开启摸鱼」- 开启自动推送
「关闭摸鱼」- 关闭自动推送
「设置摸鱼 9:00」- 添加推送时间
「删除摸鱼 9:00」- 删除推送时间
「摸鱼日历」- 手动发送一次""")

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
        times = g.get("times", ["09:00"])
        g_imtype = g.get("imtype", "qq")
        if not chat_id:
            continue
        if current_time not in times:
            continue
        if get_last_notify(chat_id, current_time) == today_str:
            continue
        try:
            cq = f"[CQ:image,file={API_URL}]"
            middleware.push(g_imtype, chat_id, "", "", cq)
            set_last_notify(chat_id, current_time, today_str)
        except Exception as e:
            print(f"[摸鱼日历] 推送失败 {chat_id}: {e}")

# ==================== 主入口 ====================

def main():
    msg = sender.getMessage().strip()

    if msg in ["摸鱼日历", "摸鱼"]:
        manual_send()
    elif msg == "开启摸鱼":
        enable_auto()
    elif msg == "关闭摸鱼":
        disable_auto()
    elif msg == "摸鱼设置":
        show_settings()
    elif msg.startswith("设置摸鱼") or msg.startswith("摸鱼时间"):
        set_time(msg)
    elif msg.startswith("删除摸鱼") or msg.startswith("取消摸鱼"):
        delete_time(msg)
    else:
        sender.setContinue()

if __name__ == "__main__":
    if imtype == 'fake':
        cron_task()
    else:
        main()

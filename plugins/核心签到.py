#[pin:false]
#[public:true]
#[disable:false]
# [rule: ^(签到|系统管理|积分查询|查询积分|兑换酷我次数|兑换次数|DD_.*|卡密:DD_.*)$]
# [cron: 0 0 0 * * *]
# [platform: qq,qb,wx,tb,tg,web,wxmp]
# [author: rujingxianghai]
# [title: 积分签到系统]
# [class: 工具类]
# [version: 6.2]
# [price: 0]
# [description: 签到获取积分,支持连续签到奖励,可兑换酷我提现次数。命令:签到丨积分查询丨兑换酷我次数丨系统管理(管理员)]
# [param: {"required":true,"key":"dd_sign_config.sign","bool":true,"placeholder":"","name":"签到功能","desc":"勾选可签到，默认关闭，需要先关闭奥特曼自带的签到功能！(用户系统里面)"}]
# [param: {"required":true,"key":"dd_sign_config.signcoin","bool":false,"placeholder":"默认:1-5 填写例:1-5","name":"积分区间","desc":"用户每次签到的积分区间"}]
# [param: {"required":true,"key":"dd_sign_config.kuwo_rate","bool":false,"placeholder":"默认:500 填写例:500","name":"酷我兑换比例","desc":"多少积分兑换1次酷我提现次数"}]

from datetime import datetime, timedelta
import random
import middleware
import time
import json
import re

# Sender info
senderID = middleware.getSenderID()
sender = middleware.Sender(senderID)
userid = sender.getUserID()
imtype = sender.getImtype()
username = sender.getUserName()

# Bucket definitions
CONFIG_BUCKET = 'dd_sign_config'
SIGN_DATE_BUCKET = 'dd_sign_dates'
POINTS_BUCKET = 'dd_sign_points'
CARD_BUCKET = 'dd_sign_cards'
STREAK_BUCKET = 'dd_sign_streak'

# Sign config
signswitch = middleware.bucketGet(bucket=CONFIG_BUCKET, key='sign') or 'false'
signcoin = middleware.bucketGet(bucket=CONFIG_BUCKET, key='signcoin') or '1-5'
kuwo_rate = middleware.bucketGet(bucket=CONFIG_BUCKET, key='kuwo_rate') or '1'

# Plugin configs (dynamic)
PLUGIN_CONFIGS = {}

# ==================== Points Functions ====================

def get_user_points(uid):
    """Get user points"""
    return int(middleware.bucketGet(POINTS_BUCKET, uid) or 0)


def add_user_points(uid, points, channel="", name=""):
    """Add points to user"""
    current = int(middleware.bucketGet(POINTS_BUCKET, uid) or 0)
    middleware.bucketSet(POINTS_BUCKET, uid, str(current + points))
    return get_user_points(uid)


def deduct_user_points(uid, points, channel="", name=""):
    """Deduct points from user"""
    current = int(middleware.bucketGet(POINTS_BUCKET, uid) or 0)
    if current < points:
        return False
    middleware.bucketSet(POINTS_BUCKET, uid, str(current - points))
    return True


# ==================== Sign Function ====================

def sign():
    """Daily sign-in with streak bonus"""
    today = str(datetime.now().date())
    yesterday = str((datetime.now() - timedelta(days=1)).date())

    lock_key = f'sign_lock_{userid}'
    if middleware.bucketGet(CONFIG_BUCKET, lock_key):
        sender.reply('操作太频繁，请稍后再试~')
        return

    try:
        middleware.bucketSet(CONFIG_BUCKET, lock_key, '1')

        last_sign = middleware.bucketGet(SIGN_DATE_BUCKET, userid)
        if last_sign == today:
            sender.reply('你好,你今日已经签到过了哦~')
            return

        # 计算连续签到
        streak = int(middleware.bucketGet(STREAK_BUCKET, userid) or 0)
        if last_sign == yesterday:
            streak += 1
        else:
            streak = 1

        min_coin, max_coin = map(int, signcoin.split('-'))
        base_coins = random.randint(min_coin, max_coin)

        # 连续签到奖励
        extra_coins = 0
        if streak >= 30:
            extra_coins = 10
        elif streak >= 7:
            extra_coins = 5
        elif streak >= 3:
            extra_coins = 2

        total_coins = base_coins + extra_coins

        current_coins = add_user_points(userid, total_coins, "签到", username)
        middleware.bucketSet(SIGN_DATE_BUCKET, userid, today)
        middleware.bucketSet(STREAK_BUCKET, userid, str(streak))

        bonus_msg = ""
        if extra_coins > 0:
            bonus_msg = f" (含连续{streak}天奖励+{extra_coins})"

        msg = f"""•你好,{username}
•签到成功,获得{total_coins}🌸{bonus_msg}
•连续签到: {streak}天
•当前积分: {current_coins}🌸
•你可通过以下操作获取🌸
① 【签到】每日签到领积分
② 【积分查询】查看可兑换服务
③ 【兑换酷我次数】用积分换提现次数"""
        sender.reply(msg)

    except Exception as e:
        sender.reply(f'签到失败:{str(e)}')
    finally:
        middleware.bucketDel(CONFIG_BUCKET, lock_key)


# ==================== Query & Use Points ====================

def query_points():
    """Query points"""
    streak = int(middleware.bucketGet(STREAK_BUCKET, userid) or 0)
    msg = f"""=====积分查询=====
💰 总积分: {get_user_points(userid)}
🔥 连续签到: {streak}天

🎯 可用插件及积分:"""

    for plugin_id, config in PLUGIN_CONFIGS.items():
        try:
            coin_value = middleware.bucketGet(config['bucket'], config['coin_key'])
            if coin_value and coin_value != '0':
                msg += f"\n• {config['name']}: {coin_value}积分/月"
        except:
            continue

    msg += """
==================
💡 发送"兑换酷我次数"可换提现次数"""
    sender.reply(msg)


def use_points(plugin_id, points):
    """Use points for plugin"""
    if plugin_id not in PLUGIN_CONFIGS:
        return False, "插件不存在"

    current = get_user_points(userid)
    if current < points:
        return False, f"积分不足\n当前积分:{current}\n需要积分:{points}"

    try:
        success = deduct_user_points(userid, points, PLUGIN_CONFIGS[plugin_id]['name'], username)
        if success:
            return True, f"扣除{points}积分成功\n当前积分:{get_user_points(userid)}"
        return False, "扣除积分失败"
    except:
        return False, "扣除积分失败"


# ==================== Exchange Kuwo Count ====================

def exchange_kuwo():
    """用积分兑换酷我提现次数"""
    try:
        rate = int(kuwo_rate)
        if rate <= 0:
            rate = 500
    except:
        rate = 500

    current_points = get_user_points(userid)
    current_count = int(middleware.bucketGet('dd_KuwoTX_UserCount', userid) or 0)

    msg = f"""=====兑换酷我提现次数=====
💰 当前积分: {current_points}
🔢 当前次数: {current_count}次
📊 兑换比例: {rate}积分 = 1次

请输入要兑换的次数(输入q取消):"""
    sender.reply(msg)

    count_input = sender.input(60000, 1, False)
    if not count_input or count_input.lower() == 'q':
        sender.reply('已取消兑换')
        return

    try:
        count = int(count_input)
        if count <= 0:
            sender.reply('兑换次数必须大于0')
            return

        need_points = count * rate

        if current_points < need_points:
            sender.reply(
                f"=====积分不足=====\n"
                f"💰 当前积分: {current_points}\n"
                f"💵 需要积分: {need_points}\n"
                f"🔢 兑换次数: {count}次\n"
                f"==================="
            )
            return

        # 确认兑换
        sender.reply(
            f"=====确认兑换=====\n"
            f"🔢 兑换次数: {count}次\n"
            f"💵 消耗积分: {need_points}\n"
            f"💰 剩余积分: {current_points - need_points}\n"
            f"是否确认?\n[y]确认 | [n]取消"
        )

        confirm = sender.input(30000, 1, False)
        if not confirm or confirm.lower() != 'y':
            sender.reply('已取消兑换')
            return

        # 扣积分
        success = deduct_user_points(userid, need_points, "兑换酷我次数", username)
        if not success:
            sender.reply('积分扣减失败，请重试')
            return

        # 加次数
        new_count = current_count + count
        middleware.bucketSet('dd_KuwoTX_UserCount', userid, str(new_count))

        sender.reply(
            f"=====兑换成功=====\n"
            f"🔢 获得次数: {count}次\n"
            f"💵 消耗积分: {need_points}\n"
            f"💰 剩余积分: {get_user_points(userid)}\n"
            f"🔢 当前总次数: {new_count}次\n"
            f"==================="
        )

    except ValueError:
        sender.reply('请输入有效的数字')


# ==================== Card Functions ====================

def generate_card(amount):
    """Generate card"""
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    card = 'DD_' + ''.join(random.choice(chars) for _ in range(12))
    middleware.bucketSet(CARD_BUCKET, card, str(amount))
    return card


def use_card(card):
    """Use card"""
    try:
        card_match = re.search(r'(?:卡密:)?(DD_[A-Z0-9]{12})', card)
        if not card_match:
            return False, '卡密格式错误!'

        card = card_match.group(1)
        amount = middleware.bucketGet(CARD_BUCKET, card)

        if not amount:
            return False, '卡密不存在!'
        if amount == 'False':
            return False, '卡密已被使用!'

        try:
            amount = int(amount)
        except ValueError:
            try:
                card_info = json.loads(amount)
                return False, f'卡密已被{card_info["user"]}使用\n使用时间:{card_info["time"]}'
            except:
                return False, '卡密数据格式错误!'

        if amount <= 0:
            return False, '卡密面额错误!'

        current = add_user_points(userid, amount, "卡密充值", username)

        use_info = {
            'user': userid,
            'username': username,
            'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'amount': amount
        }
        middleware.bucketSet(CARD_BUCKET, card, json.dumps(use_info))
        return True, f'充值成功!\n获得积分:{amount}\n当前积分:{current}'

    except Exception as e:
        return False, f'充值失败: {str(e)}'


# ==================== Admin System ====================

def system():
    """System management"""
    if not sender.isAdmin():
        sender.reply('您没有权限!')
        return

    msg = """========系统管理========
1、生成卡密
2、查看卡密
3、删除卡密
4、积分管理
5、服务积分设置
======================
回复序号,退出【q】！"""

    sender.reply(msg)
    choice = sender.input(120000, 1, False)

    if choice == 'q':
        sender.reply('已退出')
        return

    if choice == '1':
        msg = """请选择生成方式:
1、单张生成
2、批量生成
=============
回复序号,退出【q】！"""
        sender.reply(msg)
        subchoice = sender.input(120000, 1, False)

        if subchoice == 'q':
            return

        if subchoice == '1':
            sender.reply('请输入卡密面额(积分):')
            amount = sender.input(120000, 1, False)
            try:
                amount = int(amount)
                if amount <= 0:
                    sender.reply('面额必须大于0')
                    return
                card = generate_card(amount)
                sender.reply(f'生成成功!\n卡密:{card}\n面额:{amount}积分')
            except:
                sender.reply('面额必须是数字!')

        elif subchoice == '2':
            sender.reply('请输入卡密面额(积分):')
            amount = sender.input(120000, 1, False)
            try:
                amount = int(amount)
                if amount <= 0:
                    sender.reply('面额必须大于0')
                    return

                sender.reply('请输入生成数量:')
                count = sender.input(120000, 1, False)
                try:
                    count = int(count)
                    if count <= 0 or count > 100:
                        sender.reply('数量必须在1-100之间')
                        return

                    cards = []
                    for _ in range(count):
                        card = generate_card(amount)
                        cards.append(card)

                    msg = f'批量生成成功!\n面额:{amount}积分\n数量:{count}张\n\n卡密列表:\n'
                    msg += '\n'.join(cards)
                    sender.reply(msg)
                except:
                    sender.reply('数量必须是数字!')
            except:
                sender.reply('面额必须是数字!')
        else:
            sender.reply('输入错误!')

    elif choice == '2':
        cards = middleware.bucketAllKeys(CARD_BUCKET)
        if not cards:
            sender.reply('暂无卡密!')
            return

        msg = '========卡密列表========\n'
        for card in cards:
            if not card.startswith('DD_'):
                continue
            card_data = middleware.bucketGet(CARD_BUCKET, card)
            try:
                use_info = json.loads(card_data)
                if isinstance(use_info, dict):
                    msg += f'卡密:{card}\n状态:已被{use_info["user"]}使用\n使用时间:{use_info["time"]}\n面额:{use_info["amount"]}积分\n\n'
                else:
                    msg += f'卡密:{card}\n面额:{card_data}积分\n状态:未使用\n\n'
            except:
                if card_data != 'False':
                    msg += f'卡密:{card}\n面额:{card_data}积分\n状态:未使用\n\n'
        msg += '======================'
        sender.reply(msg)

    elif choice == '3':
        sender.reply('请输入要删除的卡密:')
        card = sender.input(120000, 1, False)
        if middleware.bucketDel(CARD_BUCKET, card):
            sender.reply('删除成功!')
        else:
            sender.reply('卡密不存在!')

    elif choice == '4':
        msg = """========积分管理========
1、查询用户积分
2、修改用户积分
3、批量发放积分
======================
回复序号,退出【q】！"""
        sender.reply(msg)
        subchoice = sender.input(120000, 1, False)

        if subchoice == '1':
            query_points()

        elif subchoice == '2':
            sender.reply('请输入用户ID:')
            user_id = sender.input(120000, 1, False)
            sender.reply('请输入积分数量(负数表示扣除):')
            amount = sender.input(120000, 1, False)
            try:
                amount = int(amount)
                current = get_user_points(user_id)
                if amount < 0 and abs(amount) > current:
                    sender.reply('积分不足!')
                    return
                add_user_points(user_id, amount)
                sender.reply(f'修改成功!当前积分:{get_user_points(user_id)}')
            except:
                sender.reply('输入错误!')

        elif subchoice == '3':
            sender.reply('请输入积分数量:')
            amount = sender.input(120000, 1, False)
            try:
                amount = int(amount)
                if amount <= 0:
                    sender.reply('数量必须大于0')
                    return

                sender.reply('请输入用户ID列表(用逗号分隔):')
                users = sender.input(120000, 1, False).split(',')
                success = 0
                for user_id in users:
                    user_id = user_id.strip()
                    if user_id:
                        add_user_points(user_id, amount)
                        success += 1
                sender.reply(f'批量发放完成!\n成功:{success}\n失败:{len(users)-success}')
            except:
                sender.reply('输入错误!')

    elif choice == '5':
        msg = """========服务积分设置========
当前支持的服务:"""

        service_list = []
        for idx, (service_id, config) in enumerate(PLUGIN_CONFIGS.items(), 1):
            service_list.append((str(idx), service_id, config['name']))
            msg += f"\n{idx}、{config['name']}"

        msg += """
======================
操作选项:
a、新增服务
d、删除服务
或输入序号修改积分
退出请输入【q】"""
        sender.reply(msg)

        service_map = {str(idx): service_id for idx, service_id, _ in service_list}

        subchoice = sender.input(120000, 1, False)
        if subchoice == 'q':
            return

        if subchoice == 'a':
            sender.reply("""请按以下格式输入:
插件名[,显示名称]
示例: kuwo,酷我音乐
如只输入插件名，显示名称默认与插件名相同
======================""")

            service_info = sender.input(120000, 1, False)
            try:
                parts = [x.strip() for x in service_info.split(',')]
                if len(parts) == 1:
                    plugin_id = parts[0]
                    name = plugin_id
                elif len(parts) == 2:
                    plugin_id, name = parts
                else:
                    sender.reply('格式错误!最多两个字段')
                    return

                if not plugin_id:
                    sender.reply('插件名不能为空!')
                    return

                if plugin_id in PLUGIN_CONFIGS:
                    sender.reply(f'插件 [{plugin_id}] 已存在!')
                    return

                bucket = f"dd_{plugin_id}"
                coin_key = "coin"

                new_config = {
                    'bucket': bucket,
                    'coin_key': coin_key,
                    'name': name
                }

                custom_plugins = json.loads(middleware.bucketGet('dd_sign_config', 'custom_plugins') or '{}')
                custom_plugins[plugin_id] = new_config
                middleware.bucketSet('dd_sign_config', 'custom_plugins', json.dumps(custom_plugins))

                PLUGIN_CONFIGS[plugin_id] = new_config
                sender.reply(f'成功添加服务: {name}\n存储桶: {bucket}\n积分键: {coin_key}')

            except Exception as e:
                sender.reply(f'添加失败: {str(e)}')
                return

        elif subchoice == 'd':
            sender.reply('请输入要删除的服务序号:')
            del_idx = sender.input(120000, 1, False)

            if del_idx not in service_map:
                sender.reply('序号无效!')
                return

            service_id = service_map[del_idx]
            service_name = PLUGIN_CONFIGS[service_id]['name']

            custom_plugins = json.loads(middleware.bucketGet('dd_sign_config', 'custom_plugins') or '{}')
            if service_id in custom_plugins:
                del custom_plugins[service_id]
                middleware.bucketSet('dd_sign_config', 'custom_plugins', json.dumps(custom_plugins))
                del PLUGIN_CONFIGS[service_id]
                sender.reply(f'成功删除服务: {service_name}')
            else:
                sender.reply('该服务为系统内置,无法删除!')

        elif subchoice in service_map:
            service = service_map[subchoice]
            config = PLUGIN_CONFIGS[service]

            current = middleware.bucketGet(config['bucket'], config['coin_key']) or '未设置'
            sender.reply(f'当前{config["name"]}需要积分: {current}\n请输入新的积分数量:')

            new_coins = sender.input(120000, 1, False)
            try:
                new_coins = int(new_coins)
                if new_coins <= 0:
                    sender.reply('积分必须大于0')
                    return
                middleware.bucketSet(config['bucket'], config['coin_key'], str(new_coins))
                sender.reply(f'设置成功!\n{config["name"]}现在需要{new_coins}积分')
            except:
                sender.reply('输入错误!')
        else:
            sender.reply('输入错误!')

    else:
        sender.reply('输入错误!')


# ==================== Init Custom Plugins ====================

try:
    custom_plugins = json.loads(middleware.bucketGet('dd_sign_config', 'custom_plugins') or '{}')
    PLUGIN_CONFIGS.update(custom_plugins)
except:
    pass


# ==================== Main Logic ====================

message = sender.getMessage()

if message == '签到' and signswitch == 'true':
    sign()

elif message == '系统管理':
    system()

elif message in ('积分查询', '查询积分'):
    query_points()

elif message in ('兑换酷我次数', '兑换次数'):
    exchange_kuwo()

elif 'DD_' in message:
    success, msg = use_card(message)
    sender.reply(msg)

elif imtype == 'fake':
    for key in middleware.bucketAllKeys('dd_state'):
        middleware.bucketDel('dd_state', key)

else:
    sender.setContinue()

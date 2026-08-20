#[title: 无优计划]
#[language: python]
#[class: 工具类]
#[author: ranminmo]
#[service: 2993959969] 售后联系方式
#[disable: false] 禁用开关，true表示禁用，false表示可用
#[admin: false] 是否为管理员指令
#[rule: ^无优登录$|^登录无优$|^无优查询$|^无优管理$|^无优提现$|^无优授权$|^无优检测$|^无优教程$] 匹配规则，多个规则时向下依次写多个
#[cron: 10 7 * * *] cron定时，支持5位域和6位域
#[priority: 0] 优先级，数字越大表示优先级越高
#[platform: qq,qb,wx,tb,tg,web,wxmp] 适用的平台
#[open_source: false]是否开源
#[icon: https://img-cf.885666.xyz/5967b00a7a39fba673de40a4c9e89c78.jpg]图标链接地址，请使用48像素的正方形图标，支持http和https
#[version: 1.0]版本号
#[public: true] 是否发布？值为true或false，不设置则上传aut云时会自动设置为true，false时上传后不显示在市场中，但是搜索能搜索到，方便开发者测试
#[price: 8.88] 上架价格
#[description: 刷视频领金币，需实名<br>账号密码登录，需要手动登录app绑定账号，进入活动页面一次。脚本群内获取<br>1.0：首发版本，自动签到+看广告+领取任务奖励]

# 插件参数配置
# [param: {"required":false,"key":"s_wuyou.zsm","bool":false,"placeholder":"非必填项,http://xxxx.co/xxx.jpg","name":"收款方式","desc":"微信赞赏码/收款码链接"}]
# [param: {"required":false,"key":"s_wuyou.price","bool":false,"placeholder":"例:0.88,不填为0元","name":"上车价格","desc":"授权价格(单位:元)/月"}]
# [param: {"required":false,"key":"s_wuyou.coin","bool":false,"placeholder":"不填为关闭积分授权","name":"积分开通","desc":"授权一个月需要多少积分"}]
# [param: {"required":false,"key":"s_wuyou.ql_config","bool":false,"placeholder":"格式:http://qinglong地址|ClientID|ClientSecret","name":"青龙配置","desc":"青龙面板配置信息，用|分隔"}]
# [param: {"required":false,"key":"s_wuyou.ql_envname","bool":false,"placeholder":"例:S_WUYOU","name":"青龙变量名","desc":"推送到青龙的变量名称"}]
# [param: {"required":false,"key":"s_wuyou.user_agent","bool":false,"placeholder":"Mozilla/5.0 (Linux; Android 16; ...","name":"User-Agent","desc":"Android WebView UA，建议填真机抓包到的UA保持一致"}]
# [param: {"required":false,"key":"s_wuyou.proxy_api","bool":false,"placeholder":"http://api.example.com/getip","name":"代理API","desc":"代理提取API地址，可选"}]
# [param: {"required":false,"key":"s_wuyou.ma_pay_switch","bool":true,"placeholder":"","name":"码支付功能","desc":"开启后使用码支付"}]
# [param: {"required":false,"key":"s_wuyou.notify","bool":false,"placeholder":"qq,wx,tb","name":"通知渠道","desc":"检测通知推送渠道"}]
# [param: {"required":false,"key":"s_wuyou.notify_days","bool":false,"placeholder":"3","name":"提前提醒天数","desc":"到期前多少天开始提醒"}]

import json
import requests
import re
import time
import random
import string
import middleware
import hashlib
import hmac
import base64
import secrets
import os
from datetime import datetime, timedelta
from decimal import Decimal
from urllib.parse import urlsplit

# 禁用SSL警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== 数据桶名称配置 ====================
BUCKET_USER = 's_wuyou_user'      # 用户账号列表
BUCKET_TOKEN = 's_wuyou_token'    # 用户Token信息
BUCKET_AUTH = 's_wuyou_auth'      # 授权信息
BUCKET_CONFIG = 's_wuyou'         # 插件配置
BUCKET_DEVICE = 's_wuyou_device'  # device_id 持久化

# 码支付相关配置
PAY_TYPE_NAMES = {'alipay': '支付宝', 'wxpay': '微信支付', 'qqpay': 'QQ钱包'}
PLUGIN_NAME = '无优计划'

# ==================== 无优计划 API 常量（来自 APK 逆向） ====================
API_BASE = "https://api.dgccvi.com/api/app"
ADS_BASE = "https://ads.dgccvi.com/api/app"
APP_VERSION = "1.0.9"

LOGIN_URL = f"{API_BASE}/auth/login"
ATTEST_URL = f"{API_BASE}/attest"
ME_URL = f"{API_BASE}/me"
DAILY_TASKS_URL = f"{API_BASE}/daily-tasks"
CHECKIN_URL = f"{API_BASE}/checkin"
USER_DEVICES_URL = f"{API_BASE}/user-devices"

ADS_LIST_URL = f"{ADS_BASE}/alliance-ads"
ADS_SESSION_START_URL = f"{ADS_BASE}/alliance-ads/session/start"
ADS_HEARTBEAT_URL = f"{ADS_BASE}/alliance-ads/session/heartbeat"
ADS_COMPLETE_URL = f"{ADS_BASE}/alliance-ads/session/complete"

# 逆向自 AppAttestManager.signAttest 的 HMAC 密钥
ATTEST_KEY = "aac0ab40d0612c8549f88e87e476751a348f910156e9e73590ddaece2a4288d5"

DEFAULT_UA = "Mozilla/5.0 (Linux; Android 16; PJF110 Build/BP2A.250605.031; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/148.0.7444.102 Mobile Safari/537.36 XWEB/1480473 MMWEBSDK/20250201 MMWEBID/9172 MicroMessenger/8.0.57.2820(0x28003939) WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64"

# 获取发送者信息
senderID = middleware.getSenderID()
sender = middleware.Sender(senderID)
userid = sender.getUserID()


# ==================== 工具函数 ====================

def hmac_hex(key, msg):
    return hmac.new(key.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def compact_json(payload):
    """与前端 JSON.stringify 一致的紧凑序列化（不转义中文）"""
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def gen_device_id():
    """复刻前端 deviceId 模块"""
    rand = "".join(random.choice(string.digits + string.ascii_lowercase) for _ in range(10))
    return f"{int(time.time() * 1000)}-{rand}"


# ==================== 配置获取 ====================

def get_config():
    """获取插件配置"""
    price = Decimal(middleware.bucketGet(BUCKET_CONFIG, 'price') or '0')
    coin_price = middleware.bucketGet(BUCKET_CONFIG, 'coin') or ''
    zsm = middleware.bucketGet(BUCKET_CONFIG, 'zsm') or ''
    ql_config = middleware.bucketGet(BUCKET_CONFIG, 'ql_config') or ''
    ql_envname = middleware.bucketGet(BUCKET_CONFIG, 'ql_envname') or 'S_WUYOU'
    user_agent = middleware.bucketGet(BUCKET_CONFIG, 'user_agent') or DEFAULT_UA
    proxy_api = middleware.bucketGet(BUCKET_CONFIG, 'proxy_api') or ''

    return price, coin_price, zsm, ql_config, ql_envname, user_agent, proxy_api


# ==================== 授权相关函数 ====================

def calculate_auth_time(uid, months):
    """计算授权时间"""
    try:
        current_auth = middleware.bucketGet(BUCKET_AUTH, uid)
        if current_auth and datetime.strptime(current_auth, "%Y-%m-%d").date() > datetime.now().date():
            base_date = datetime.strptime(current_auth, "%Y-%m-%d").date()
        else:
            base_date = datetime.now().date()
        new_date = base_date + timedelta(days=30 * int(months))
        return str(new_date)
    except Exception as e:
        raise Exception(f"计算授权时间失败: {str(e)}")


def calculate_auth_time_by_days(uid, days):
    """按天数计算授权时间"""
    try:
        current_auth = middleware.bucketGet(BUCKET_AUTH, uid)
        if current_auth and datetime.strptime(current_auth, "%Y-%m-%d").date() > datetime.now().date():
            base_date = datetime.strptime(current_auth, "%Y-%m-%d").date()
        else:
            base_date = datetime.now().date()
        new_date = base_date + timedelta(days=int(days))
        return str(new_date)
    except Exception as e:
        raise Exception(f"计算授权时间失败: {str(e)}")


def set_auth_success(uid, months, total_price):
    """设置授权成功并显示成功信息"""
    try:
        token_info_str = middleware.bucketGet(BUCKET_TOKEN, uid)
        if not token_info_str:
            sender.reply(f"❌ 未找到账号 {uid} 的Token信息")
            return False
        token_info = json.loads(token_info_str)
        alias = token_info.get("alias", "未知用户")

        auth_time = calculate_auth_time(uid, months)
        middleware.bucketSet(BUCKET_AUTH, uid, auth_time)

        _, _, _, ql_config, ql_envname, _, _ = get_config()
        ql_result = False
        if ql_config:
            ql_result, ql_message = add_to_qinglong(uid, token_info, ql_envname)

        sender.reply(f"""
=====授权成功=====
👤 用户: {alias}
📱 UID: {uid}
💰 支付: {total_price}元
📅 有效期至: {auth_time}
------------------
🔄 青龙同步: {'成功' if ql_result else '失败'}
==================""")
        return True
    except Exception as e:
        sender.reply(f"❌ 设置授权失败: {str(e)}")
        return False


def generate_iframe_url(url):
    """将URL通过base64编码生成iframe页面链接"""
    try:
        encoded = base64.b64encode(url.encode('utf-8')).decode('utf-8')
        return f"https://metwhale.github.io?u={encoded}"
    except Exception:
        return url


def generate_qrcode(url):
    """生成二维码图片"""
    QRCODE_API_URL = "https://qrcode.vorto.cn/api/qrcode/generate"
    QRCODE_API_KEY = "4jpC3Cgd0zA7Z3HTJ6aDfW9QjtzitDGI"
    try:
        response = requests.post(
            QRCODE_API_URL, json={"content": url},
            headers={"X-API-Key": QRCODE_API_KEY}, timeout=10
        )
        if response.status_code == 200:
            result = response.json()
            if result.get('success') and result.get('data', {}).get('url'):
                return result['data']['url']
    except Exception as e:
        print(f"主接口生成二维码失败: {str(e)}")
    try:
        encoded_url = requests.utils.quote(url)
        return f"https://api.qrtool.cn/?text={encoded_url}&size=300&level=M"
    except Exception:
        return None


def handle_mapay_order(project, months, money, pay_type=None):
    """处理码支付订单"""
    config = {
        'gateway': middleware.bucketGet('dd_sign_config', 'ma_pay_gateway') or '',
        'pid': middleware.bucketGet('dd_sign_config', 'ma_pay_pid') or '',
        'key': middleware.bucketGet('dd_sign_config', 'ma_pay_key') or '',
        'notify_url': middleware.bucketGet('dd_sign_config', 'ma_pay_notify_url') or '',
        'return_url': middleware.bucketGet('dd_sign_config', 'ma_pay_return_url') or ''
    }
    if not (config['gateway'] and config['pid'] and config['key']):
        sender.reply('❌ 码支付配置不完整')
        return False

    amount = round(float(money), 2)
    out_trade_no = f"WUYOU{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(10000, 99999)}"
    selected_type = pay_type or 'alipay'

    sender.reply(f"===== 支付信息 =====\n🎫 商品: {project}\n📅 时长: {months}月\n💰 金额: {amount}元\n💳 支付: {PAY_TYPE_NAMES.get(selected_type, selected_type)}\n==================")

    params = {
        'pid': config['pid'], 'type': selected_type, 'out_trade_no': out_trade_no,
        'notify_url': config['notify_url'], 'return_url': config['return_url'],
        'name': f"{project}-{amount}", 'money': str(amount), 'param': userid
    }
    params = {k: v for k, v in params.items() if v}
    sign_str = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    params['sign'] = hashlib.md5((sign_str + config['key']).encode()).hexdigest().lower()
    params['sign_type'] = 'MD5'

    try:
        resp = requests.post(f"{config['gateway'].rstrip('/')}/mapi.php", data=params, timeout=10).json()
        if resp.get('code') != 1:
            sender.reply(f'❌ 创建订单失败: {resp.get("msg")}')
            return False
        trade_no = resp.get('trade_no')
        pay_url = f"{config['gateway'].rstrip('/')}/pay/{trade_no}"
        iframe_url = generate_iframe_url(pay_url)
        sender.reply('请扫描下方二维码完成支付:')
        sender.replyImage(generate_qrcode(iframe_url))
        sender.reply('输入"q"可取消')

        for _ in range(30):
            qresp = requests.get(
                f"{config['gateway'].rstrip('/')}/xpay/epay/api.php",
                params={'act': 'order', 'pid': config['pid'], 'key': config['key'], 'out_trade_no': out_trade_no},
                timeout=10
            ).json()
            if qresp.get('code') == 1 and qresp.get('status') == 1:
                return True
            if sender.listen(5000) == 'q':
                sender.reply("✅ 已取消")
                return False
        sender.reply("❌ 支付超时")
        return False
    except Exception as e:
        sender.reply(f'❌ 支付异常: {str(e)}')
        return False


def process_payment_zsm(uid, months):
    """处理扫码支付（已知月数）"""
    try:
        price, _, zsm, _, _, _, _ = get_config()
        if price is None:
            sender.reply("❌ 未设置价格，请联系管理员")
            return False
        token_info_str = middleware.bucketGet(BUCKET_TOKEN, uid)
        if not token_info_str:
            sender.reply(f"❌ 未找到账号 {uid} 的Token信息")
            return False
        token_info = json.loads(token_info_str)
        alias = token_info.get("alias", "未知用户")
        total_price = price * months
        if not zsm:
            sender.reply("❌ 未配置收款码")
            return False

        pay_msg = f"""
=====扫码支付=====
💰 单价: {price}元/月
⏰ 时长: {months}月
👤 用户: {alias}
📱 UID: {uid}
💵 总价: {total_price}元
------------------"""
        if price == 0:
            pay_msg += "\n✅ 免费授权，无需支付"
            sender.reply(pay_msg)
            return set_auth_success(uid, months, total_price)
        else:
            pay_msg += """请使用微信扫码支付
回复"q"取消"""
            sender.reply(pay_msg)
            sender.replyImage(zsm)
            result = sender.waitPay("q", 120000)
            if result == 'q':
                sender.reply("✅ 已取消支付")
                return False
            try:
                if isinstance(result, str):
                    result = json.loads(result)
                if float(result.get('Money', 0)) or float(result.get('money', 0)) >= float(total_price):
                    return set_auth_success(uid, months, total_price)
                else:
                    sender.reply(f"❌ 支付失败，应付金额{total_price}元，实付金额{result.get('Money', 0)}元")
            except:
                sender.reply("❌ 支付失败，返回数据格式错误")
                return False
    except Exception as e:
        sender.reply(f"❌ 扫码支付失败: {str(e)}")
        return False


def process_coin_auth_with_months(uid, months):
    """处理积分兑换授权（已知月数）"""
    try:
        _, coin_price, _, _, _, _, _ = get_config()
        if not coin_price:
            sender.reply("❌ 积分授权未开启")
            return False
        token_info_str = middleware.bucketGet(BUCKET_TOKEN, uid)
        if not token_info_str:
            sender.reply(f"❌ 未找到账号 {uid} 的Token信息")
            return False
        token_info = json.loads(token_info_str)
        alias = token_info.get("alias", "未知用户")
        user_coin = Decimal(middleware.bucketGet('dd_sign_points', userid) or '0')
        required_coin = Decimal(coin_price) * months
        if user_coin < required_coin:
            sender.reply(f"❌ 积分不足，当前积分: {user_coin}，需要积分: {required_coin}")
            return False

        sender.reply(f"""
=====兑换确认=====
👤 用户: {alias}
📱 UID: {uid}
💰 当前积分: {user_coin}
🎟 兑换: {months}个月
💵 需要积分: {required_coin}
💰 剩余积分: {user_coin - required_coin}
------------------
回复"y"确认兑换
回复其他取消""")
        confirm = sender.listen(60000)
        if confirm.lower() != 'y':
            sender.reply("✅ 已取消兑换")
            return False

        remaining_coin = user_coin - required_coin
        middleware.bucketSet('dd_sign_points', userid, str(remaining_coin))
        auth_time = calculate_auth_time(uid, months)
        middleware.bucketSet(BUCKET_AUTH, uid, auth_time)

        _, _, _, ql_config, ql_envname, _, _ = get_config()
        ql_result = False
        if ql_config:
            ql_result, _ = add_to_qinglong(uid, token_info, ql_envname)

        sender.reply(f"""
=====兑换成功=====
👤 用户: {alias}
📱 UID: {uid}
🎟️ 兑换: {months}个月授权
📅 有效期至: {auth_time}
💰 剩余积分: {remaining_coin}
------------------
🔄 青龙同步: {'成功' if ql_result else '失败'}
==================""")
        return True
    except Exception as e:
        sender.reply(f"❌ 积分兑换失败: {str(e)}")
        return False


def process_auth(uid):
    """处理授权流程"""
    try:
        price, coin_price, zsm, ql_config, ql_envname, _, _ = get_config()
        token_info_str = middleware.bucketGet(BUCKET_TOKEN, uid)
        if not token_info_str:
            sender.reply(f"❌ 未找到账号 {uid} 的Token信息")
            return False
        token_info = json.loads(token_info_str)
        alias = token_info.get("alias", "未知用户")

        auth_options = """=====授权选项=====\n"""
        options = []
        option_index = 1

        ma_pay_switch = middleware.bucketGet(BUCKET_CONFIG, 'ma_pay_switch') or 'false'
        if ma_pay_switch.lower() == 'true' and middleware.bucketGet('dd_sign_config', 'ma_pay_gateway'):
            for pt in (middleware.bucketGet('dd_sign_config', 'ma_pay_type') or 'alipay,wxpay').split(','):
                auth_options += f"[{option_index}] {PAY_TYPE_NAMES.get(pt.strip(), pt.strip())} ({price}元/月)\n"
                options.append((str(option_index), f"mapay_{pt.strip()}"))
                option_index += 1
        elif zsm and price is not None:
            auth_options += f"[{option_index}] 扫码支付 ({price}元/月)\n"
            options.append((str(option_index), "zsm"))
            option_index += 1

        if coin_price:
            auth_options += f"[{option_index}] 积分兑换 ({coin_price}积分/月)\n"
            options.append((str(option_index), "coin"))
            option_index += 1

        if not options:
            sender.reply("❌ 未配置任何授权方式，请联系管理员")
            return False

        auth_options += """------------------
请选择授权方式
回复"q"退出"""
        sender.reply(auth_options)
        option = sender.listen(60000)
        if not option or option == 'q':
            sender.reply("✅ 已退出授权流程")
            return False

        selected_pay_type = None
        for opt_num, pay_type in options:
            if option == opt_num:
                selected_pay_type = pay_type
                break
        if not selected_pay_type:
            sender.reply("❌ 无效的选择")
            return False

        sender.reply("""请输入授权月数:
回复"q"退出""")
        months = sender.listen(60000)
        if not months or months == 'q':
            sender.reply("✅ 已退出授权流程")
            return False
        try:
            months = int(months)
            if months <= 0:
                raise ValueError()
        except ValueError:
            sender.reply("❌ 无效的月数")
            return False

        if selected_pay_type == "coin":
            return process_coin_auth_with_months(uid, months)
        elif selected_pay_type == "zsm":
            return process_payment_zsm(uid, months)
        elif selected_pay_type.startswith("mapay_"):
            total_price = float(price) * months
            if handle_mapay_order(PLUGIN_NAME, months, total_price, selected_pay_type.replace('mapay_', '')):
                return set_auth_success(uid, months, total_price)
            return False
        else:
            sender.reply("❌ 无效的选择")
            return False
    except Exception as e:
        sender.reply(f"❌ 授权流程失败: {str(e)}")
        return False


# ==================== 青龙相关功能 ====================

def get_ql_token(host, client_id, client_secret):
    """获取青龙面板的访问令牌"""
    try:
        url = f'{host}/open/auth/token?client_id={client_id}&client_secret={client_secret}'
        response = requests.get(url)
        data = response.json()
        if data.get('code') == 200:
            return data['data']['token']
        print(f"获取青龙token失败: {data}")
        return None
    except Exception as e:
        print(f"获取青龙token异常: {str(e)}")
        return None


def add_to_qinglong(uid, token_info, env_name="S_WUYOU"):
    """添加无优计划账号到青龙"""
    try:
        _, _, _, ql_config, _, _, _ = get_config()
        if not ql_config:
            print("未配置青龙信息")
            return False, "未配置青龙信息"

        configs = ql_config.split('丨')
        if len(configs) < 3:
            configs = ql_config.split('|')
            if len(configs) < 3:
                return False, "青龙配置格式错误"

        host = configs[0].strip()
        client_id = configs[1].strip()
        client_secret = configs[2].strip()

        token = get_ql_token(host, client_id, client_secret)
        if not token:
            return False, "获取青龙token失败"

        headers = {'Authorization': f'Bearer {token}'}
        envs_response = requests.get(f'{host}/open/envs', headers=headers)
        if envs_response.status_code != 200:
            return False, "获取环境变量失败"

        envs = envs_response.json()['data']
        for env in envs:
            if env['name'] == env_name and uid in env['value']:
                env_id = env.get('_id') or env.get('id')
                if env_id:
                    requests.delete(f'{host}/open/envs', headers=headers, json=[env_id])
                break

        if isinstance(token_info, str):
            token_info = json.loads(token_info)

        account = token_info.get("account", "")
        password = token_info.get("password", "")
        device_id = token_info.get("device_id", "")
        alias = token_info.get("alias", "未知用户")
        env_value = f"{account}#{password}#{device_id}"
        auth_time = middleware.bucketGet(BUCKET_AUTH, uid) or '未授权'

        data = [{
            'name': env_name, 'value': env_value,
            'remarks': f"无优账号：{alias}({account})|到期：{auth_time}"
        }]
        add_response = requests.post(f'{host}/open/envs', headers=headers, json=data)
        if add_response.status_code != 200:
            return False, "添加变量失败"

        result = add_response.json()
        if result['code'] != 200:
            return False, f"添加变量失败: {result.get('message')}"

        new_id = result['data'][0].get('_id') or result['data'][0].get('id')
        if new_id:
            requests.put(f'{host}/open/envs/enable', headers=headers, json=[new_id])
        return True, "添加青龙变量成功"
    except Exception as e:
        return False, f"添加青龙变量异常: {str(e)}"


def delete_from_qinglong(uid, env_name=None):
    """从青龙面板删除指定账号的变量"""
    try:
        _, _, _, ql_config, ql_envname, _, _ = get_config()
        if not env_name:
            env_name = ql_envname
        if not ql_config:
            return False, "未配置青龙信息"

        configs = ql_config.split('丨')
        if len(configs) < 3:
            configs = ql_config.split('|')
            if len(configs) < 3:
                return False, "青龙配置格式错误"

        host = configs[0].strip()
        client_id = configs[1].strip()
        client_secret = configs[2].strip()
        token = get_ql_token(host, client_id, client_secret)
        if not token:
            return False, "获取青龙token失败"

        headers = {'Authorization': f'Bearer {token}'}
        envs_response = requests.get(f'{host}/open/envs', headers=headers)
        if envs_response.status_code != 200:
            return False, "获取环境变量失败"

        envs = envs_response.json()['data']
        deleted = False
        for env in envs:
            if env['name'] == env_name and uid in env['value']:
                env_id = env.get('_id') or env.get('id')
                if env_id:
                    delete_response = requests.delete(f'{host}/open/envs', headers=headers, json=[env_id])
                    if delete_response.status_code == 200:
                        deleted = True
        return deleted, "删除" + ("成功" if deleted else "失败")
    except Exception as e:
        return False, f"删除青龙变量异常: {str(e)}"


# ==================== 过期检测 ====================

def mask_uid(uid):
    if not uid or len(uid) < 6:
        return uid
    return f"{uid[:3]}***{uid[-3:]}"


def check_auth_status():
    """检测授权状态并推送通知"""
    notify = middleware.bucketGet(BUCKET_CONFIG, 'notify') or ''
    if not notify:
        return "❌ 未配置通知渠道"
    channels = [c.strip() for c in notify.split(',') if c.strip()]
    all_users = middleware.bucketAllKeys(BUCKET_USER)
    if not all_users:
        return "❌ 没有用户"

    notify_days = int(middleware.bucketGet(BUCKET_CONFIG, 'notify_days') or '3')
    current_date = datetime.now().date()
    total, notified, cleaned = 0, 0, 0

    for user_id in all_users:
        try:
            accounts = eval(middleware.bucketGet(BUCKET_USER, user_id) or '[]')
            to_notify, to_clean = [], []

            for uid in accounts:
                auth_time_str = middleware.bucketGet(BUCKET_AUTH, uid)
                token_info_str = middleware.bucketGet(BUCKET_TOKEN, uid)
                alias = "未知用户"
                if token_info_str:
                    try:
                        alias = json.loads(token_info_str).get("alias", "未知用户")
                    except:
                        pass

                if not auth_time_str:
                    to_clean.append({'uid': uid, 'alias': alias, 'auth_time': '未授权', 'days_left': 0})
                    continue
                try:
                    auth_date = datetime.strptime(auth_time_str, "%Y-%m-%d").date()
                    days_left = (auth_date - current_date).days
                    if days_left <= 0:
                        to_clean.append({'uid': uid, 'alias': alias, 'auth_time': auth_time_str, 'days_left': days_left})
                    elif days_left <= notify_days:
                        to_notify.append({'uid': uid, 'alias': alias, 'auth_time': auth_time_str, 'days_left': days_left})
                except:
                    to_clean.append({'uid': uid, 'alias': alias, 'auth_time': auth_time_str, 'days_left': 0})

            total += len(accounts)

            if to_clean:
                for acc in to_clean:
                    uid = acc['uid']
                    delete_from_qinglong(uid)
                    middleware.bucketSet(BUCKET_TOKEN, uid, '')
                    if uid in accounts:
                        accounts.remove(uid)
                    middleware.bucketSet(BUCKET_AUTH, uid, '')
                    cleaned += 1
                if accounts:
                    middleware.bucketSet(BUCKET_USER, user_id, str(accounts))
                else:
                    middleware.bucketDel(BUCKET_USER, user_id)

            if to_notify:
                notify_list = "\n".join([
                    f"📱 {a['alias']}({mask_uid(a['uid'])}) 剩余{a['days_left']}天({a['auth_time']})"
                    for a in to_notify
                ])
                msg = f"=====无优计划账号检测=====\n⚠️ 即将过期:\n{notify_list}\n💡 发送\"无优管理\"续费\n=================="
                for ch in channels:
                    try:
                        middleware.push(imType=ch, groupCode='', userID=user_id, title="", content=msg)
                        notified += 1
                    except:
                        pass
        except:
            pass

    return f"✅ 无优计划检测完成，共 {total} 个账号，发送 {notified} 条通知，清理 {cleaned} 个过期账号"


# ==================== 管理员授权 ====================

def admin_auth_all_accounts():
    """管理员一键授权所有用户的所有账号"""
    try:
        users = middleware.bucketAllKeys(BUCKET_USER)
        if not users:
            sender.reply("❌ 未找到任何用户账号")
            return
        total_accounts = 0
        for user_id in users:
            accounts_str = middleware.bucketGet(BUCKET_USER, user_id)
            if accounts_str and accounts_str != '[]':
                total_accounts += len(eval(accounts_str))

        sender.reply(f"""
=====授权所有用户=====
👥 用户数: {len(users)}
📊 账号数: {total_accounts}
------------------
请输入授权天数:
(正数增加天数，负数减少天数)
回复"q"退出""")
        days_input = sender.listen(60000)
        if not days_input or days_input == 'q':
            sender.reply("✅ 已取消授权")
            return
        try:
            days = int(days_input)
        except ValueError:
            sender.reply("❌ 无效的天数")
            return

        action_text = f"增加 {days} 天" if days > 0 else f"减少 {abs(days)} 天"
        sender.reply(f"""
=====确认授权=====
👥 用户数: {len(users)}
📊 账号数: {total_accounts}
⏰ 操作: {action_text}
------------------
⚠️ 此操作影响所有用户
回复"y"确认
回复其他取消""")
        confirm = sender.listen(60000)
        if not confirm or confirm.lower() != 'y':
            sender.reply("✅ 已取消授权")
            return

        success_count, fail_count = 0, 0
        for user_id in users:
            accounts_str = middleware.bucketGet(BUCKET_USER, user_id)
            if not accounts_str or accounts_str == '[]':
                continue
            try:
                accounts = eval(accounts_str)
                for uid in accounts:
                    try:
                        token_info_str = middleware.bucketGet(BUCKET_TOKEN, uid)
                        if not token_info_str:
                            fail_count += 1
                            continue
                        new_auth_time = calculate_auth_time_by_days(uid, days)
                        middleware.bucketSet(BUCKET_AUTH, uid, new_auth_time)
                        _, _, _, ql_config, ql_envname, _, _ = get_config()
                        if ql_config:
                            add_to_qinglong(uid, json.loads(token_info_str), ql_envname)
                        success_count += 1
                    except Exception as e:
                        print(f"授权账号 {uid} 出错: {str(e)}")
                        fail_count += 1
            except Exception as e:
                print(f"处理用户 {user_id} 出错: {str(e)}")

        sender.reply(f"""
=====授权结果=====
✅ 成功: {success_count} 个账号
❌ 失败: {fail_count} 个账号
⏰ 操作: {action_text}
==================""")
    except Exception as e:
        sender.reply(f"❌ 授权失败: {str(e)}")


def admin_auth_by_user():
    """管理员按用户授权"""
    try:
        sender.reply("""
=====按用户授权=====
请输入用户ID:
回复"q"退出""")
        target_user_id = sender.listen(60000)
        if not target_user_id or target_user_id == 'q':
            sender.reply("✅ 已退出")
            return

        accounts_str = middleware.bucketGet(BUCKET_USER, target_user_id)
        if not accounts_str or accounts_str == '[]':
            sender.reply(f"❌ 用户 {target_user_id} 没有绑定任何账号")
            return

        accounts = eval(accounts_str)
        account_list = f"=====用户 {target_user_id} 的账号=====\n[0] 选择全部账号\n"
        for i, uid in enumerate(accounts, 1):
            token_info_str = middleware.bucketGet(BUCKET_TOKEN, uid)
            if token_info_str:
                try:
                    token_info = json.loads(token_info_str)
                    alias = token_info.get("alias", "未知用户")
                    auth_time = middleware.bucketGet(BUCKET_AUTH, uid) or '未授权'
                    account_list += f"[{i}] {alias} ({uid}) - {auth_time}\n"
                except:
                    account_list += f"[{i}] {uid} - 数据错误\n"
            else:
                account_list += f"[{i}] {uid} - 数据错误\n"

        account_list += """------------------
支持多选，用逗号分隔
回复"q"退出"""
        sender.reply(account_list)
        account_choice = sender.listen(60000)
        if not account_choice or account_choice == 'q':
            sender.reply("✅ 已取消授权")
            return

        selected_uids = []
        if account_choice == '0':
            selected_uids = accounts.copy()
        else:
            try:
                indices = [int(idx.strip()) - 1 for idx in account_choice.split(',') if idx.strip().isdigit()]
                for index in indices:
                    if 0 <= index < len(accounts):
                        selected_uids.append(accounts[index])
            except:
                sender.reply("❌ 无效的选择格式")
                return

        if not selected_uids:
            sender.reply("❌ 未选择任何账号")
            return

        sender.reply(f"""
已选择 {len(selected_uids)} 个账号
请输入授权天数:
(正数增加天数，负数减少天数)
回复"q"退出""")
        days_input = sender.listen(60000)
        if not days_input or days_input == 'q':
            sender.reply("✅ 已取消授权")
            return
        try:
            days = int(days_input)
        except ValueError:
            sender.reply("❌ 无效的天数")
            return

        action_text = f"增加 {days} 天" if days > 0 else f"减少 {abs(days)} 天"
        sender.reply(f"""
=====确认授权=====
📊 账号数: {len(selected_uids)} 个
⏰ 操作: {action_text}
------------------
回复"y"确认
回复其他取消""")
        confirm = sender.listen(60000)
        if not confirm or confirm.lower() != 'y':
            sender.reply("✅ 已取消授权")
            return

        success_count, fail_count = 0, 0
        for uid in selected_uids:
            try:
                token_info_str = middleware.bucketGet(BUCKET_TOKEN, uid)
                if not token_info_str:
                    fail_count += 1
                    continue
                new_auth_time = calculate_auth_time_by_days(uid, days)
                middleware.bucketSet(BUCKET_AUTH, uid, new_auth_time)
                _, _, _, ql_config, ql_envname, _, _ = get_config()
                if ql_config:
                    add_to_qinglong(uid, json.loads(token_info_str), ql_envname)
                success_count += 1
            except Exception as e:
                print(f"授权账号 {uid} 出错: {str(e)}")
                fail_count += 1

        sender.reply(f"""
=====授权结果=====
✅ 成功: {success_count} 个账号
❌ 失败: {fail_count} 个账号
⏰ 操作: {action_text}
==================""")
    except Exception as e:
        sender.reply(f"❌ 授权失败: {str(e)}")


def admin_auth_management():
    """管理员授权管理"""
    try:
        sender.reply("""
=====管理员授权=====
[1] 授权所有用户
[2] 按用户授权
------------------
回复数字选择操作
回复"q"退出""")
        option = sender.listen(60000)
        if not option or option == 'q':
            sender.reply("✅ 已退出管理员授权")
            return
        if option == '1':
            admin_auth_all_accounts()
        elif option == '2':
            admin_auth_by_user()
        else:
            sender.reply("❌ 无效的选择")
    except Exception as e:
        sender.reply(f"❌ 管理员授权失败: {str(e)}")


# ==================== 无优计划核心业务 ====================

class AppAttest:
    """App Attest 签名会话（逆向自 AppAttestBridge / AppAttestManager）"""

    def __init__(self, http, device_id, log_func):
        self.http = http
        self.device_id = device_id
        self.log = log_func
        self.session_id = None
        self.session_secret = None
        self.expires_at = 0

    def has_session(self):
        return bool(self.session_id and self.session_secret and time.time() < self.expires_at)

    def ensure(self, force=False):
        if not force and self.has_session():
            return True
        try:
            ts = str(int(time.time()))
            nonce = secrets.token_hex(16)
            native_proof = hmac_hex(ATTEST_KEY, f"attest\n{ts}\n{nonce}\n{self.device_id}")
            payload = {"integrity_token": "", "device_id": self.device_id, "ts": ts, "nonce": nonce, "native_proof": native_proof}
            resp = self.http.post(ATTEST_URL, data=compact_json(payload), headers={"Content-Type": "application/json"}, verify=False, timeout=15)
            data = resp.json()
            if data.get("ok") and data.get("session_id") and data.get("session_secret"):
                self.session_id = data["session_id"]
                self.session_secret = data["session_secret"]
                self.expires_at = time.time() + int(data.get("expires_in", 1800)) - 60
                return True
            self.log(f"⚠️ attest 失败: {str(data)[:200]}")
        except Exception as e:
            self.log(f"⚠️ attest 异常: {e}")
        return False

    def sign_headers(self, method, url, body):
        if not self.has_session():
            return {}
        ts = str(int(time.time()))
        nonce = secrets.token_hex(16)
        path = urlsplit(url).path or "/"
        body_hash = sha256_hex(body)
        msg = f"{method.upper()}\n{path}\n{ts}\n{nonce}\n{body_hash}"
        sign = hmac_hex(self.session_secret, msg)
        return {"X-App-Session": self.session_id, "X-App-Ts": ts, "X-App-Nonce": nonce, "X-App-Sign": sign}


class WuYouPlan:
    """无优计划自动任务执行器（适配 middleware 框架）"""

    def __init__(self, account, password, device_id="", ua=""):
        self.account = account
        self.password = password
        self.session = requests.Session()
        self.session.verify = False
        self.ua = ua or DEFAULT_UA
        self.session.headers.update({
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "origin": "https://localhost",
            "referer": "https://localhost/",
            "x-requested-with": "com.dgccvi.app",
            "user-agent": self.ua,
            "accept-encoding": "gzip, deflate",
            "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "sec-fetch-site": "cross-site",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "sec-ch-ua": '"Chromium";v="148", "Android WebView";v="148", "Not/A)Brand";v="99"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
        })
        self.device_id = device_id
        self.attest = AppAttest(self.session, self.device_id, self.log)
        self.token = None
        self.user_id = None
        self.user_info = None
        self.total_coins_earned = 0

    def log(self, msg):
        sender.reply(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def _request(self, method, url, payload=None, params=None, retry_on_app_required=True):
        body = b"" if payload is None else compact_json(payload)
        headers = dict(self.attest.sign_headers(method, url, body))
        if payload is not None:
            headers["Content-Type"] = "application/json"
        resp = self.session.request(method, url, data=body if payload is not None else None, params=params, headers=headers, timeout=20)
        if retry_on_app_required and resp.status_code == 403:
            try:
                err = resp.json()
            except Exception:
                err = {}
            if err.get("code") == "app_required":
                self.log("🔁 收到 app_required，重新进行 attest 签名...")
                if self.attest.ensure(force=True):
                    return self._request(method, url, payload, params, retry_on_app_required=False)
        return resp

    def _get(self, url, params=None):
        return self._request("GET", url, params=params)

    def _post(self, url, payload=None, params=None):
        return self._request("POST", url, payload=payload if payload is not None else {}, params=params)

    def login(self):
        self.attest.ensure()
        payload = {"account": self.account, "password": self.password, "device_id": self.device_id, "platform": "android", "app_version": APP_VERSION}
        resp = self._post(LOGIN_URL, payload)
        data = resp.json()
        token = data.get("token")

        used_fallback = False
        if not token and data.get("code") == "device_limit":
            self.log("⚠️ 设备数量已达上限，尝试用空 device_id 登录...")
            payload["device_id"] = ""
            resp = self._post(LOGIN_URL, payload)
            data = resp.json()
            token = data.get("token")
            used_fallback = True

        if token:
            self.token = token
            self.user_info = data.get("user", {})
            self.user_id = self.user_info.get("id")
            self.session.headers.update({"authorization": f"Bearer {self.token}"})
            self.log(f"✅ 登录成功 | 用户ID: {self.user_id} | device_id: {self.device_id or '(待回填)'}")
            if used_fallback or not self.device_id:
                if self.sync_device_from_server():
                    self.log(f"📱 已回填服务端绑定设备 device_id: {self.device_id}")
                else:
                    self.log("⚠️ 未能回填 device_id，广告流程可能受限")
            return True
        else:
            self.log(f"❌ 登录失败: {str(data)[:300]}")
            return False

    def sync_device_from_server(self):
        try:
            resp = self._get(USER_DEVICES_URL, params={"device_id": self.device_id})
            data = resp.json()
            devices = data.get("devices", [])
            chosen = next((d for d in devices if d.get("is_current")), None) or (devices[0] if devices else None)
            if chosen and chosen.get("device_id"):
                new_device_id = chosen["device_id"]
                if new_device_id != self.device_id:
                    self.device_id = new_device_id
                    self.attest.device_id = new_device_id
                    self.attest.session_id = None
                    self.attest.session_secret = None
                    self.attest.ensure(force=True)
                return True
        except Exception as e:
            self.log(f"⚠️ 回填 device_id 失败: {e}")
        return False

    def get_user_info(self):
        resp = self._get(ME_URL, params={"device_id": self.device_id, "platform": "android", "app_version": APP_VERSION})
        return resp.json().get("user", {})

    def get_user_devices(self):
        resp = self._get(USER_DEVICES_URL, params={"device_id": self.device_id})
        data = resp.json()
        devices = data.get("devices", [])
        device_ids = [d.get("device_id", "") for d in devices]
        self.log(f"📱 查询设备 | device_id: {device_ids}")
        return data

    def get_daily_tasks(self):
        resp = self._get(DAILY_TASKS_URL)
        return resp.json()

    def checkin(self):
        self.log("📅 执行每日签到...")
        resp = self._post(CHECKIN_URL)
        data = resp.json()
        coins = data.get("coins_awarded", 0)
        day = data.get("day_number", 0)
        msg = data.get("message", "")
        self.total_coins_earned += coins
        self.log(f"   {msg} | 连续第{day}天 | +{coins}金币")

        self.log("🎁 领取签到奖励...")
        resp2 = self._post(f"{DAILY_TASKS_URL}/daily_checkin/claim")
        data2 = resp2.json()
        if data2.get("ok"):
            claim_coins = data2.get("coins", 0)
            claim_msg = data2.get("message", "")
            self.total_coins_earned += claim_coins
            self.log(f"   {claim_msg} | +{claim_coins}金币")
        else:
            self.log(f"   ⚠️ 领取签到奖励失败: {str(data2)[:200]}")
        return data

    def claim_task(self, task_key):
        url = f"{DAILY_TASKS_URL}/{task_key}/claim"
        resp = self._post(url)
        data = resp.json()
        if data.get("ok"):
            coins = data.get("coins", 0)
            msg = data.get("message", "")
            self.total_coins_earned += coins
            self.log(f"   {msg} | +{coins}金币")
        else:
            self.log(f"   ⚠️ 领取失败 ({task_key}): {str(data)[:200]}")
        return data

    def get_ads_info(self):
        resp = self._get(ADS_LIST_URL, params={"device_id": self.device_id})
        data = resp.json()
        self.log(f"📡 [广告] enabled={data.get('enabled')} | 每日上限={data.get('max_views_per_day')} | 可选={len(data.get('items', []))}")
        return data

    def start_ad_session(self):
        payload = {"device_id": self.device_id, "client": "app"}
        resp = self._post(ADS_SESSION_START_URL, payload)
        try:
            return resp.json()
        except Exception:
            return {"ok": False, "message": f"HTTP {resp.status_code}: {resp.text[:150]}"}

    def send_heartbeat(self, play_token, progress_seconds):
        payload = {"play_token": play_token, "progress_seconds": progress_seconds}
        resp = self._post(ADS_HEARTBEAT_URL, payload)
        return resp.json()

    def complete_ad_session(self, play_token, progress_seconds):
        payload = {"play_token": play_token, "progress_seconds": progress_seconds}
        resp = self._post(ADS_COMPLETE_URL, payload)
        return resp.json()

    def watch_ads(self, account_max_views=None):
        self.log("📺 开始广告流程...")
        ads_info = self.get_ads_info()
        enabled = ads_info.get("enabled", False)
        max_views = ads_info.get("max_views_per_day", 20)
        if account_max_views:
            max_views = min(max_views, account_max_views)
        items = ads_info.get("items", [])
        heartbeat_interval = ads_info.get("heartbeat_interval", 30)

        if not enabled:
            self.log("   ⚠️ 广告功能未启用")
            return
        if max_views <= 0:
            self.log("   ⚠️ 今日广告次数已用完")
            return
        self.log(f"   广告已启用 | 今日可看 {max_views} 次 | 共 {len(items)} 个广告可选")

        success_count, fail_count = 0, 0
        for i in range(max_views):
            self.log(f"\n{'─' * 50}")
            self.log(f"📺 第 {i+1}/{max_views} 个广告")

            session_data = self.start_ad_session()
            if not session_data.get("ok"):
                msg = session_data.get("message") or str(session_data)[:200]
                self.log(f"   ❌ 启动广告会话失败: {msg}")
                fail_count += 1
                break

            sess = session_data.get("session", {})
            play_token = sess.get("play_token")
            duration = sess.get("duration_seconds", 30)
            reward = sess.get("reward_coins", 0)
            hb_interval = sess.get("heartbeat_interval", heartbeat_interval)
            ad_info = sess.get("ad", {})
            self.log(f"   📱 {ad_info.get('title', '未知')} | 时长: {duration}秒 | 💰 奖励: {reward}金币")

            time.sleep(random.uniform(0.2, 1.5))
            elapsed = random.uniform(0.1, 0.5)
            self.send_heartbeat(play_token, round(elapsed, 2))

            next_hb = hb_interval + random.uniform(0.1, 0.3)
            while elapsed < duration:
                remain = duration - elapsed
                step = min(next_hb, remain)
                time.sleep(max(step, 0.1) if step > 0.1 else 0.1)
                elapsed = min(elapsed + step, duration)
                if elapsed >= duration:
                    break
                self.send_heartbeat(play_token, round(elapsed, 2))
                self.log(f"   💓 心跳 | 进度: {round(elapsed, 2)}/{duration}秒")
                next_hb = hb_interval + random.uniform(0.1, 0.3)

            final_progress = round(duration + random.uniform(0.05, 0.3), 2)
            self.send_heartbeat(play_token, final_progress)
            time.sleep(random.uniform(0.5, 1.2))
            self.send_heartbeat(play_token, final_progress)

            self.log("   🏁 完成观看，领取奖励...")
            complete_data = self.complete_ad_session(play_token, final_progress)

            if complete_data.get("ok"):
                coins = complete_data.get("gold_coins", 0)
                msg = complete_data.get("message", "")
                self.total_coins_earned += coins
                success_count += 1
                self.log(f"   ✅ {msg} | +{coins}金币 | 累计: {self.total_coins_earned}金币")
            else:
                err_msg = complete_data.get("message", "领取失败")
                self.log(f"   ❌ {err_msg}")
                fail_count += 1

            if i < max_views - 1:
                interval = complete_data.get("next_request_available_in") or session_data.get("request_interval_seconds") or random.randint(3, 5)
                self.log(f"   ⏳ 等待 {interval} 秒后请求下一个广告...")
                time.sleep(interval)

        self.log(f"\n{'─' * 50}")
        self.log(f"📊 广告观看汇总: 成功 {success_count} 次 | 失败 {fail_count} 次 | 本次运行累计 +{self.total_coins_earned}金币")

    def run(self):
        self.log(f"🚀 无优计划 - 账号: {self.account}")
        if not self.login():
            return None

        user = self.get_user_info()
        nickname = user.get("nickname", "")
        wallet = user.get("wallet", {})
        start_coins = wallet.get("gold_coins", 0)
        account_max_views = user.get("max_alliance_ads_per_day")
        level = (user.get("gold_level") or {}).get("name", "")
        self.log(f"👤 {nickname} | 等级: {level} | 当前金币: {start_coins} | 广告上限: {account_max_views}/天")

        self.log("📋 获取任务列表...")
        tasks_data = self.get_daily_tasks()
        tasks = tasks_data.get("tasks", [])
        today = tasks_data.get("today", "")
        pending = tasks_data.get("pending_claim", 0)
        self.log(f"📅 日期: {today} | 待领取: {pending}个")
        for task in tasks:
            icon = task.get("icon", "📌")
            title = task.get("title", "")
            reward = task.get("reward_coins", 0)
            progress = task.get("current_progress", 0)
            target = task.get("condition_value", 0)
            completed = task.get("is_completed", False)
            claimed = task.get("is_claimed", False)
            period = task.get("period_type", "")
            if claimed:
                status = "✅已领取"
            elif completed:
                status = "🎁可领取"
            else:
                status = f"⏳{progress}/{target}"
            self.log(f"  {icon} {title} | {status} | +{reward}金币 | [{period}]")

        self.checkin()

        try:
            devices_data = self.get_user_devices()
            max_devices = devices_data.get("max_devices", 0)
            used = devices_data.get("devices_used", 0)
            phone_masked = devices_data.get("phone_masked", "")
            self.log(f"📱 设备: {used}/{max_devices} | 手机号: {phone_masked}")
            tip = devices_data.get("tip", "")
            if tip:
                self.log(f"   💡 {tip}")
        except Exception as e:
            self.log(f"   ⚠️ 查询设备信息失败: {e}")

        self.watch_ads(account_max_views=account_max_views)

        tasks_data = self.get_daily_tasks()
        for task in tasks_data.get("tasks", []):
            task_key = task.get("task_key", "")
            if task.get("is_completed") and not task.get("is_claimed"):
                self.claim_task(task_key)

        user2 = self.get_user_info()
        end_coins = user2.get("wallet", {}).get("gold_coins", 0)
        earned = end_coins - start_coins
        self.log(f"✨ 任务执行完毕 | 本次获得: {earned}金币 | 总金币: {end_coins}")

        return {"start_coins": start_coins, "end_coins": end_coins, "earned": earned, "nickname": nickname}


# ==================== 登录/保存 ====================

def save_user_info(login_data, device_id):
    """保存无优计划用户信息到数据桶"""
    try:
        account = login_data.get("account", "")
        password = login_data.get("password", "")
        user_info = login_data.get("user", {})
        uid = str(user_info.get("id", ""))
        token = login_data.get("token", "")
        nickname = user_info.get("nickname", account)

        if not uid:
            sender.reply("❌ 无法获取用户UID")
            return False

        token_data = {
            "uid": uid, "account": account, "password": password,
            "token": token, "device_id": device_id, "alias": nickname,
            "UpdateTime": int(time.time())
        }

        user_accounts = eval(middleware.bucketGet(BUCKET_USER, userid) or '[]')
        if uid not in user_accounts:
            user_accounts.append(uid)
            middleware.bucketSet(BUCKET_USER, userid, str(user_accounts))

        middleware.bucketSet(BUCKET_TOKEN, uid, json.dumps(token_data, ensure_ascii=False))
        middleware.bucketSet(BUCKET_DEVICE, uid, device_id)

        sender.reply(f"""
=====登录成功=====
👤 用户: {nickname}
📱 UID: {uid}
📱 账号: {account}
✅ 数据已保存
==================""")

        auth_time = middleware.bucketGet(BUCKET_AUTH, uid) or ''
        current_date = datetime.now().strftime("%Y-%m-%d")
        if not auth_time or auth_time < current_date:
            process_auth(uid)
        else:
            _, _, _, ql_config, ql_envname, _, _ = get_config()
            if ql_config:
                ql_result, _ = add_to_qinglong(uid, token_data, ql_envname)
                if ql_result:
                    print(f"更新青龙变量成功: {uid}")

        return True
    except Exception as e:
        sender.reply(f"❌ 保存用户信息失败: {str(e)}")
        return False


def process_login():
    """处理登录流程"""
    sender.reply("""
=====登录方式=====
账号密码登录
------------------
请输入账号（手机号）：
回复"q"退出""")
    account = sender.listen(60000)
    if not account or account == 'q':
        sender.reply("✅ 已取消登录")
        return False

    sender.reply("请输入密码：")
    password = sender.listen(60000)
    if not password or password == 'q':
        sender.reply("✅ 已取消登录")
        return False

    _, _, _, _, _, user_agent, proxy_api = get_config()
    device_id = middleware.bucketGet(BUCKET_DEVICE, account) or gen_device_id()

    sender.reply("⏳ 正在登录无优计划...")
    app = WuYouPlan(account, password, device_id=device_id, ua=user_agent)
    if proxy_api:
        app.session.proxies = {"http": proxy_api, "https": proxy_api}

    app.attest.ensure()
    payload = {"account": account, "password": password, "device_id": device_id, "platform": "android", "app_version": APP_VERSION}
    resp = app._post(LOGIN_URL, payload)
    data = resp.json()
    token = data.get("token")

    used_fallback = False
    if not token and data.get("code") == "device_limit":
        sender.reply("⚠️ 设备数量已达上限，尝试复用已绑定设备...")
        payload["device_id"] = ""
        resp = app._post(LOGIN_URL, payload)
        data = resp.json()
        token = data.get("token")
        used_fallback = True

    if token:
        if used_fallback or not device_id:
            app.token = token
            app.session.headers.update({"authorization": f"Bearer {token}"})
            app.sync_device_from_server()
            device_id = app.device_id
            middleware.bucketSet(BUCKET_DEVICE, account, device_id)

        login_data = {"account": account, "password": password, "token": token, "user": data.get("user", {})}
        return save_user_info(login_data, device_id)
    else:
        sender.reply(f"❌ 登录失败: {str(data)[:300]}")
        return False


# ==================== 查询/管理 ====================

def run_account_tasks(uid):
    """执行单个账号的签到+看广告任务"""
    try:
        token_info_str = middleware.bucketGet(BUCKET_TOKEN, uid)
        if not token_info_str:
            return f"❌ 未找到账号 {uid} 的Token信息"
        token_info = json.loads(token_info_str)
        account = token_info.get("account", "")
        password = token_info.get("password", "")
        device_id = token_info.get("device_id", "")
        alias = token_info.get("alias", "未知用户")

        _, _, _, _, _, user_agent, proxy_api = get_config()
        sender.reply(f"🚀 开始执行账号 {alias}({account}) 的任务...")
        app = WuYouPlan(account, password, device_id=device_id, ua=user_agent)
        if proxy_api:
            app.session.proxies = {"http": proxy_api, "https": proxy_api}

        result = app.run()
        if result:
            return f"✅ 账号 {alias}({account}) 任务完成 | 获得: {result.get('earned', 0)}金币 | 总金币: {result.get('end_coins', 0)}"
        return f"❌ 账号 {alias}({account}) 执行失败"
    except Exception as e:
        return f"❌ 账号 {uid} 执行失败: {str(e)}"


def query_user_info(uid):
    """查询用户信息"""
    try:
        token_info_str = middleware.bucketGet(BUCKET_TOKEN, uid)
        if not token_info_str:
            return f"❌ 未找到账号 {uid} 的Token信息"
        token_info = json.loads(token_info_str)
        account = token_info.get("account", "")
        password = token_info.get("password", "")
        device_id = token_info.get("device_id", "")
        alias = token_info.get("alias", "未知用户")
        auth_time = middleware.bucketGet(BUCKET_AUTH, uid) or '未授权'

        _, _, _, _, _, user_agent, proxy_api = get_config()
        app = WuYouPlan(account, password, device_id=device_id, ua=user_agent)
        if proxy_api:
            app.session.proxies = {"http": proxy_api, "https": proxy_api}

        if not app.login():
            return f"❌ 账号 {alias}({account}) 登录失败"
        user = app.get_user_info()
        wallet = user.get("wallet", {})
        coins = wallet.get("gold_coins", 0)
        level = (user.get("gold_level") or {}).get("name", "")
        max_ads = user.get("max_alliance_ads_per_day", 0)

        return f"""=====账号信息=====
👤 用户: {alias}
📱 UID: {uid}
📱 账号: {account}
💰 金币: {coins}
📊 等级: {level}
📺 广告上限: {max_ads}/天
📅 授权到期: {auth_time}
=================="""
    except Exception as e:
        return f"❌ 查询失败: {str(e)}"


def query_all_accounts():
    """查询用户所有绑定账号的信息"""
    try:
        user_accounts = eval(middleware.bucketGet(BUCKET_USER, userid) or '[]')
        if not user_accounts:
            sender.reply("❌ 您还没有绑定无优计划账号")
            return
        for uid in user_accounts:
            sender.reply(query_user_info(uid))
    except Exception as e:
        sender.reply(f"❌ 查询失败: {str(e)}")


def manage_wuyou():
    """无优计划账号管理"""
    try:
        accounts = eval(middleware.bucketGet(BUCKET_USER, userid) or '[]')
        if not accounts:
            sender.reply("❌ 您还没有绑定无优计划账号")
            return

        sender.reply("""
=====管理选项=====
[1] 账号授权
[2] 账号删除
[3] 立即执行任务
------------------
回复数字选择操作
回复"q"退出""")
        option = sender.listen(60000)
        if not option or option == 'q':
            sender.reply("✅ 已退出管理流程")
            return
        if option not in ['1', '2', '3']:
            sender.reply("❌ 无效的选择")
            return

        account_list = "=====账号列表=====\n[0] 选择全部账号\n"
        for i, uid in enumerate(accounts, 1):
            token_info_str = middleware.bucketGet(BUCKET_TOKEN, uid)
            if token_info_str:
                try:
                    token_info = json.loads(token_info_str)
                    alias = token_info.get("alias", "未知用户")
                    auth_time = middleware.bucketGet(BUCKET_AUTH, uid) or '未授权'
                    account_list += f"[{i}] {alias} ({uid}) - {auth_time}\n"
                except:
                    account_list += f"[{i}] {uid} - 数据错误\n"
            else:
                account_list += f"[{i}] {uid} - 数据错误\n"

        action_text = {'1': '授权', '2': '删除', '3': '执行'}[option]
        sender.reply(f"""{account_list}
------------------
请选择要{action_text}的账号
可以输入多个账号序号，使用英文逗号分隔
例如: 1,3,5
回复"q"退出""")
        choice = sender.listen(60000)
        if not choice or choice == 'q':
            sender.reply("✅ 已退出管理流程")
            return

        selected_uids = []
        try:
            if choice == '0':
                selected_uids = accounts.copy()
            else:
                indices = [int(idx.strip()) - 1 for idx in choice.split(',')]
                for index in indices:
                    if 0 <= index < len(accounts):
                        selected_uids.append(accounts[index])
                    else:
                        sender.reply(f"❌ 无效的选择: {index + 1}")
                        return
            if not selected_uids:
                sender.reply("❌ 未选择任何账号")
                return
        except ValueError:
            sender.reply("❌ 无效的选择格式")
            return

        if option == '1':
            success_count = 0
            for selected_uid in selected_uids:
                if process_auth(selected_uid):
                    success_count += 1
                    token_info_str = middleware.bucketGet(BUCKET_TOKEN, selected_uid)
                    if token_info_str:
                        token_info = json.loads(token_info_str)
                        _, _, _, ql_config, ql_envname, _, _ = get_config()
                        if ql_config:
                            add_to_qinglong(selected_uid, token_info, ql_envname)
            if len(selected_uids) > 1:
                sender.reply(f"✅ 授权完成，成功授权 {success_count}/{len(selected_uids)} 个账号")

        elif option == '2':
            if len(selected_uids) == 1:
                selected_uid = selected_uids[0]
                token_info_str = middleware.bucketGet(BUCKET_TOKEN, selected_uid)
                alias = "未知用户"
                if token_info_str:
                    try:
                        alias = json.loads(token_info_str).get("alias", "未知用户")
                    except:
                        pass
                sender.reply(f"""=====删除确认=====
即将删除以下账号:
👤 用户: {alias}
📱 UID: {selected_uid}
------------------
⚠️ 数据无法恢复
回复"y"确认删除""")
                confirm = sender.listen(60000)
                if confirm.lower() != 'y':
                    sender.reply("✅ 已取消删除")
                    return
                try:
                    accounts.remove(selected_uid)
                    middleware.bucketSet(BUCKET_TOKEN, selected_uid, '')
                    middleware.bucketSet(BUCKET_AUTH, selected_uid, '')
                    if accounts:
                        middleware.bucketSet(BUCKET_USER, userid, str(accounts))
                    else:
                        middleware.bucketDel(BUCKET_USER, userid)
                    _, _, _, ql_config, ql_envname, _, _ = get_config()
                    if ql_config:
                        delete_from_qinglong(selected_uid, ql_envname)
                    sender.reply(f"✅ 已成功删除账号: {alias} ({selected_uid})")
                except Exception as e:
                    sender.reply(f"❌ 删除失败: {str(e)}")
            else:
                account_info = ""
                for i, uid in enumerate(selected_uids, 1):
                    token_info_str = middleware.bucketGet(BUCKET_TOKEN, uid)
                    alias = "未知用户"
                    if token_info_str:
                        try:
                            alias = json.loads(token_info_str).get("alias", "未知用户")
                        except:
                            pass
                    account_info += f"{i}. {alias} ({uid})\n"
                sender.reply(f"""=====删除确认=====
即将删除以下 {len(selected_uids)} 个账号:
{account_info}
------------------
⚠️ 数据无法恢复
回复"y"确认删除""")
                confirm = sender.listen(60000)
                if confirm.lower() != 'y':
                    sender.reply("✅ 已取消删除")
                    return
                success_count = 0
                for selected_uid in selected_uids:
                    try:
                        accounts.remove(selected_uid)
                        middleware.bucketSet(BUCKET_TOKEN, selected_uid, '')
                        middleware.bucketSet(BUCKET_AUTH, selected_uid, '')
                        _, _, _, ql_config, ql_envname, _, _ = get_config()
                        if ql_config:
                            delete_from_qinglong(selected_uid, ql_envname)
                        success_count += 1
                    except Exception as e:
                        print(f"删除账号 {selected_uid} 失败: {str(e)}")
                if accounts:
                    middleware.bucketSet(BUCKET_USER, userid, str(accounts))
                else:
                    middleware.bucketDel(BUCKET_USER, userid)
                sender.reply(f"✅ 删除完成，成功删除 {success_count}/{len(selected_uids)} 个账号")

        elif option == '3':
            for selected_uid in selected_uids:
                sender.reply(run_account_tasks(selected_uid))

    except Exception as e:
        sender.reply(f"❌ 管理失败: {str(e)}")


def show_tutorial():
    """显示无优计划插件使用教程"""
    sender.reply("""=====无优教程=====
📱 用户指令:
• 无优登录 - 绑定无优计划账号
• 无优查询 - 查询账号金币和状态
• 无优管理 - 授权/删除/执行账号
• 无优教程 - 查看本教程
------------------
🔧 管理员指令:
• 无优授权 - 管理员按天数授权
• 无优检测 - 检测过期账号并清理
------------------
💡 登录方式:
📝 账号密码登录（手机号+密码）
💡 登录后自动进入授权流程
------------------
📝 账号获取方式:
1. 下载无优计划APP
   下载链接: http://down.dgccvi.com/index.html
2. 注册必填邀请码: 40UQ4NE
3. 完成实名认证
4. 进入活动页面一次激活账号
------------------
💰 功能说明:
• 账号绑定: 保存账号信息到系统
• 金币查询: 查看金币余额和等级
• 授权管理: 付费使用插件功能
• 青龙提交: 自动提交到青龙容器
• 过期检测: 自动清理过期账号
• 自动签到: 每日签到领金币
• 自动看广告: 看广告赚金币
• 自动领任务: 领取可领取的任务奖励
------------------
🎯 使用流程:
1. 发送"无优登录"绑定账号
2. 输入手机号和密码登录
3. 登录成功后选择授权方式
4. 完成支付获得使用权限
5. 系统自动提交到青龙容器
6. 等待定时任务自动执行
   或发送"无优管理"→3立即执行
------------------
⚠️ 注意事项:
• 授权后才能使用签到功能
• 过期账号会被自动清理
• 支持微信支付和积分兑换
• 管理员可批量授权用户
• User-Agent建议配置真机UA
• 代理API可选配置
==================""")


# ==================== 主入口 ====================
# 获取匹配的指令
rule = middleware.getRule()
matched_rule = None
if rule:
    for r in "^无优登录$|^登录无优$|^无优查询$|^无优管理$|^无优提现$|^无优授权$|^无优检测$|^无优教程$".split('|'):
        if re.match(r, rule):
            matched_rule = r
            break

if matched_rule:
    if matched_rule in ["^无优登录$", "^登录无优$"]:
        process_login()
    elif matched_rule == "^无优查询$":
        query_all_accounts()
    elif matched_rule == "^无优管理$":
        manage_wuyou()
    elif matched_rule == "^无优授权$":
        admin_auth_management()
    elif matched_rule == "^无优检测$":
        result = check_auth_status()
        sender.reply(result)
    elif matched_rule == "^无优提现$":
        sender.reply("⚠️ 提现功能开发中，敬请期待")
    elif matched_rule == "^无优教程$":
        show_tutorial()
else:
    # 定时任务执行：遍历所有已授权用户的所有账号执行签到+看广告
    all_users = middleware.bucketAllKeys(BUCKET_USER)
    if all_users:
        for user_id in all_users:
            try:
                accounts = eval(middleware.bucketGet(BUCKET_USER, user_id) or '[]')
                for uid in accounts:
                    auth_time_str = middleware.bucketGet(BUCKET_AUTH, uid)
                    if not auth_time_str:
                        continue
                    try:
                        auth_date = datetime.strptime(auth_time_str, "%Y-%m-%d").date()
                        if auth_date < datetime.now().date():
                            continue
                    except:
                        continue

                    token_info_str = middleware.bucketGet(BUCKET_TOKEN, uid)
                    if not token_info_str:
                        continue

                    token_info = json.loads(token_info_str)
                    account = token_info.get("account", "")
                    password = token_info.get("password", "")
                    device_id = token_info.get("device_id", "")

                    _, _, _, _, _, user_agent, proxy_api = get_config()

                    app = WuYouPlan(account, password, device_id=device_id, ua=user_agent)
                    if proxy_api:
                        app.session.proxies = {"http": proxy_api, "https": proxy_api}

                    try:
                        result = app.run()
                        print(f"账号 {account} 执行完成: {result}")
                    except Exception as e:
                        print(f"账号 {account} 执行失败: {str(e)}")

                    time.sleep(random.uniform(2, 5))
            except Exception as e:
                print(f"处理用户 {user_id} 出错: {str(e)}")
    else:
        print("无优计划定时任务：没有用户账号")

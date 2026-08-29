#[pin:false]
#[disable:false]
#[public:true]
#[rule: ^(反渣联盟|反渣联盟执行|反渣联盟查询|反渣运行)$]
#[version: 1.2]
#[price: 0.00]
#[cron: 1 0 * * *]
#[title: 反渣联盟]
#[author: 豆包]
#[admin: false]
#[icon: ]
#[description: ai练手反渣联盟自动签到插件<br>指令:反渣联盟、反渣联盟执行、反渣联盟查询、反渣运行<br>格式：账号#密码<br>内置定时签到]
#[param: {"required":false,"key":"dd_FZ_PluginsData.proxy","bool":false,"placeholder":"可选,代理API地址","name":"代理API","desc":"代理API接口地址,支持 ip:port user pass 格式"}]

import re
import middleware
import requests
import json
import time
from datetime import datetime

senderID = middleware.getSenderID()
sender = middleware.Sender(senderID)
userid = sender.getUserID()
uservalue = middleware.bucketGet(bucket='dd_FZ_bind', key=userid)

BASE_URL = "https://www.jishufanzhei.cyou"
ORIGIN = "https://www.jishufanzhei.cyou"
HOST_HEADER = "www.jishufanzhei.cyou"
USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 12; M2004J19C Build/SP1A.210812.016; wv) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 "
    "Chrome/103.0.5060.129 Mobile Safari/537.36 NativeApp/android/1.0.2"
)
X_REQUESTED_WITH = "com.ebrzhepqw.abgmjsdi.pya"
X_CLIENT_TYPE = "app"
X_APP_PLATFORM = "android"
X_APP_VERSION = "1.0.2"

LOGIN_PATH = "/user/login/"
USER_PROFILE_PATH = "/user/usersProfile/"
SIGN_STATUS_PATH = "/user/check-in/"
SIGN_PATH = "/user/check-in/"

REQUEST_TIMEOUT = 15
REQUEST_RETRY = 1


def now_text() -> str:
    return datetime.now().strftime("%H:%M:%S")


def log(msg: str):
    print(f"[{now_text()}] {msg}", flush=True)


def mask_account(account: str) -> str:
    if len(account) >= 8:
        return account[:3] + "****" + account[-4:]
    return account


def parse_accounts(value):
    if not value:
        return []
    try:
        data = json.loads(value.replace("'", '"'))
        if isinstance(data, list):
            return data
    except Exception:
        try:
            data = eval(value)
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []


def load_proxy() -> str:
    return middleware.bucketGet(bucket='dd_FZ_PluginsData', key='proxy') or ''


def parse_proxy_api(text: str):
    text = text.strip()
    if not text:
        return None
    space_parts = text.split()
    if len(space_parts) >= 1 and ':' in space_parts[0]:
        ip_port = space_parts[0].split(':', 1)
        if len(ip_port) == 2:
            try:
                return {
                    "host": ip_port[0],
                    "port": int(ip_port[1]),
                    "username": space_parts[1] if len(space_parts) > 1 else "",
                    "password": space_parts[2] if len(space_parts) > 2 else "",
                }
            except ValueError:
                pass
    if ":" in text:
        parts = text.split(":")
        if len(parts) >= 2:
            try:
                return {
                    "host": parts[0],
                    "port": int(parts[1]),
                    "username": parts[2] if len(parts) > 2 else "",
                    "password": parts[3] if len(parts) > 3 else "",
                }
            except ValueError:
                pass
    match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5})', text)
    if match:
        ip_port = match.group(1)
        host, port = ip_port.split(":")
        return {"host": host, "port": int(port), "username": "", "password": ""}
    return None


def normalize_proxy(proxy: str) -> str:
    proxy = (proxy or "").strip()
    if not proxy:
        return ""
    if proxy.startswith("http"):
        try:
            resp = requests.get(proxy, headers={"User-Agent": "Mozilla/5.0"}, timeout=15, verify=False)
            text = resp.text
            proxy_info = parse_proxy_api(text)
            if proxy_info:
                host = proxy_info["host"]
                port = proxy_info["port"]
                username = proxy_info.get("username", "")
                password = proxy_info.get("password", "")
                if username and password:
                    return f"http://{username}:{password}@{host}:{port}"
                return f"http://{host}:{port}"
        except Exception as e:
            print(f"代理API获取失败: {e}")
            return ""
    if not re.match(r"^[a-zA-Z]+://", proxy):
        proxy = "http://" + proxy
    return proxy


def proxy_dict(proxy: str):
    proxy = normalize_proxy(proxy)
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}


def build_headers(token: str = "", method: str = "GET", referer_path: str = "/monthly-sign-in"):
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "X-Client-Type": X_CLIENT_TYPE,
        "X-App-Platform": X_APP_PLATFORM,
        "X-App-Version": X_APP_VERSION,
        "Referer": ORIGIN + referer_path,
        "Accept-Encoding": "gzip, deflate" if method.upper() != "GET" else "gzip",
        "Host": HOST_HEADER,
    }
    if token:
        headers["Authorization"] = "Bearer " + token.removeprefix("Bearer ").strip()
    if method.upper() != "GET":
        headers["Origin"] = ORIGIN
        headers["X-Requested-With"] = X_REQUESTED_WITH
        headers["Sec-Fetch-Site"] = "same-origin"
        headers["Sec-Fetch-Mode"] = "cors"
        headers["Sec-Fetch-Dest"] = "empty"
        headers["Content-Type"] = "application/json"
    return headers


class FZClient:
    def __init__(self, proxy: str = ""):
        self.proxy = normalize_proxy(proxy)
        self.session = requests.Session()
        self.session.trust_env = False

    def request(self, method: str, path: str, token: str = "", data=None, referer_path: str = "/"):
        method = method.upper()
        url = BASE_URL.rstrip("/") + path
        headers = build_headers(token=token, method=method, referer_path=referer_path)
        last_error = ""
        for attempt in range(REQUEST_RETRY + 1):
            try:
                kwargs = {
                    "headers": headers,
                    "timeout": REQUEST_TIMEOUT,
                    "proxies": proxy_dict(self.proxy),
                    "verify": False,
                }
                if method == "GET":
                    resp = self.session.get(url, **kwargs)
                else:
                    body = json.dumps(data or {}, ensure_ascii=False, separators=(",", ":"))
                    resp = self.session.post(url, data=body.encode("utf-8"), **kwargs)
                text = resp.text or ""
                try:
                    js = resp.json()
                except Exception:
                    js = {"code": -1, "msg": "响应不是 JSON", "data": text[:500]}
                return {"status": resp.status_code, "json": js, "text": text}
            except Exception as exc:
                last_error = str(exc)
                log(f"请求异常，第 {attempt + 1} 次：{last_error}")
                if attempt < REQUEST_RETRY:
                    time.sleep(0.8)
        return {"status": -1, "json": {"code": -1, "msg": last_error, "data": None}, "text": ""}


def step_login(client: FZClient, account: str, password: str):
    res = client.request("POST", LOGIN_PATH, data={"phone_number": account, "password": password}, referer_path="/login")
    js = res["json"]
    token = ""
    if isinstance(js.get("data"), dict):
        token = str(js["data"].get("access") or "")
    ok = js.get("code") == 0 and bool(token)
    return ok, token, js


def step_user_profile(client: FZClient, token: str):
    return client.request("GET", USER_PROFILE_PATH, token=token, referer_path="/")["json"]


def step_sign_status(client: FZClient, token: str):
    return client.request("GET", SIGN_STATUS_PATH, token=token, referer_path="/monthly-sign-in")["json"]


def step_sign_day(client: FZClient, token: str):
    return client.request("POST", SIGN_PATH, token=token, data={}, referer_path="/monthly-sign-in")["json"]


def is_checked(profile_or_status) -> bool:
    text = json.dumps(profile_or_status, ensure_ascii=False, separators=(",", ":"))
    return '"has_checked_in_today":true' in text or '"today_checked":true' in text or "已签到" in text


def get_profile_summary(profile) -> str:
    data = profile.get("data") if isinstance(profile, dict) else {}
    if not isinstance(data, dict):
        return ""
    real_name = data.get("real_name") or ""
    user_id = data.get("id") or ""
    balances = data.get("balances") or []
    balance_texts = []
    if isinstance(balances, list):
        for item in balances:
            if isinstance(item, dict):
                balance_texts.append(f"{item.get('type','余额')}={item.get('amount','')}")
    return f"ID={user_id} 实名={real_name or '未实名'} " + " ".join(balance_texts)


def query_account(account: str) -> dict:
    login_info = middleware.bucketGet(bucket='dd_FZ_login', key=account)
    if not login_info:
        return {"account": account, "success": False, "error": "缺少登录信息", "checked": False, "summary": ""}
    parts = login_info.split("#")
    if len(parts) != 2:
        return {"account": account, "success": False, "error": "格式错误", "checked": False, "summary": ""}
    acc, pwd = parts[0].strip(), parts[1].strip()
    if not acc or not pwd:
        return {"account": account, "success": False, "error": "账号或密码为空", "checked": False, "summary": ""}
    proxy = load_proxy()
    client = FZClient(proxy=proxy)
    try:
        ok, token, login_js = step_login(client, acc, pwd)
        if not ok:
            return {"account": account, "success": False, "error": login_js.get("msg", "登录失败"), "checked": False, "summary": ""}
        profile = step_user_profile(client, token)
        summary = get_profile_summary(profile)
        checked = is_checked(profile)
        if not checked:
            status = step_sign_status(client, token)
            checked = is_checked(status)
        return {
            "account": account,
            "success": True,
            "checked": checked,
            "summary": summary,
            "error": "",
        }
    except Exception as e:
        return {"account": account, "success": False, "error": str(e), "checked": False, "summary": ""}


def execute_account(account: str) -> dict:
    login_info = middleware.bucketGet(bucket='dd_FZ_login', key=account)
    if not login_info:
        return {"account": account, "success": False, "error": "缺少登录信息", "checked": False, "summary": "", "sign_msg": ""}
    parts = login_info.split("#")
    if len(parts) != 2:
        return {"account": account, "success": False, "error": "格式错误", "checked": False, "summary": "", "sign_msg": ""}
    acc, pwd = parts[0].strip(), parts[1].strip()
    if not acc or not pwd:
        return {"account": account, "success": False, "error": "账号或密码为空", "checked": False, "summary": "", "sign_msg": ""}
    proxy = load_proxy()
    client = FZClient(proxy=proxy)
    try:
        ok, token, login_js = step_login(client, acc, pwd)
        if not ok:
            return {"account": account, "success": False, "error": login_js.get("msg", "登录失败"), "checked": False, "summary": "", "sign_msg": ""}
        profile = step_user_profile(client, token)
        summary = get_profile_summary(profile)
        if is_checked(profile):
            return {"account": account, "success": True, "checked": True, "summary": summary, "sign_msg": "资料显示今日已签到"}
        status = step_sign_status(client, token)
        if is_checked(status):
            return {"account": account, "success": True, "checked": True, "summary": summary, "sign_msg": "签到日历显示今日已签到"}
        sign_res = step_sign_day(client, token)
        if sign_res.get("code") == 0:
            sign_msg = f"签到成功：{sign_res.get('msg', '')}"
        else:
            sign_msg = f"签到失败：{sign_res.get('msg', '')}"
        final_profile = step_user_profile(client, token)
        summary = get_profile_summary(final_profile)
        return {
            "account": account,
            "success": True,
            "checked": False,
            "summary": summary,
            "sign_msg": sign_msg,
        }
    except Exception as e:
        return {"account": account, "success": False, "error": str(e), "checked": False, "summary": "", "sign_msg": ""}


def format_query(result: dict) -> str:
    acc = mask_account(result["account"])
    if not result["success"]:
        return f"❌ {acc}\n   查询失败：{result.get('error', '未知')}"
    icon = "✅" if result["checked"] else "⏳"
    lines = [f"{icon} {acc}"]
    if result.get("summary"):
        lines.append(f"   📋 {result['summary']}")
    if result["checked"]:
        lines.append("   📝 今日已签到")
    else:
        lines.append("   📝 今日未签到")
    return "\n".join(lines)


def format_execute(result: dict) -> str:
    acc = mask_account(result["account"])
    if not result["success"]:
        return f"❌ {acc}\n   失败：{result.get('error', '未知')}"
    lines = [f"✅ {acc}"]
    if result.get("summary"):
        lines.append(f"   📋 {result['summary']}")
    if result.get("sign_msg"):
        lines.append(f"   📝 {result['sign_msg']}")
    elif result["checked"]:
        lines.append("   📝 今日已签到，跳过")
    return "\n".join(lines)


def bind():
    sender.reply(
        "🎯 反渣联盟\n"
        "────────────────────\n"
        "📱 格式：账号#密码\n"
        "⚠️ 建议私聊提交\n"
        "────────────────────\n"
        "⭐ 输入 q 退出"
    )
    login_value = sender.input(120000, 1, False)
    if not login_value:
        sender.reply('⏰ 输入超时')
        return
    elif login_value.lower() == 'q':
        sender.reply('已退出')
        return
    if "#" not in login_value:
        sender.reply(
            "❌ 格式错误\n"
            "────────────────────\n"
            "📱 正确格式：账号#密码"
        )
        return
    account, password = login_value.split("#", 1)
    account = account.strip()
    password = password.strip()
    if not account or not password:
        sender.reply("❌ 账号或密码为空")
        return
    middleware.bucketSet(bucket='dd_FZ_login', key=account, value=f"{account}#{password}")
    accounts = parse_accounts(uservalue)
    if account in accounts:
        middleware.bucketSet(bucket='dd_FZ_bind', key=userid, value=json.dumps(accounts, ensure_ascii=False))
        sender.reply(f"✅ {mask_account(account)} 已更新")
    else:
        accounts.append(account)
        middleware.bucketSet(bucket='dd_FZ_bind', key=userid, value=json.dumps(accounts, ensure_ascii=False))
        sender.reply(
            "✅ 绑定成功\n"
            "────────────────────\n"
            f"📱 账号：{mask_account(account)}\n"
            f"📊 共 {len(accounts)} 个账号"
        )


def query_all(accounts: list):
    if not accounts:
        sender.reply("未绑定任何账号")
        return
    sender.reply(f"🔍 查询 {len(accounts)} 个账号...")
    results = []
    for acc in accounts:
        result = query_account(acc)
        results.append(result)
        sender.reply(format_query(result))
        time.sleep(0.5)
    checked = sum(1 for r in results if r.get("checked"))
    total = len(results)
    sender.reply(
        "📊 查询汇总\n"
        "────────────────────\n"
        f"📱 共 {total} 个账号\n"
        f"✅ 已签到 {checked}\n"
        f"⏳ 未签到 {total - checked}"
    )


def execute_all(accounts: list):
    if not accounts:
        sender.reply("未绑定任何账号")
        return
    sender.reply(f"🚀 执行 {len(accounts)} 个账号...")
    results = []
    for acc in accounts:
        result = execute_account(acc)
        results.append(result)
        sender.reply(format_execute(result))
        time.sleep(1.0)
    success = sum(1 for r in results if r["success"])
    checked = sum(1 for r in results if r.get("checked"))
    fail = len(results) - success
    sender.reply(
        "📊 执行汇总\n"
        "────────────────────\n"
        f"📱 账号 {len(results)} 个\n"
        f"✅ 成功 {success}\n"
        f"❌ 失败 {fail}\n"
        f"📝 已签到 {checked}"
    )


def Administration():
    global uservalue
    base_message = (
        "🎯 反渣联盟\n"
        "────────────────────\n"
        "1️⃣  提交账号\n"
        "2️⃣  执行签到\n"
        "3️⃣  删除账号\n"
        "4️⃣  查看账号\n"
        "5️⃣  查询状态 🔍"
    )
    base_message += "\n────────────────────\n⚠️ 输入 q 退出"
    sender.reply(base_message)
    choice = sender.input(60000, 1, False)
    if not choice or choice.lower() == 'q':
        sender.reply('已退出')
        return
    try:
        choice = int(choice)
    except ValueError:
        sender.reply('❌ 请输入数字')
        return
    accounts = parse_accounts(uservalue)
    if choice == 1:
        bind()
        return
    elif choice == 2:
        if not accounts:
            sender.reply("未绑定任何账号")
            return
        sender.reply(
            "📱 确认执行\n"
            "────────────────────\n"
            f"📊 账号数：{len(accounts)} 个\n"
            "❓ 是否立即执行？\n"
            "────────────────────\n"
            "[y]是  [n]否"
        )
        confirm = sender.input(60000, 1, False)
        if not confirm or confirm.lower() != 'y':
            sender.reply('已取消')
            return
        execute_all(accounts)
        return
    elif choice == 3:
        if not accounts:
            sender.reply("未绑定任何账号")
            return
        msg = "🗑️ 删除账号\n────────────────────\n"
        for i, acc in enumerate(accounts, 1):
            msg += f"{i}. {mask_account(acc)}\n"
        msg += "────────────────────\n输入 q 取消"
        sender.reply(msg)
        acc_choice = sender.input(60000, 1, False)
        if not acc_choice or acc_choice.lower() == 'q':
            sender.reply('已取消')
            return
        try:
            idx = int(acc_choice)
            if idx < 1 or idx > len(accounts):
                sender.reply('❌ 序号无效')
                return
        except ValueError:
            sender.reply('❌ 请输入数字')
            return
        selected = accounts[idx - 1]
        sender.reply(
            "⚠️ 删除确认\n"
            "────────────────────\n"
            f"📱 账号：{mask_account(selected)}\n"
            "❓ 确认删除？\n"
            "────────────────────\n"
            "[y]确认  [n]取消"
        )
        confirm = sender.input(60000, 1, False)
        if confirm and confirm.lower() == 'y':
            try:
                accounts.remove(selected)
                if accounts:
                    middleware.bucketSet(bucket='dd_FZ_bind', key=userid, value=json.dumps(accounts, ensure_ascii=False))
                else:
                    middleware.bucketDel(bucket='dd_FZ_bind', key=userid)
                middleware.bucketDel(bucket='dd_FZ_login', key=selected)
                sender.reply(f'✅ {mask_account(selected)} 已删除')
            except Exception as e:
                sender.reply(f'❌ 删除失败：{str(e)}')
        else:
            sender.reply('已取消')
    elif choice == 4:
        if not accounts:
            sender.reply("未绑定任何账号")
            return
        msg = "📋 我的账号\n────────────────────\n"
        for i, acc in enumerate(accounts, 1):
            msg += f"{i}. {mask_account(acc)}\n"
        msg += f"────────────────────\n共 {len(accounts)} 个账号"
        sender.reply(msg)
        return
    elif choice == 5:
        if not accounts:
            sender.reply("未绑定任何账号")
            return
        query_all(accounts)
        return
    else:
        sender.reply('❌ 无效选项')


def main():
    global uservalue
    uservalue = middleware.bucketGet(bucket='dd_FZ_bind', key=userid)
    message = sender.getMessage()
    if message == "反渣联盟查询":
        accounts = parse_accounts(uservalue)
        if not accounts:
            sender.reply("未绑定任何账号")
            return
        query_all(accounts)
        return
    if message == "反渣联盟执行":
        accounts = parse_accounts(uservalue)
        if not accounts:
            sender.reply("未绑定任何账号")
            return
        execute_all(accounts)
        return
    if message == "反渣运行":
        accounts = parse_accounts(uservalue)
        if not accounts:
            sender.reply("未绑定任何账号")
            return
        sender.reply(f"🚀 一键运行 {len(accounts)} 个账号...")
        execute_all(accounts)
        return
    Administration()


main()
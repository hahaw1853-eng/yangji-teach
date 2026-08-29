#[pin:false]
#[disable:false]
#[public:true]
#[rule: ^(无忧计划|无忧计划执行|无忧计划任务检测|无忧运行)$]
#[version: 5.5]
#[price: 0.00]
#[cron: 0 8 * * *]
#[title: 无忧计划]
#[author: 豆包]
#[admin: false]
#[icon: https://img.cdn1.vip/i/6a8e00f74bda3_1787691255.webp]
#[description: 无忧计划自动任务插件，内置每日签到与看广告赚金币！<br>指令:无忧计划、无忧计划执行、无忧计划任务检测、无忧运行<br>格式：手机号#密码#UA(可选)<br>内置定时检测与自动执行任务<br>增强代理与UA池<br>v5.5: 全体执行支持全系统账号]
#[param: {"required":false,"key":"dd_WuYou_PluginsData.proxy_api","bool":false,"placeholder":"可选,代理API地址","name":"代理API","desc":"代理API接口地址,每个账号独立获取代理"}]

import re
import middleware
import requests
import json
import hashlib
import hmac
import urllib.parse
from datetime import datetime
import random
import secrets
import string
import time
import sys
import urllib3
from urllib3.exceptions import InsecureRequestWarning
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings(InsecureRequestWarning)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ==================== 增强UA池（20个真机Android WebView UA）====================
BUILTIN_UAS = [
    # 华为
    "Mozilla/5.0 (Linux; Android 9; ELE-AL00 Build/HUAWEIELE-AL00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/66.0.3359.126 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; ELE-AL00 Build/HUAWEIELE-AL00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/76.0.3809.89 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; EML-AL00 Build/HUAWEIEML-AL00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.99 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; SEA-AL10 Build/HUAWEISEA-AL10; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.99 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; HMA-AL00 Build/HUAWEIHMA-AL00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/79.0.3945.93 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; OXF-AN10 Build/HUAWEIOXF-AN10; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/76.0.3809.89 Mobile Safari/537.36",
    # 荣耀
    "Mozilla/5.0 (Linux; Android 10; HLK-AL00 Build/HONORHLK-AL00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.99 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 9; JSN-AL00a Build/HONORJSN-AL00a; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/76.0.3809.89 Mobile Safari/537.36",
    # 小米
    "Mozilla/5.0 (Linux; Android 11; MI 9 Build/RKQ1.200826.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.99 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; Mi 10 Build/QKQ1.191117.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/76.0.3809.89 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; M2011K2C Build/RKQ1.200928.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.99 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; MI 8 SE Build/QKQ1.190828.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.99 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 9; MIX 2S Build/PKQ1.180729.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/76.0.3809.89 Mobile Safari/537.36",
    # 红米
    "Mozilla/5.0 (Linux; Android 11; 21091116C Build/RP1A.200720.011; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.99 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; M2004J7BC Build/RP1A.200720.011; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.99 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 9; Redmi Note 8 Pro Build/PPR1.180610.011; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/66.0.3359.126 Mobile Safari/537.36",
    # OPPO / vivo / 一加
    "Mozilla/5.0 (Linux; Android 9; PACM00 Build/PPR1.180610.011; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/76.0.3809.89 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 8.1.0; OPPO R11s Build/OPM1.171019.011; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/76.0.3809.89 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 9; V1813BT Build/PKQ1.181030.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/76.0.3809.89 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; GM1910 Build/QKQ1.190716.003; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/78.0.3904.96 Mobile Safari/537.36",
]

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

ATTEST_KEY = "aac0ab40d0612c8549f88e87e476751a348f910156e9e73590ddaece2a4288d5"

PROXY_RETRY_TIMES = 3
PROXY_VALIDATE_URL = "http://httpbin.org/ip"
ENABLE_DIRECT_FALLBACK = True
REQUEST_TIMEOUT = 30

senderID = middleware.getSenderID()
sender = middleware.Sender(senderID)
userid = sender.getUserID()
uservalue = middleware.bucketGet(bucket='dd_WuYou_bind', key=userid)


def hmac_hex(key: str, msg: str) -> str:
    return hmac.new(key.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compact_json(payload) -> bytes:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def gen_device_id() -> str:
    rand = "".join(random.choice(string.digits + string.ascii_lowercase) for _ in range(10))
    return f"{int(time.time() * 1000)}-{rand}"


def load_device_store() -> dict:
    store_str = middleware.bucketGet(bucket='dd_WuYou_device', key='store')
    if not store_str:
        return {}
    try:
        store = json.loads(store_str)
        if isinstance(store, dict):
            return store
    except Exception:
        pass
    return {}


def save_device_store(store: dict):
    try:
        middleware.bucketSet(bucket='dd_WuYou_device', key='store', value=json.dumps(store, ensure_ascii=False))
    except Exception as e:
        print(f"保存 device_id 失败: {e}")


def load_proxy_api() -> str:
    return middleware.bucketGet(bucket='dd_WuYou_PluginsData', key='proxy_api') or ''


def parse_account_info(login_info: str):
    parts = login_info.split('#')
    if len(parts) >= 3:
        return parts[0], parts[1], '#'.join(parts[2:])
    elif len(parts) == 2:
        return parts[0], parts[1], ""
    return parts[0], "", ""


def mask_account(account: str) -> str:
    if len(account) >= 7:
        return account[:3] + "****" + account[-4:]
    return account


def get_account_owner(account: str) -> str:
    return middleware.bucketGet(bucket='dd_WuYou_owner', key=account) or ""


def set_account_owner(account: str, owner_id: str):
    middleware.bucketSet(bucket='dd_WuYou_owner', key=account, value=owner_id)


def remove_account_owner(account: str):
    middleware.bucketDel(bucket='dd_WuYou_owner', key=account)


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


# ==================== 全局用户注册（全体执行用）====================
def register_user(user_id: str):
    """将用户ID注册到全局用户列表，用于全体执行时遍历"""
    users_str = middleware.bucketGet(bucket='dd_WuYou_global', key='registered_users') or '[]'
    try:
        users = json.loads(users_str)
        if not isinstance(users, list):
            users = []
    except Exception:
        users = []
    if user_id not in users:
        users.append(user_id)
        try:
            middleware.bucketSet(bucket='dd_WuYou_global', key='registered_users', value=json.dumps(users, ensure_ascii=False))
        except Exception as e:
            print(f"注册全局用户失败: {e}")


def get_all_accounts_global() -> list:
    """获取系统中所有用户绑定的所有账号（去重）"""
    users_str = middleware.bucketGet(bucket='dd_WuYou_global', key='registered_users') or '[]'
    try:
        users = json.loads(users_str)
        if not isinstance(users, list):
            users = []
    except Exception:
        users = []

    all_accounts = []
    for uid in users:
        user_value = middleware.bucketGet(bucket='dd_WuYou_bind', key=uid)
        user_accounts = parse_accounts(user_value)
        for acc in user_accounts:
            if acc and acc not in all_accounts:
                all_accounts.append(acc)
    return all_accounts


class ProxyManager:
    def __init__(self, api_url: str, account_name: str = ""):
        self.api_url = api_url
        self.account_name = account_name
        self.current_proxy = None
        self.proxy_ip = "-"
        self.proxy_type = "http"

    def _parse_proxy_response(self, text):
        if not isinstance(text, str):
            text = json.dumps(text, ensure_ascii=False)
        text = text.strip()
        if not text:
            return None
        try:
            data = json.loads(text)
            proxy_obj = None
            if isinstance(data.get("data"), list) and data["data"]:
                proxy_obj = data["data"][0]
            elif isinstance(data.get("data"), dict):
                proxy_obj = data["data"]
            elif data.get("ip") and data.get("port"):
                proxy_obj = data
            elif isinstance(data.get("result"), dict):
                proxy_obj = data["result"]
            if proxy_obj:
                host = proxy_obj.get("ip") or proxy_obj.get("host")
                port = proxy_obj.get("port")
                if host and port:
                    return {
                        "host": str(host),
                        "port": int(port),
                        "username": proxy_obj.get("user") or proxy_obj.get("username") or "",
                        "password": proxy_obj.get("pass") or proxy_obj.get("password") or "",
                    }
        except Exception:
            pass
        # 支持 ip:port username password（空格分隔，品赞格式）
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
        # 支持 ip:port:user:pass（冒号分隔）
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

    def _build_proxy_dict(self, proxy_info: dict) -> dict:
        if not proxy_info:
            return None
        host = proxy_info["host"]
        port = proxy_info["port"]
        username = proxy_info.get("username", "")
        password = proxy_info.get("password", "")
        auth = ""
        if username and password:
            auth = f"{urllib.parse.quote(username)}:{urllib.parse.quote(password)}@"
        scheme = "socks5" if self.proxy_type == "socks5" else "http"
        proxy_url = f"{scheme}://{auth}{host}:{port}"
        return {"http": proxy_url, "https": proxy_url}

    def _validate_proxy(self, proxies: dict) -> bool:
        if not proxies:
            return False
        try:
            resp = requests.get(PROXY_VALIDATE_URL, proxies=proxies, timeout=15)
            if resp.status_code == 200:
                try:
                    self.proxy_ip = resp.json().get("origin", "未知")
                except Exception:
                    self.proxy_ip = "未知"
                return True
        except Exception:
            pass
        return False

    def refresh(self):
        if not self.api_url:
            return None
        print(f"🌐 [代理] {self.account_name} 正在获取代理...")
        for index in range(1, PROXY_RETRY_TIMES + 1):
            try:
                resp = requests.get(self.api_url, timeout=15)
                proxy_info = self._parse_proxy_response(resp.text)
                if not proxy_info:
                    print(f"⚠️ [代理] 第 {index} 次解析失败")
                    continue
                print(f"✅ [代理] 提取到 {proxy_info['host']}:{proxy_info['port']}")
                proxies = self._build_proxy_dict(proxy_info)
                if self._validate_proxy(proxies):
                    print(f"✅ [代理] 验证通过，出口 IP: {self.proxy_ip}")
                    self.current_proxy = proxies
                    return proxies
                print(f"⚠️ [代理] 第 {index} 次代理不可用")
            except Exception as exc:
                print(f"⚠️ [代理] 第 {index} 次获取异常: {exc}")
            if index < PROXY_RETRY_TIMES:
                time.sleep(2)
        print("⚠️ [代理] 获取失败")
        self.current_proxy = None
        self.proxy_ip = "-"
        return None

    def request_with_proxy(self, method, url, **kwargs):
        kwargs.setdefault("timeout", REQUEST_TIMEOUT)
        if self.current_proxy:
            try:
                return requests.request(method, url, proxies=self.current_proxy, **kwargs)
            except Exception as exc:
                print(f"⚠️ [代理] 请求失败: {exc}")
                if ENABLE_DIRECT_FALLBACK:
                    print("🔁 [兜底] 切换直连重试")
                else:
                    raise
        session = requests.Session()
        session.trust_env = False
        return session.request(method, url, **kwargs)


class AppAttest:
    def __init__(self, http: requests.Session, device_id: str, log):
        self.http = http
        self.device_id = device_id
        self.log = log
        self.session_id = None
        self.session_secret = None
        self.expires_at = 0

    def has_session(self) -> bool:
        return bool(self.session_id and self.session_secret and time.time() < self.expires_at)

    def ensure(self, force: bool = False) -> bool:
        if not force and self.has_session():
            return True
        try:
            ts = str(int(time.time()))
            nonce = secrets.token_hex(16)
            native_proof = hmac_hex(ATTEST_KEY, f"attest\n{ts}\n{nonce}\n{self.device_id}")
            payload = {
                "integrity_token": "",
                "device_id": self.device_id,
                "ts": ts,
                "nonce": nonce,
                "native_proof": native_proof,
            }
            resp = self.http.post(
                ATTEST_URL,
                data=compact_json(payload),
                headers={"Content-Type": "application/json"},
                verify=False,
                timeout=15,
            )
            data = resp.json()
            if data.get("ok") and data.get("session_id") and data.get("session_secret"):
                self.session_id = data["session_id"]
                self.session_secret = data["session_secret"]
                self.expires_at = time.time() + int(data.get("expires_in", 1800)) - 60
                return True
            self.log(f"attest 失败: {str(data)[:200]}")
        except Exception as e:
            self.log(f"attest 异常: {e}")
        return False

    def sign_headers(self, method: str, url: str, body: bytes) -> dict:
        if not self.has_session():
            return {}
        ts = str(int(time.time()))
        nonce = secrets.token_hex(16)
        path = urllib.parse.urlsplit(url).path or "/"
        body_hash = sha256_hex(body)
        msg = f"{method.upper()}\n{path}\n{ts}\n{nonce}\n{body_hash}"
        sign = hmac_hex(self.session_secret, msg)
        return {
            "X-App-Session": self.session_id,
            "X-App-Ts": ts,
            "X-App-Nonce": nonce,
            "X-App-Sign": sign,
        }


class WuYouPlan:
    def __init__(self, account, password, device_id="", ua="", proxy_api=""):
        self.account = account
        self.password = password
        self.session = requests.Session()
        self.session.verify = False
        self.ua = ua or random.choice(BUILTIN_UAS)
        self.proxy_api = proxy_api
        self.proxy_mgr = ProxyManager(self.proxy_api, account)
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
        self.device_id = device_id or self._load_or_create_device_id()
        self.attest = AppAttest(self.session, self.device_id, self.log)
        self.token = None
        self.user_id = None
        self.user_info = None
        self.total_coins_earned = 0
        self.result_lines = []
        self.ad_error = ""
        self.checkin_status = ""

    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}"
        self.result_lines.append(line)
        print(line)

    def _load_or_create_device_id(self) -> str:
        store = load_device_store()
        dev = store.get(self.account)
        if dev:
            return dev
        dev = gen_device_id()
        store[self.account] = dev
        save_device_store(store)
        return dev

    def _request(self, method: str, url: str, payload=None, params=None, retry_on_app_required=True):
        body = b"" if payload is None else compact_json(payload)
        # 合并 session 默认头（含 authorization）+ attest 签名头
        headers = dict(self.session.headers)
        headers.update(self.attest.sign_headers(method, url, body))
        if payload is not None:
            headers["Content-Type"] = "application/json"
        resp = self.proxy_mgr.request_with_proxy(
            method, url,
            data=body if payload is not None else None,
            params=params, headers=headers,
        )
        if retry_on_app_required and resp.status_code == 403:
            try:
                err = resp.json()
            except Exception:
                err = {}
            if err.get("code") == "app_required":
                self.log("收到 app_required，重新进行 attest 签名...")
                if self.attest.ensure(force=True):
                    return self._request(method, url, payload, params, retry_on_app_required=False)
        return resp

    def _get(self, url, params=None):
        return self._request("GET", url, params=params)

    def _post(self, url, payload=None, params=None):
        return self._request("POST", url, payload=payload if payload is not None else {}, params=params)

    def login(self):
        self.attest.ensure()
        payload = {
            "account": self.account,
            "password": self.password,
            "device_id": self.device_id,
            "platform": "android",
            "app_version": APP_VERSION,
        }
        resp = self._post(LOGIN_URL, payload)
        try:
            data = resp.json()
        except Exception:
            data = {}
        token = data.get("token")
        used_fallback = False
        if not token and data.get("code") == "device_limit":
            self.log("设备数量已达上限，尝试用空 device_id 登录...")
            payload["device_id"] = ""
            resp = self._post(LOGIN_URL, payload)
            try:
                data = resp.json()
            except Exception:
                data = {}
            token = data.get("token")
            used_fallback = True
        if token:
            self.token = token
            self.user_info = data.get("user", {})
            self.user_id = self.user_info.get("id")
            self.session.headers.update({"authorization": f"Bearer {self.token}"})
            self.log(f"登录成功 | 用户ID: {self.user_id}")
            if used_fallback or not self.device_id:
                if self.sync_device_from_server():
                    self.log(f"已回填服务端绑定设备 device_id: {self.device_id}")
                else:
                    self.log("未能回填 device_id，广告流程可能受限")
            return True
        else:
            self.log(f"登录失败: {str(data)[:300]}")
            return False

    def sync_device_from_server(self) -> bool:
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
                store = load_device_store()
                store[self.account] = self.device_id
                save_device_store(store)
                return True
        except Exception as e:
            self.log(f"回填 device_id 失败: {e}")
        return False

    def get_user_info(self):
        resp = self._get(ME_URL, params={
            "device_id": self.device_id,
            "platform": "android",
            "app_version": APP_VERSION,
        })
        try:
            return resp.json().get("user", {})
        except Exception:
            return {}

    def get_user_devices(self):
        resp = self._get(USER_DEVICES_URL, params={"device_id": self.device_id})
        try:
            return resp.json()
        except Exception:
            return {}

    def get_daily_tasks(self):
        resp = self._get(DAILY_TASKS_URL)
        try:
            return resp.json()
        except Exception:
            return {}

    def checkin(self):
        self.log("执行每日签到...")
        resp = self._post(CHECKIN_URL)
        try:
            data = resp.json()
        except Exception:
            data = {}
        coins = data.get("coins_awarded", 0)
        day = data.get("day_number", 0)
        msg = data.get("message", "")
        self.total_coins_earned += coins
        self.log(f"  {msg} | 连续第{day}天 | +{coins}金币")
        self.log("领取签到奖励...")
        try:
            resp2 = self._post(f"{DAILY_TASKS_URL}/daily_checkin/claim")
            data2 = resp2.json()
            if data2.get("ok"):
                claim_coins = data2.get("coins", 0)
                claim_msg = data2.get("message", "")
                self.total_coins_earned += claim_coins
                self.log(f"  {claim_msg} | +{claim_coins}金币")
                self.checkin_status = f"已领+{claim_coins}"
            else:
                err = str(data2)[:100]
                self.log(f"  领取签到奖励失败: {err}")
                if "已领取" in err:
                    self.checkin_status = "已领取"
                else:
                    self.checkin_status = "领取失败"
        except Exception as e:
            self.log(f"  领取签到奖励异常: {e}")
            self.checkin_status = "异常"
        return data

    def claim_task(self, task_key):
        url = f"{DAILY_TASKS_URL}/{task_key}/claim"
        try:
            resp = self._post(url)
            data = resp.json()
            if data.get("ok"):
                coins = data.get("coins", 0)
                msg = data.get("message", "")
                self.total_coins_earned += coins
                self.log(f"  {msg} | +{coins}金币")
            else:
                self.log(f"  领取失败 ({task_key}): {str(data)[:200]}")
            return data
        except Exception as e:
            self.log(f"  领取异常 ({task_key}): {e}")
            return {}

    def get_ads_info(self):
        resp = self._get(ADS_LIST_URL, params={"device_id": self.device_id})
        try:
            return resp.json()
        except Exception:
            return {}

    def start_ad_session(self):
        payload = {"device_id": self.device_id, "client": "app"}
        try:
            resp = self._post(ADS_SESSION_START_URL, payload)
            return resp.json()
        except Exception as e:
            return {"ok": False, "message": f"请求异常: {e}"}

    def send_heartbeat(self, play_token, progress_seconds):
        payload = {"play_token": play_token, "progress_seconds": progress_seconds}
        try:
            resp = self._post(ADS_HEARTBEAT_URL, payload)
            return resp.json()
        except Exception:
            return {}

    def complete_ad_session(self, play_token, progress_seconds):
        payload = {"play_token": play_token, "progress_seconds": progress_seconds}
        try:
            resp = self._post(ADS_COMPLETE_URL, payload)
            return resp.json()
        except Exception:
            return {}

    def watch_ads(self, account_max_views=None):
        self.log("开始广告流程...")
        ads_info = self.get_ads_info()
        enabled = ads_info.get("enabled", False)
        max_views = ads_info.get("max_views_per_day", 20)
        if account_max_views:
            max_views = min(max_views, account_max_views)
        items = ads_info.get("items", [])
        heartbeat_interval = ads_info.get("heartbeat_interval", 30)
        if not enabled:
            self.log("  广告功能未启用")
            self.ad_error = "未启用"
            return 0, 0
        if max_views <= 0:
            self.log("  今日广告次数已用完")
            self.ad_error = "次数已用完"
            return 0, 0
        self.log(f"  今日可看 {max_views} 次 | 共 {len(items)} 个广告")
        success_count = 0
        fail_count = 0
        for i in range(max_views):
            self.log(f"第 {i+1}/{max_views} 个广告")
            session_data = self.start_ad_session()
            if not session_data.get("ok"):
                msg = session_data.get("message") or str(session_data)[:200]
                self.log(f"  启动广告会话失败: {msg}")
                self.ad_error = "已达上限" if "上限" in msg else "暂无可看"
                fail_count += 1
                break
            sess = session_data.get("session", {})
            play_token = sess.get("play_token")
            duration = sess.get("duration_seconds", 30)
            reward = sess.get("reward_coins", 0)
            hb_interval = sess.get("heartbeat_interval", heartbeat_interval)
            ad_info = sess.get("ad", {})
            self.log(f"  {ad_info.get('title', '未知')} | 时长: {duration}秒 | 奖励: {reward}金币")
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
                self.log(f"  心跳 | 进度: {round(elapsed, 2)}/{duration}秒")
                next_hb = hb_interval + random.uniform(0.1, 0.3)
            final_progress = round(duration + random.uniform(0.05, 0.3), 2)
            self.send_heartbeat(play_token, final_progress)
            time.sleep(random.uniform(0.5, 1.2))
            self.send_heartbeat(play_token, final_progress)
            self.log("  完成观看，领取奖励...")
            complete_data = self.complete_ad_session(play_token, final_progress)
            if complete_data.get("ok"):
                coins = complete_data.get("gold_coins", 0)
                msg = complete_data.get("message", "")
                self.total_coins_earned += coins
                success_count += 1
                self.log(f"  成功 | {msg} | +{coins}金币 | 累计: {self.total_coins_earned}金币")
            else:
                err_msg = complete_data.get("message", "领取失败")
                self.log(f"  失败 | {err_msg}")
                fail_count += 1
            if i < max_views - 1:
                interval = complete_data.get("next_request_available_in") or session_data.get("request_interval_seconds") or random.randint(3, 5)
                self.log(f"  等待 {interval} 秒后下一个...")
                time.sleep(interval)
        self.log(f"广告汇总: 成功 {success_count} 次 | 失败 {fail_count} 次 | 累计 +{self.total_coins_earned}金币")
        if not self.ad_error:
            if success_count == 0 and fail_count > 0:
                self.ad_error = "全部失败"
            else:
                self.ad_error = f"{success_count}次成功"
        return success_count, fail_count

    def run(self) -> dict:
        self.log(f"========== 账号: {mask_account(self.account)} ==========")
        if self.proxy_api:
            proxy = self.proxy_mgr.refresh()
            if proxy:
                self.log(f"已获取代理 | 出口IP: {self.proxy_mgr.proxy_ip}")
            else:
                self.log("未获取到可用代理，将直连执行")
        if not self.login():
            return {
                "account": self.account,
                "success": False,
                "error": "登录失败",
                "logs": self.result_lines,
                "earned": 0,
                "total": 0,
                "ad_error": "",
                "checkin": "",
                "proxy_ip": self.proxy_mgr.proxy_ip,
            }
        try:
            user = self.get_user_info()
            nickname = user.get("nickname", "")
            wallet = user.get("wallet", {})
            start_coins = wallet.get("gold_coins", 0)
            account_max_views = user.get("max_alliance_ads_per_day")
            level = (user.get("gold_level") or {}).get("name", "")
            self.log(f"用户: {nickname} | 等级: {level} | 金币: {start_coins} | 广告上限: {account_max_views}/天")
        except Exception as e:
            start_coins = 0
            account_max_views = None
            nickname = ""
            self.log(f"获取用户信息失败: {e}")
        self.log("获取任务列表...")
        tasks_data = self.get_daily_tasks()
        self.checkin()
        try:
            devices_data = self.get_user_devices()
            max_devices = devices_data.get("max_devices", 0)
            used = devices_data.get("devices_used", 0)
            self.log(f"设备: {used}/{max_devices}")
        except Exception as e:
            self.log(f"查询设备信息失败: {e}")
        self.watch_ads(account_max_views=account_max_views)
        tasks_data = self.get_daily_tasks()
        claimed_tasks = []
        for task in tasks_data.get("tasks", []):
            task_key = task.get("task_key", "")
            if task.get("is_completed") and not task.get("is_claimed"):
                result = self.claim_task(task_key)
                claimed_tasks.append(task.get("title", task_key))
        try:
            user2 = self.get_user_info()
            end_coins = user2.get("wallet", {}).get("gold_coins", 0)
            earned = end_coins - start_coins
            self.log(f"任务完毕 | 本次获得: {earned}金币 | 总金币: {end_coins}")
        except Exception as e:
            end_coins = start_coins
            earned = 0
            self.log(f"查询最终余额失败: {e}")
        return {
            "account": self.account,
            "success": True,
            "nickname": nickname,
            "start_coins": start_coins,
            "end_coins": end_coins,
            "earned": earned,
            "total": end_coins,
            "tasks": tasks_data,
            "claimed_tasks": claimed_tasks,
            "logs": self.result_lines,
            "ad_error": self.ad_error,
            "checkin": self.checkin_status,
            "proxy_ip": self.proxy_mgr.proxy_ip,
        }


def format_result(result: dict) -> str:
    acc = mask_account(result["account"])
    if not result["success"]:
        return f"❌ {acc}\n   失败：{result.get('error', '未知')}"
    lines = []
    nickname = result.get("nickname", "")
    if nickname:
        lines.append(f"✅ {acc} 〔{nickname}〕")
    else:
        lines.append(f"✅ {acc}")
    earned = result.get("earned", 0)
    total = result.get("total", 0)
    lines.append(f"   💰 收益 +{earned}（总{total}）")
    proxy_ip = result.get("proxy_ip", "-")
    if proxy_ip and proxy_ip != "-":
        lines.append(f"   🌐 代理 {proxy_ip}")
    ad_err = result.get("ad_error", "")
    if ad_err:
        if "上限" in ad_err or "已用完" in ad_err:
            lines.append("   📺 广告 已达上限")
        elif "未启用" in ad_err:
            lines.append("   📺 广告 未启用")
        else:
            lines.append(f"   📺 广告 {ad_err}")
    checkin = result.get("checkin", "")
    if checkin:
        lines.append(f"   📝 签到 {checkin}")
    tasks = result.get("tasks", {})
    task_list = tasks.get("tasks", [])
    if task_list:
        completed = sum(1 for t in task_list if t.get("is_completed"))
        lines.append(f"   📋 任务 {completed}/{len(task_list)}")
    return "\n".join(lines)


def format_summary(results: list, done_count: int = 0) -> str:
    total = len(results)
    success = sum(1 for r in results if r.get("success") and not r.get("all_done"))
    fail = sum(1 for r in results if not r.get("success"))
    earned = sum(r.get("earned", 0) for r in results if r.get("success") and not r.get("all_done"))
    lines = [
        "📊 执行汇总",
        "────────────────────",
        f"📱 账号 {total + done_count} 个",
    ]
    if done_count > 0:
        lines.append(f"✅ 已完成 {done_count}")
    lines.extend([
        f"✅ 本次成功 {success}",
        f"❌ 失败 {fail}",
        f"💰 总收益 +{earned}",
    ])
    fails = [r for r in results if not r.get("success")]
    if fails:
        lines.append("")
        lines.append("⚠️ 失败详情")
        for r in fails:
            lines.append(f"   {mask_account(r['account'])}：{r.get('error', '未知')}")
    return "\n".join(lines)


def bind():
    sender.reply(
        "🎯 无忧计划\n"
        "────────────────────\n"
        "📱 格式：手机号#密码#UA\n"
        "💡 UA 可省略，自动使用内置真机UA\n"
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
    parts = login_value.split('#')
    if len(parts) < 2:
        sender.reply(
            "❌ 格式错误\n"
            "────────────────────\n"
            "📱 正确格式：手机号#密码#UA"
        )
        return
    account = parts[0]
    password = parts[1]
    ua = '#'.join(parts[2:]) if len(parts) >= 3 else ""
    if not ua:
        sender.reply(
            "📱 未检测到自定义UA\n"
            "────────────────────\n"
            "❓ 是否使用内置随机UA？\n"
            "[y]是  [n]否"
        )
        confirm = sender.input(60000, 1, False)
        if confirm and confirm.lower() == 'y':
            ua = random.choice(BUILTIN_UAS)
            sender.reply("✅ 已使用内置UA（20个真机UA池）")
        else:
            sender.reply(
                "请重新提交\n"
                "格式：手机号#密码#UA"
            )
            return
    full_info = f"{account}#{password}#{ua}"
    middleware.bucketSet(bucket='dd_WuYou_login', key=account, value=full_info)
    set_account_owner(account, userid)
    accounts = parse_accounts(uservalue)
    if account in accounts:
        middleware.bucketSet(bucket='dd_WuYou_bind', key=userid, value=json.dumps(accounts, ensure_ascii=False))
        sender.reply(f"✅ {mask_account(account)} 已更新")
    else:
        accounts.append(account)
        middleware.bucketSet(bucket='dd_WuYou_bind', key=userid, value=json.dumps(accounts, ensure_ascii=False))
        sender.reply(
            "✅ 绑定成功\n"
            "────────────────────\n"
            f"📱 账号：{mask_account(account)}\n"
            f"📊 共 {len(accounts)} 个账号"
        )
    # ★ 注册到全局用户列表，供全体执行遍历
    register_user(userid)


def query_account(account: str) -> dict:
    """直连查询账号今日状态，不走代理"""
    login_info = middleware.bucketGet(bucket='dd_WuYou_login', key=account)
    if not login_info:
        return {"account": account, "success": False, "error": "缺少登录信息", "nickname": "", "total": 0, "checkin": "未知", "ad_status": "未知", "task_done": 0, "task_total": 0, "all_done": False}
    acc, pwd, ua = parse_account_info(login_info)
    if not pwd:
        return {"account": account, "success": False, "error": "缺少密码", "nickname": "", "total": 0, "checkin": "未知", "ad_status": "未知", "task_done": 0, "task_total": 0, "all_done": False}
    if not ua:
        ua = random.choice(BUILTIN_UAS)

    app = WuYouPlan(acc, pwd, ua=ua, proxy_api="")
    try:
        # 用 app.login() 走完整签名流程（直连，无代理）
        if not app.login():
            return {"account": account, "success": False, "error": "登录失败", "nickname": "", "total": 0, "checkin": "未知", "ad_status": "未知", "task_done": 0, "task_total": 0, "all_done": False}

        user = app.get_user_info()
        nickname = user.get("nickname", "")
        wallet = user.get("wallet", {})
        total_coins = wallet.get("gold_coins", 0)

        tasks_data = app.get_daily_tasks()
        task_list = tasks_data.get("tasks", [])
        task_done = sum(1 for t in task_list if t.get("is_claimed"))
        task_total = len(task_list)

        # 检查签到（用 _post 带签名）
        checkin_status = "未知"
        try:
            r2 = app._post(f"{DAILY_TASKS_URL}/daily_checkin/claim")
            data2 = r2.json()
            if data2.get("ok"):
                checkin_status = "未领取"
            elif "已领取" in str(data2) or "已领" in str(data2):
                checkin_status = "已领取"
            else:
                checkin_status = "已领取"
        except Exception:
            checkin_status = "未知"

        # 检查广告
        ads_info = app.get_ads_info()
        if not ads_info.get("enabled", False):
            ad_status = "未启用"
        else:
            items = ads_info.get("items", [])
            max_views = ads_info.get("max_views_per_day", 0)
            if len(items) == 0 or max_views <= 0:
                ad_status = "已达上限"
            else:
                ad_status = f"剩余 {max_views} 次"

        # 判断是否全部完成
        all_done = (checkin_status == "已领取") and (ad_status in ["已达上限", "未启用"]) and (task_done >= task_total)

        return {
            "account": account,
            "success": True,
            "nickname": nickname,
            "total": total_coins,
            "checkin": checkin_status,
            "ad_status": ad_status,
            "task_done": task_done,
            "task_total": task_total,
            "all_done": all_done,
            "error": "",
        }
    except Exception as e:
        return {"account": account, "success": False, "error": str(e), "nickname": "", "total": 0, "checkin": "未知", "ad_status": "未知", "task_done": 0, "task_total": 0, "all_done": False}


def format_query(result: dict) -> str:
    acc = mask_account(result["account"])
    if not result["success"]:
        return f"❌ {acc}\n   查询失败：{result.get('error', '未知')}"

    nickname = result.get("nickname", "")
    name = f"〔{nickname}〕" if nickname else ""
    icon = "✅" if result.get("all_done") else "⏳"

    lines = [f"{icon} {acc} {name}"]
    lines.append(f"   💰 金币 {result['total']}")
    lines.append(f"   📝 签到 {result['checkin']}")
    lines.append(f"   📺 广告 {result['ad_status']}")
    lines.append(f"   📋 任务 {result['task_done']}/{result['task_total']}")

    if result.get("all_done"):
        lines.append("   🎉 今日已全部完成")

    return "\n".join(lines)


def query_all(accounts: list):
    if not accounts:
        sender.reply("未绑定任何账号")
        return
    sender.reply(f"🔍 查询 {len(accounts)} 个账号今日状态...")
    results = []
    with ThreadPoolExecutor(max_workers=min(len(accounts), 5)) as executor:
        future_to_account = {executor.submit(query_account, acc): acc for acc in accounts}
        for future in as_completed(future_to_account):
            account = future_to_account[future]
            try:
                result = future.result()
            except Exception as e:
                result = {"account": account, "success": False, "error": str(e), "nickname": "", "total": 0, "checkin": "未知", "ad_status": "未知", "task_done": 0, "task_total": 0, "all_done": False}
            results.append(result)
            sender.reply(format_query(result))

    done_count = sum(1 for r in results if r.get("all_done"))
    total = len(results)
    sender.reply(
        "📊 查询汇总\n"
        "────────────────────\n"
        f"📱 共 {total} 个账号\n"
        f"✅ 已完成 {done_count}\n"
        f"⏳ 待执行 {total - done_count}"
    )
    return results


def execute_account(account: str, proxy_api: str, skip_check: bool = False) -> dict:
    login_info = middleware.bucketGet(bucket='dd_WuYou_login', key=account)
    if not login_info:
        return {"account": account, "success": False, "error": "缺少登录信息", "logs": [], "earned": 0, "total": 0, "ad_error": "", "checkin": "", "proxy_ip": "-"}
    acc, pwd, ua = parse_account_info(login_info)
    if not pwd:
        return {"account": account, "success": False, "error": "缺少密码", "logs": [], "earned": 0, "total": 0, "ad_error": "", "checkin": "", "proxy_ip": "-"}
    if not ua:
        ua = random.choice(BUILTIN_UAS)

    # 计划任务模式：先不用代理快速预检，避免浪费代理资源
    if skip_check:
        app = WuYouPlan(acc, pwd, ua=ua, proxy_api="")
        try:
            app.attest.ensure()
            # 尝试登录（直连）
            payload = {
                "account": acc,
                "password": pwd,
                "device_id": app.device_id,
                "platform": "android",
                "app_version": APP_VERSION,
            }
            resp = app.session.post(
                LOGIN_URL,
                data=compact_json(payload),
                headers={"Content-Type": "application/json"},
                verify=False,
                timeout=15,
            )
            data = resp.json()
            token = data.get("token")
            if not token:
                return {"account": account, "success": False, "error": f"登录失败: {str(data)[:200]}", "logs": [], "earned": 0, "total": 0, "ad_error": "", "checkin": "", "proxy_ip": "-"}
            app.token = token
            app.session.headers.update({"authorization": f"Bearer {token}"})

            # 查询今日状态
            user = app.get_user_info()
            tasks_data = app.get_daily_tasks()

            # 检查是否所有任务都已领取
            all_claimed = True
            for task in tasks_data.get("tasks", []):
                if task.get("is_completed") and not task.get("is_claimed"):
                    all_claimed = False
                    break

            # 检查广告是否已看完（max_views <= 0 或 items 为空）
            ads_info = app.get_ads_info()
            ads_done = not ads_info.get("enabled", False) or ads_info.get("max_views_per_day", 0) <= 0

            # 检查签到是否已领取
            checkin_done = True
            try:
                resp2 = app.session.post(
                    f"{DAILY_TASKS_URL}/daily_checkin/claim",
                    headers={"Content-Type": "application/json", "authorization": f"Bearer {token}"},
                    verify=False,
                    timeout=15,
                )
                if "已领取" not in str(resp2.json()):
                    checkin_done = False
            except Exception:
                checkin_done = False

            wallet = user.get("wallet", {})
            total_coins = wallet.get("gold_coins", 0)
            nickname = user.get("nickname", "")

            if all_claimed and ads_done and checkin_done:
                return {
                    "account": account,
                    "success": True,
                    "nickname": nickname,
                    "start_coins": total_coins,
                    "end_coins": total_coins,
                    "earned": 0,
                    "total": total_coins,
                    "tasks": tasks_data,
                    "claimed_tasks": [],
                    "logs": [f"[{datetime.now().strftime('%H:%M:%S')}] 预检跳过：今日任务已全部完成"],
                    "ad_error": "今日已完成",
                    "checkin": "已领取",
                    "proxy_ip": "直连预检",
                }

            # 有任务要做，回退到完整执行（走代理）
        except Exception as e:
            # 预检异常，回退到完整执行
            pass

    # 正常执行（走代理）
    app = WuYouPlan(acc, pwd, ua=ua, proxy_api=proxy_api)
    try:
        return app.run()
    except Exception as e:
        return {"account": account, "success": False, "error": str(e), "logs": app.result_lines if hasattr(app, 'result_lines') else [], "earned": 0, "total": 0, "ad_error": "", "checkin": "", "proxy_ip": app.proxy_mgr.proxy_ip if hasattr(app, 'proxy_mgr') else "-"}


def execute_all(accounts: list, proxy_api: str, notify_owner: bool = True, skip_check: bool = False):
    if not accounts:
        sender.reply("未绑定任何账号")
        return []
    proxy_api = proxy_api or load_proxy_api()

    # 计划任务模式：先查询，全完成的直接发结果，不浪费代理
    if skip_check:
        sender.reply(f"🔍 预检 {len(accounts)} 个账号...")
        query_results = []
        with ThreadPoolExecutor(max_workers=min(len(accounts), 5)) as executor:
            future_to_account = {executor.submit(query_account, acc): acc for acc in accounts}
            for future in as_completed(future_to_account):
                account = future_to_account[future]
                try:
                    result = future.result()
                except Exception as e:
                    result = {"account": account, "success": False, "error": str(e), "nickname": "", "total": 0, "checkin": "未知", "ad_status": "未知", "task_done": 0, "task_total": 0, "all_done": False}
                query_results.append(result)

        # 分离已完成和待执行的
        done_results = [r for r in query_results if r.get("all_done")]
        todo_accounts = [r["account"] for r in query_results if r.get("success") and not r.get("all_done")]
        fail_accounts = [r["account"] for r in query_results if not r.get("success")]

        # 发已完成的结果
        if done_results:
            for r in done_results:
                sender.reply(format_query(r))

        if not todo_accounts:
            sender.reply(
                "📊 执行汇总\n"
                "────────────────────\n"
                f"📱 共 {len(accounts)} 个账号\n"
                f"✅ 全部已完成，无需执行\n"
                f"💰 总收益 +0"
            )
            return query_results

        sender.reply(f"⏳ {len(todo_accounts)} 个账号有任务待执行，开始跑...")
        accounts = todo_accounts

    sender.reply(f"🚀 执行 {len(accounts)} 个账号...")
    results = []
    with ThreadPoolExecutor(max_workers=min(len(accounts), 5)) as executor:
        future_to_account = {
            executor.submit(execute_account, acc, proxy_api, False): acc
            for acc in accounts
        }
        for future in as_completed(future_to_account):
            account = future_to_account[future]
            try:
                result = future.result()
            except Exception as e:
                result = {"account": account, "success": False, "error": str(e), "logs": [], "earned": 0, "total": 0, "ad_error": "", "checkin": "", "proxy_ip": "-"}
            results.append(result)
            formatted = format_result(result)
            owner_id = get_account_owner(account)
            if notify_owner and owner_id and owner_id != userid:
                sender.reply(f"{formatted}\n[CQ:at,qq={owner_id}]")
            else:
                sender.reply(formatted)
    summary = format_summary(results, done_count=len(done_results) if skip_check else 0)
    sender.reply(summary)
    # 合并查询结果和执行结果返回
    if skip_check:
        return done_results + results
    return results


def Administration():
    global uservalue
    base_message = (
        "🎯 无忧计划\n"
        "────────────────────\n"
        "1️⃣  提交账号\n"
        "2️⃣  执行任务\n"
        "3️⃣  删除账号\n"
        "4️⃣  查看账号\n"
        "5️⃣  查询今日状态 🔍"
    )
    if sender.isAdmin():
        base_message += "\n6️⃣  全体执行 👑"
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
        execute_all(accounts, load_proxy_api())
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
                    middleware.bucketSet(bucket='dd_WuYou_bind', key=userid, value=json.dumps(accounts, ensure_ascii=False))
                else:
                    middleware.bucketDel(bucket='dd_WuYou_bind', key=userid)
                middleware.bucketDel(bucket='dd_WuYou_login', key=selected)
                remove_account_owner(selected)
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
            owner = get_account_owner(acc)
            owner_tag = f" 〔归属:{owner[:6]}...〕" if owner and owner != userid else ""
            msg += f"{i}. {mask_account(acc)}{owner_tag}\n"
        msg += f"────────────────────\n共 {len(accounts)} 个账号"
        sender.reply(msg)
        return
    elif choice == 5:
        if not accounts:
            sender.reply("未绑定任何账号")
            return
        query_all(accounts)
        return
    elif choice == 6 and sender.isAdmin():
        all_accounts = get_all_accounts_global()  # ★ 获取全系统所有账号
        if not all_accounts:
            sender.reply("系统中没有任何账号")
            return
        sender.reply(
            "👑 全体执行\n"
            "────────────────────\n"
            f"📊 共 {len(all_accounts)} 个账号（全系统）\n"
            "❓ 是否执行？\n"
            "────────────────────\n"
            "[y]是  [n]否"
        )
        confirm = sender.input(60000, 1, False)
        if not confirm or confirm.lower() != 'y':
            sender.reply('已取消')
            return
        execute_all(all_accounts, load_proxy_api(), notify_owner=True)
        return
    else:
        sender.reply('❌ 无效选项')


def main():
    global uservalue
    uservalue = middleware.bucketGet(bucket='dd_WuYou_bind', key=userid)
    message = sender.getMessage()
    if message == "无忧计划任务检测":
        accounts = parse_accounts(uservalue)
        sender.reply(
            "📊 任务状态\n"
            "────────────────────\n"
            f"📱 绑定：{len(accounts)} 个账号\n"
            f"📅 日期：{datetime.now().strftime('%Y-%m-%d')}\n"
            "⏰ 定时：每天 8:00"
        )
        return
    if message == "无忧计划执行":
        accounts = parse_accounts(uservalue)
        if not accounts:
            sender.reply("未绑定任何账号")
            return
        execute_all(accounts, load_proxy_api(), skip_check=True)
        return
    if message == "无忧运行":
        accounts = parse_accounts(uservalue)
        if not accounts:
            sender.reply("未绑定任何账号")
            return
        sender.reply(f"🚀 一键运行 {len(accounts)} 个账号...")
        execute_all(accounts, load_proxy_api(), skip_check=True)
        return
    Administration()


main()

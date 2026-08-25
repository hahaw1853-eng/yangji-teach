#[pin:false]
#[disable:false]
#[public:true]
#[rule: ^(无忧计划|无忧计划执行|无忧计划任务检测|无忧运行)$]
#[version: 4.1]
#[price: 0.00]
#[cron: 0 8 * * *]
#[title: 无忧计划]
#[author: kimi]
#[admin: false]
#[icon: https://img.cdn1.vip/i/6a8e00f74bda3_1787691255.webp]
#[description: 无忧计划自动任务插件，内置每日签到与看广告赚金币！<br>指令:无忧计划、无忧计划执行、无忧计划任务检测、无忧运行<br>格式：手机号#密码#UA(可选)<br>内置定时检测与自动执行任务]
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

# ==================== 内置 UA 池 ====================
BUILTIN_UAS = [
    "Mozilla/5.0 (Linux; Android 14; SM-S918B Build/UP1A.231005.007; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/120.0.6099.230 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-G991B Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/110.0.5481.153 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; Pixel 6 Build/SQ1D.220205.003; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/105.0.5195.136 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; Redmi K40 Build/RKQ1.200826.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/96.0.4664.104 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; V2031A Build/QP1A.190711.020; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 9; ASUS_AI2401_A Build/PQ3B.190801.07131748; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Mobile Safari/537.36",
]

# ==================== 常量 ====================
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

senderID = middleware.getSenderID()
sender = middleware.Sender(senderID)
userid = sender.getUserID()
uservalue = middleware.bucketGet(bucket='dd_WuYou_bind', key=userid)

# ==================== 工具函数 ====================
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
    """解析 手机号#密码#UA"""
    parts = login_info.split('#')
    if len(parts) >= 3:
        return parts[0], parts[1], '#'.join(parts[2:])
    elif len(parts) == 2:
        return parts[0], parts[1], ""
    return parts[0], "", ""

def mask_account(account: str) -> str:
    """手机号脱敏"""
    if len(account) >= 7:
        return account[:3] + "****" + account[-4:]
    return account

def get_account_owner(account: str) -> str:
    """获取账号归属的QQ用户ID"""
    return middleware.bucketGet(bucket='dd_WuYou_owner', key=account) or ""

def set_account_owner(account: str, owner_id: str):
    """设置账号归属"""
    middleware.bucketSet(bucket='dd_WuYou_owner', key=account, value=owner_id)

def remove_account_owner(account: str):
    """删除账号归属"""
    middleware.bucketDel(bucket='dd_WuYou_owner', key=account)

def parse_accounts(value):
    """安全解析账号列表"""
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

# ==================== 代理管理 ====================
class ProxyManager:
    def __init__(self, api_url: str):
        self.api_url = api_url
        self.current_proxy = None

    def _parse_proxy_response(self, text: str):
        """解析代理API返回: IP:PORT 用户名 密码"""
        text = text.strip()
        if not text:
            return None
        
        # 格式: 218.95.39.29:15129 4IC9GGRE2E od7gi00v3on4ctg
        parts = text.split()
        if len(parts) >= 3 and ':' in parts[0]:
            ip_port = parts[0]
            username = parts[1]
            password = parts[2]
            proxy_url = f"http://{username}:{password}@{ip_port}"
            return {'http': proxy_url, 'https': proxy_url}
        
        # 格式: IP:PORT
        if len(parts) == 1 and ':' in parts[0]:
            proxy_url = f"http://{parts[0]}"
            return {'http': proxy_url, 'https': proxy_url}
        
        # 尝试 JSON
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                if 'data' in data and isinstance(data['data'], list) and data['data']:
                    item = data['data'][0]
                    ip = item.get('ip', item.get('IP'))
                    port = item.get('port', item.get('PORT'))
                    user = item.get('username', item.get('user', ''))
                    pwd = item.get('password', item.get('pass', ''))
                    if ip and port:
                        if user and pwd:
                            proxy_url = f"http://{user}:{pwd}@{ip}:{port}"
                        else:
                            proxy_url = f"http://{ip}:{port}"
                        return {'http': proxy_url, 'https': proxy_url}
                elif 'ip' in data and 'port' in data:
                    ip, port = data['ip'], data['port']
                    user = data.get('username', data.get('user', ''))
                    pwd = data.get('password', data.get('pass', ''))
                    if user and pwd:
                        proxy_url = f"http://{user}:{pwd}@{ip}:{port}"
                    else:
                        proxy_url = f"http://{ip}:{port}"
                    return {'http': proxy_url, 'https': proxy_url}
        except (ValueError, json.JSONDecodeError):
            pass
        
        # 兜底: 正则匹配 IP:PORT
        match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5})', text)
        if match:
            proxy_url = f"http://{match.group(1)}"
            return {'http': proxy_url, 'https': proxy_url}
        
        return None

    def refresh(self):
        if not self.api_url:
            return None
        try:
            resp = requests.get(self.api_url, timeout=10)
            self.current_proxy = self._parse_proxy_response(resp.text)
            return self.current_proxy
        except Exception as e:
            print(f"获取代理失败: {e}")
            return None

# ==================== AppAttest ====================
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

# ==================== 无忧计划核心类 ====================
class WuYouPlan:
    def __init__(self, account, password, device_id="", ua="", proxy_api=""):
        self.account = account
        self.password = password
        self.session = requests.Session()
        self.session.verify = False
        self.ua = ua
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
        # 每个账号独立代理
        self.proxy_api = proxy_api
        self.proxy_mgr = ProxyManager(self.proxy_api)
        self.device_id = device_id or self._load_or_create_device_id()
        self.attest = AppAttest(self.session, self.device_id, self.log)
        self.token = None
        self.user_id = None
        self.user_info = None
        self.total_coins_earned = 0
        self.result_lines = []

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
        headers = dict(self.attest.sign_headers(method, url, body))
        if payload is not None:
            headers["Content-Type"] = "application/json"
        resp = self.session.request(
            method, url, data=body if payload is not None else None,
            params=params, headers=headers, timeout=20,
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
            else:
                self.log(f"  领取签到奖励失败: {str(data2)[:200]}")
        except Exception as e:
            self.log(f"  领取签到奖励异常: {e}")
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
            return 0, 0
        if max_views <= 0:
            self.log("  今日广告次数已用完")
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
                interval = complete_data.get("next_request_available_in") or \
                    session_data.get("request_interval_seconds") or random.randint(3, 5)
                self.log(f"  等待 {interval} 秒后下一个...")
                time.sleep(interval)

        self.log(f"广告汇总: 成功 {success_count} 次 | 失败 {fail_count} 次 | 累计 +{self.total_coins_earned}金币")
        return success_count, fail_count

    def run(self) -> dict:
        """执行一个账号的全部任务，返回结构化结果"""
        self.log(f"========== 账号: {mask_account(self.account)} ==========")

        # 获取代理
        if self.proxy_api:
            proxy = self.proxy_mgr.refresh()
            if proxy:
                self.session.proxies = proxy
                self.log(f"已获取代理: {proxy['http'][:50]}...")
            else:
                self.log("未获取到代理，将直连执行")

        if not self.login():
            return {
                "account": self.account,
                "success": False,
                "error": "登录失败",
                "logs": self.result_lines,
                "earned": 0,
                "total": 0,
            }

        # 查询用户信息
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

        # 获取每日任务
        self.log("获取任务列表...")
        tasks_data = self.get_daily_tasks()

        # 每日签到
        self.checkin()

        # 查询设备
        try:
            devices_data = self.get_user_devices()
            max_devices = devices_data.get("max_devices", 0)
            used = devices_data.get("devices_used", 0)
            self.log(f"设备: {used}/{max_devices}")
        except Exception as e:
            self.log(f"查询设备信息失败: {e}")

        # 看广告
        self.watch_ads(account_max_views=account_max_views)

        # 领取任务奖励
        tasks_data = self.get_daily_tasks()
        claimed_tasks = []
        for task in tasks_data.get("tasks", []):
            task_key = task.get("task_key", "")
            if task.get("is_completed") and not task.get("is_claimed"):
                result = self.claim_task(task_key)
                claimed_tasks.append(task.get("title", task_key))

        # 查询最终余额
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
        }

# ==================== 结果格式化 ====================
def format_result(result: dict) -> str:
    """将结构化结果格式化为美观的文本"""
    acc = mask_account(result["account"])
    if not result["success"]:
        return f"[❌] {acc} | 失败: {result.get('error', '未知错误')}"

    earned = result.get("earned", 0)
    total = result.get("total", 0)
    nickname = result.get("nickname", "")
    
    line = f"[✅] {acc}"
    if nickname:
        line += f"({nickname})"
    line += f" | +{earned}金币 | 总:{total}"
    
    # 任务状态
    tasks = result.get("tasks", {})
    task_list = tasks.get("tasks", [])
    if task_list:
        completed = sum(1 for t in task_list if t.get("is_completed"))
        claimed = sum(1 for t in task_list if t.get("is_claimed"))
        pending = sum(1 for t in task_list if t.get("is_completed") and not t.get("is_claimed"))
        line += f" | 任务:{completed}/{len(task_list)}"

    # 自动领取的任务
    claimed_tasks = result.get("claimed_tasks", [])
    if claimed_tasks:
        line += f" | 领奖:{len(claimed_tasks)}个"

    return line

def format_summary(results: list) -> str:
    """汇总多个账号的执行结果"""
    total_accounts = len(results)
    success_count = sum(1 for r in results if r["success"])
    fail_count = total_accounts - success_count
    total_earned = sum(r.get("earned", 0) for r in results if r["success"])

    lines = []
    lines.append("========== 执行汇总 ==========")
    lines.append(f"总账号: {total_accounts} | 成功: {success_count} | 失败: {fail_count}")
    lines.append(f"总获得: +{total_earned}金币")
    lines.append("==============================")

    # 失败详情
    fails = [r for r in results if not r["success"]]
    if fails:
        lines.append("失败详情:")
        for r in fails:
            lines.append(f"  [❌] {mask_account(r['account'])}: {r.get('error', '未知')}")

    return "\n".join(lines)

# ==================== 机器人框架交互 ====================
def bind():
    """绑定账号"""
    sender.reply(
        "========== 无忧计划 - 绑定账号 ==========\n"
        "格式: 手机号#密码#UA\n"
        "示例: 13800138000#mypassword#Mozilla/5.0...\n"
        "\n"
        "UA 可省略，将询问是否使用内置UA\n"
        "! 建议私聊提交，密码泄露风险自负\n"
        "* 输入 q 退出操作\n"
        "========================================"
    )

    login_value = sender.input(120000, 1, False)
    if not login_value:
        sender.reply('输入超时！')
        return
    elif login_value.lower() == 'q':
        sender.reply('已退出操作')
        return

    # 解析
    parts = login_value.split('#')
    if len(parts) < 2:
        sender.reply('格式错误！请使用: 手机号#密码#UA(可选)')
        return

    account = parts[0]
    password = parts[1]
    ua = '#'.join(parts[2:]) if len(parts) >= 3 else ""

    # 如果没有UA，询问是否使用内置
    if not ua:
        sender.reply(
            "========== 未检测到自定义 UA ==========\n"
            "是否使用内置随机 UA 执行？\n"
            "[y] 是 - 使用内置UA\n"
            "[n] 否 - 重新提交（带UA）\n"
            "======================================"
        )
        confirm = sender.input(60000, 1, False)
        if confirm and confirm.lower() == 'y':
            ua = random.choice(BUILTIN_UAS)
            sender.reply(f"已随机选择内置UA:\n{ua[:60]}...")
        else:
            sender.reply('请重新提交，格式: 手机号#密码#UA')
            return

    # 保存登录信息
    full_info = f"{account}#{password}#{ua}"
    middleware.bucketSet(bucket='dd_WuYou_login', key=account, value=full_info)

    # 记录归属
    set_account_owner(account, userid)

    # 更新绑定列表
    accounts = parse_accounts(uservalue)
    if account in accounts:
        middleware.bucketSet(bucket='dd_WuYou_bind', key=userid, value=json.dumps(accounts, ensure_ascii=False))
        sender.reply(f"账号 {mask_account(account)} 信息已更新！")
    else:
        accounts.append(account)
        middleware.bucketSet(bucket='dd_WuYou_bind', key=userid, value=json.dumps(accounts, ensure_ascii=False))
        sender.reply(
            "========== 绑定成功！ ==========\n"
            f"账号: {mask_account(account)}\n"
            f"当前共 {len(accounts)} 个账号\n"
            "发送 [无忧计划] 管理账号\n"
            "==============================="
        )


def execute_account(account: str, proxy_api: str) -> dict:
    """执行单个账号任务，返回结构化结果"""
    login_info = middleware.bucketGet(bucket='dd_WuYou_login', key=account)
    if not login_info:
        return {"account": account, "success": False, "error": "缺少登录信息", "logs": [], "earned": 0, "total": 0}

    acc, pwd, ua = parse_account_info(login_info)
    if not pwd:
        return {"account": account, "success": False, "error": "缺少密码", "logs": [], "earned": 0, "total": 0}

    # 如果没有UA，用内置
    if not ua:
        ua = random.choice(BUILTIN_UAS)

    app = WuYouPlan(acc, pwd, ua=ua, proxy_api=proxy_api)
    try:
        return app.run()
    except Exception as e:
        return {"account": account, "success": False, "error": str(e), "logs": app.result_lines if hasattr(app, 'result_lines') else [], "earned": 0, "total": 0}


def execute_all(accounts: list, proxy_api: str, notify_owner: bool = True):
    """执行多个账号（支持并发）"""
    if not accounts:
        sender.reply("未绑定任何账号")
        return []

    proxy_api = proxy_api or load_proxy_api()

    sender.reply(f"开始执行 {len(accounts)} 个账号...")

    results = []
    # 并发执行，每个账号独立代理
    with ThreadPoolExecutor(max_workers=min(len(accounts), 5)) as executor:
        future_to_account = {
            executor.submit(execute_account, acc, proxy_api): acc
            for acc in accounts
        }
        for future in as_completed(future_to_account):
            account = future_to_account[future]
            try:
                result = future.result()
            except Exception as e:
                result = {"account": account, "success": False, "error": str(e), "logs": [], "earned": 0, "total": 0}
            results.append(result)

            # 发送该账号结果
            formatted = format_result(result)
            owner_id = get_account_owner(account)
            if notify_owner and owner_id and owner_id != userid:
                # 艾特归属用户
                sender.reply(f"{formatted}\n[CQ:at,qq={owner_id}]")
            else:
                sender.reply(formatted)

    # 发送汇总
    summary = format_summary(results)
    sender.reply(summary)
    return results


def Administration():
    """管理账号"""
    global uservalue

    base_message = (
        "========== 无忧计划 - 管理面板 ==========\n"
        "[1] 提交/更新账号\n"
        "[2] 执行我的账号\n"
        "[3] 删除账号\n"
        "[4] 查看我的账号\n"
    )

    if sender.isAdmin():
        base_message += "[5] 全体执行(仅管理员账号)\n"

    base_message += (
        "* 输入 q 退出操作\n"
        "========================================"
    )

    sender.reply(base_message)

    choice = sender.input(60000, 1, False)
    if not choice or choice.lower() == 'q':
        sender.reply('已退出')
        return

    try:
        choice = int(choice)
    except ValueError:
        sender.reply('请输入数字选项')
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
            "========== 确认执行 ==========\n"
            f"账号数: {len(accounts)} 个\n"
            "是否立即执行? [y]是 | [n]否\n"
            "=============================="
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

        msg = "========== 选择要删除的账号 ==========\n"
        for i, acc in enumerate(accounts, 1):
            msg += f"[{i}] {mask_account(acc)}\n"
        msg += "* 输入 q 取消\n"
        msg += "======================================"
        sender.reply(msg)

        acc_choice = sender.input(60000, 1, False)
        if not acc_choice or acc_choice.lower() == 'q':
            sender.reply('已取消')
            return

        try:
            idx = int(acc_choice)
            if idx < 1 or idx > len(accounts):
                sender.reply('序号无效')
                return
        except ValueError:
            sender.reply('请输入有效数字')
            return

        selected = accounts[idx - 1]

        sender.reply(
            "========== 删除确认 ==========\n"
            f"账号: {mask_account(selected)}\n"
            "[y] 确认删除 | [n] 取消\n"
            "=============================="
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
                sender.reply(f'账号 {mask_account(selected)} 已删除')
            except Exception as e:
                sender.reply(f'删除失败: {str(e)}')
        else:
            sender.reply('已取消删除')

    elif choice == 4:
        if not accounts:
            sender.reply("未绑定任何账号")
            return

        msg = "========== 我的账号列表 ==========\n"
        for i, acc in enumerate(accounts, 1):
            owner = get_account_owner(acc)
            owner_tag = f" (归属:{owner[:6]}...)" if owner and owner != userid else ""
            msg += f"[{i}] {mask_account(acc)}{owner_tag}\n"
        msg += f"----------------------------------\n"
        msg += f"共 {len(accounts)} 个账号\n"
        msg += "=================================="
        sender.reply(msg)
        return

    elif choice == 5 and sender.isAdmin():
        # 管理员全体执行 - 只执行管理员自己绑定的账号，并发
        if not accounts:
            sender.reply("管理员未绑定任何账号")
            return

        sender.reply(
            "========== 管理员全体执行 ==========\n"
            f"将执行管理员绑定的 {len(accounts)} 个账号\n"
            "并发执行，是否确认? [y]是 | [n]否\n"
            "==================================="
        )
        confirm = sender.input(60000, 1, False)
        if not confirm or confirm.lower() != 'y':
            sender.reply('已取消')
            return

        execute_all(accounts, load_proxy_api(), notify_owner=True)
        return

    else:
        sender.reply('无效选项')


def main():
    global uservalue
    uservalue = middleware.bucketGet(bucket='dd_WuYou_bind', key=userid)

    message = sender.getMessage()

    if message == "无忧计划任务检测":
        accounts = parse_accounts(uservalue)
        sender.reply(
            "========== 无忧计划任务状态 ==========\n"
            f"绑定账号: {len(accounts)} 个\n"
            f"今日日期: {datetime.now().strftime('%Y-%m-%d')}\n"
            "任务将自动定时执行 (每天8:00)\n"
            "====================================="
        )
        return

    if message == "无忧计划执行":
        accounts = parse_accounts(uservalue)
        if not accounts:
            sender.reply("未绑定任何账号，请先提交账号")
            return
        execute_all(accounts, load_proxy_api())
        return

    if message == "无忧运行":
        # 一键运行 - 自动运行当前用户所有账号
        accounts = parse_accounts(uservalue)
        if not accounts:
            sender.reply("未绑定任何账号，请先发送 [无忧计划] 绑定")
            return
        sender.reply(f"一键运行 {len(accounts)} 个账号...")
        execute_all(accounts, load_proxy_api())
        return

    Administration()


main()

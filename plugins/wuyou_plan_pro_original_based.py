#[pin:false]
#[disable:false]
#[public:true]
#[rule: ^(无忧计划|无忧计划执行|无忧计划任务检测|无忧运行)(\s+.*)?$]
#[version: 4.4]
#[price: 0.00]
#[cron: 0 8 * * *]
#[title: 无忧计划]
#[author: kimi]
#[admin: false]
#[icon: https://img.cdn1.vip/i/6a8e00f74bda3_1787691255.webp]
#[description: 无忧计划自动任务插件，内置每日签到与看广告赚金币！<br>指令:无忧计划、无忧计划执行、无忧计划任务检测、无忧运行<br>格式：手机号#密码#UA(可选)<br>内置定时检测与自动执行任务]
#[param: {"required":false,"key":"dd_WuYou_PluginsData.proxy_api","bool":false,"placeholder":"可选,代理API地址","name":"代理API","desc":"代理API接口地址,每个账号独立获取代理"}]

import re
import ast
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

BUILTIN_UAS = [
    "Mozilla/5.0 (Linux; Android 14; SM-S918B Build/UP1A.231005.007; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/120.0.6099.230 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-G991B Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/110.0.5481.153 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; Pixel 6 Build/SQ1D.220205.003; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/105.0.5195.136 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; Redmi K40 Build/RKQ1.200826.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/96.0.4664.104 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; V2031A Build/QP1A.190711.020; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 9; ASUS_AI2401_A Build/PQ3B.190801.07131748; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Mobile Safari/537.36",
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
    """兼容旧版列表格式，但绝不执行用户或存储中的任意代码。"""
    if not value:
        return []
    try:
        data = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        try:
            data = ast.literal_eval(value)
        except (ValueError, SyntaxError, TypeError):
            return []
    if not isinstance(data, list):
        return []
    return [str(item).strip() for item in data if str(item).strip()]

class ProxyManager:
    def __init__(self, api_url: str):
        self.api_url = api_url
        self.current_proxy = None

    def _parse_proxy_response(self, text: str):
        text = text.strip()
        if not text:
            return None
        parts = text.split()
        if len(parts) >= 3 and ':' in parts[0]:
            ip_port = parts[0]
            username = parts[1]
            password = parts[2]
            proxy_url = f"http://{username}:{password}@{ip_port}"
            return {'http': proxy_url, 'https': proxy_url}
        if len(parts) == 1 and ':' in parts[0]:
            proxy_url = f"http://{parts[0]}"
            return {'http': proxy_url, 'https': proxy_url}
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
        self.proxy_api = proxy_api
        self.proxy_mgr = ProxyManager(self.proxy_api)
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
                "ad_error": "",
                "checkin": "",
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
        }

# ─────────────────────────────────────────────────────────────────────────────
# 交互与展示层（v5 UI）
# 说明：以下重构只处理菜单、账户展示、执行汇总和本地状态快照。
# WuYouPlan、登录、设备、签到、任务、并发和定时执行的原有链路保持不变。
# ─────────────────────────────────────────────────────────────────────────────
ALIAS_BUCKET = 'dd_WuYou_alias'
STATUS_BUCKET = 'dd_WuYou_status'


def clean_message(value, limit=90):
    return str(value or '').replace('\r', ' ').replace('\n', ' ').strip()[:limit]


def get_account_alias(account: str) -> str:
    return middleware.bucketGet(bucket=ALIAS_BUCKET, key=f'{userid}:{account}') or ''


def set_account_alias(account: str, alias: str):
    alias = re.sub(r'\s+', ' ', str(alias or '')).strip()[:16]
    if alias:
        middleware.bucketSet(bucket=ALIAS_BUCKET, key=f'{userid}:{account}', value=alias)
    else:
        middleware.bucketDel(bucket=ALIAS_BUCKET, key=f'{userid}:{account}')


def delete_account_alias(account: str):
    middleware.bucketDel(bucket=ALIAS_BUCKET, key=f'{userid}:{account}')


def display_name(account: str, index=None) -> str:
    alias = get_account_alias(account)
    if alias:
        return alias
    return f'账号 {index}' if index else mask_account(account)


def load_status_map() -> dict:
    raw = middleware.bucketGet(bucket=STATUS_BUCKET, key=userid)
    try:
        data = json.loads(raw) if raw else {}
        return data if isinstance(data, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def save_status(account: str, result: dict):
    """只保存脱敏的上次执行摘要，不保存密码、令牌或接口原文。"""
    states = load_status_map()
    states[account] = {
        'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'success': bool(result.get('success')),
        'earned': result.get('earned', 0) if result.get('success') else 0,
        'total': result.get('total', 0) if result.get('success') else 0,
        'checkin': clean_message(result.get('checkin', ''), 25),
        'ad': clean_message(result.get('ad_error', ''), 25),
        'error': clean_message(result.get('error', ''), 50),
    }
    middleware.bucketSet(bucket=STATUS_BUCKET, key=userid, value=json.dumps(states, ensure_ascii=False))


def delete_status(account: str):
    states = load_status_map()
    if account in states:
        del states[account]
        middleware.bucketSet(bucket=STATUS_BUCKET, key=userid, value=json.dumps(states, ensure_ascii=False))


def line(width=22):
    return '─' * width


def keycap(number) -> str:
    """QQ 文本菜单统一使用 keycap 数字；双位序号保留紧凑兜底格式。"""
    keys = {
        0: '0️⃣', 1: '1️⃣', 2: '2️⃣', 3: '3️⃣', 4: '4️⃣',
        5: '5️⃣', 6: '6️⃣', 7: '7️⃣', 8: '8️⃣', 9: '9️⃣',
    }
    try:
        return keys.get(int(number), f'[{number}]')
    except (TypeError, ValueError):
        return f'[{number}]'


def short_name(account: str, index=None) -> str:
    return clean_message(display_name(account, index), 7)

def format_result(result: dict, index=None) -> str:
    """单账号结果控制为两行：数字锚点、状态锚点、可扫读数据。"""
    label = keycap(index) if index is not None else '👤'
    name = short_name(result.get('account', ''), index)
    account = mask_account(result.get('account', ''))
    if not result.get('success'):
        return (
            f'{label} {name} · {account}　❌ 失败\n'
            f'　{clean_message(result.get("error", "执行异常，请稍后重试"), 35)}'
        )

    tasks = result.get('tasks') or {}
    task_list = tasks.get('tasks') or []
    completed = sum(1 for item in task_list if isinstance(item, dict) and item.get('is_completed')) if isinstance(task_list, list) else 0
    task_text = f'{completed}/{len(task_list)}' if task_list else '--'
    checkin = clean_message(result.get('checkin', ''), 10) or '已处理'
    ad_state = clean_message(result.get('ad_error', ''), 10)
    ad_suffix = ''
    if ad_state:
        if '上限' in ad_state or '已用完' in ad_state:
            ad_suffix = '｜广告满'
        elif '未启用' in ad_state:
            ad_suffix = '｜广告关'
        else:
            ad_suffix = f'｜{ad_state}'
    return (
        f'{label} {name} · {account}　✅ +{result.get("earned", 0)}\n'
        f'　签到{checkin}｜任务{task_text}｜余额{result.get("total", 0)}{ad_suffix}'
    )

def format_summary(results: list, accounts=None, started_at=None) -> str:
    total = len(results)
    success = sum(1 for item in results if item.get('success'))
    earned = sum(item.get('earned', 0) for item in results if item.get('success'))
    elapsed = max(0, int(time.time() - started_at)) if started_at is not None else 0
    lines = [
        '✅ 执行完成',
        f'📊 {total} 个账号｜{success} 成功｜+{earned} 金币｜{elapsed} 秒',
        '',
    ]
    for index, result in enumerate(results, 1):
        lines.append(format_result(result, index))
    if success != total:
        lines.extend(['', '⚠️ 失败账号可在「账号管理」中更新后重试'])
    lines.extend(['', '💬 发送「无忧计划 状态」查看记录'])
    return '\n'.join(lines)

def render_status_dashboard(accounts: list) -> str:
    states = load_status_map()
    if not accounts:
        return '📅 今日状态\n还没有账号，发送「无忧计划 添加」开始。'
    success = 0
    earned = 0
    rows = []
    for index, account in enumerate(accounts, 1):
        state = states.get(account, {})
        name = short_name(account, index)
        if not state:
            rows.append(f'{keycap(index)} {name}　⚪ 未执行')
            continue
        when = clean_message(state.get('time', ''), 16)[-5:] or '--:--'
        if state.get('success'):
            success += 1
            value = state.get('earned', 0) or 0
            earned += value
            rows.append(f'{keycap(index)} {name}　✅ +{value}｜余额{state.get("total", 0)}｜{when}')
        else:
            rows.append(f'{keycap(index)} {name}　❌ 待处理｜{when}')
    lines = [f'📅 今日状态　{len(accounts)} 个账号', f'📊 {success} 完成｜+{earned} 金币', '']
    lines.extend(rows)
    lines.extend(['', '💬 发送「无忧计划 执行」开始任务'])
    return '\n'.join(lines)

def render_account_list(accounts: list) -> str:
    if not accounts:
        return '👤 账号管理\n还没有账号，回复「添加」开始。'
    states = load_status_map()
    lines = [f'👤 账号管理　{len(accounts)} 个', '']
    for index, account in enumerate(accounts, 1):
        state = states.get(account, {})
        name = clean_message(get_account_alias(account) or f'账号{index}', 7)
        if not state:
            status = '⚪ 未执行'
        elif state.get('success'):
            status = f'✅ 正常 · +{state.get("earned", 0)}'
        else:
            status = '❌ 待处理'
        lines.append(f'{keycap(index)} {name} · {mask_account(account)}\n　{status}')
    lines.extend(['', '💬 添加｜改名 1｜删除 1｜执行 1', '回复 q 返回'])
    return '\n'.join(lines)

def ask_input(prompt: str, timeout=60000) -> str:
    sender.reply(prompt)
    return (sender.input(timeout, 1, False) or '').strip()


def bind():
    """保留绑定格式，使用短标题、单 emoji、短提示。"""
    login_value = ask_input(
        '➕ 添加账号\n请输入：手机号#密码#UA\n💡 UA 可省略，建议私聊\n回复 q 取消',
        120000,
    )
    if not login_value:
        sender.reply('⏱️ 已超时，添加取消。')
        return
    if login_value.lower() == 'q':
        sender.reply('已取消。')
        return
    parts = login_value.split('#')
    if len(parts) < 2 or not parts[0].strip() or not parts[1]:
        sender.reply('❌ 格式不正确\n手机号#密码#UA')
        return

    account = parts[0].strip()
    password = parts[1]
    ua = '#'.join(parts[2:]).strip() if len(parts) >= 3 else ''
    if not ua:
        confirm = ask_input('📱 未填写 UA\n回复 y 使用内置 UA｜其他取消', 60000)
        if confirm.lower() != 'y':
            sender.reply('已取消。')
            return
        ua = random.choice(BUILTIN_UAS)

    alias = ask_input('🏷️ 设置别名，例如「主号」\n回复 - 跳过', 60000)
    if alias.lower() == 'q':
        sender.reply('已取消。')
        return
    if alias and alias != '-':
        set_account_alias(account, alias)

    full_info = f'{account}#{password}#{ua}'
    middleware.bucketSet(bucket='dd_WuYou_login', key=account, value=full_info)
    set_account_owner(account, userid)
    accounts = parse_accounts(uservalue)
    if account in accounts:
        middleware.bucketSet(bucket='dd_WuYou_bind', key=userid, value=json.dumps(accounts, ensure_ascii=False))
        sender.reply(f'✅ 已更新\n👤 {short_name(account)} · {mask_account(account)}')
    else:
        accounts.append(account)
        middleware.bucketSet(bucket='dd_WuYou_bind', key=userid, value=json.dumps(accounts, ensure_ascii=False))
        sender.reply(f'✅ 添加成功\n👤 {short_name(account, len(accounts))} · {mask_account(account)}\n📊 当前 {len(accounts)} 个账号')

def execute_account(account: str, proxy_api: str) -> dict:
    """保留原有账户执行流程和原始返回结构。"""
    login_info = middleware.bucketGet(bucket='dd_WuYou_login', key=account)
    if not login_info:
        return {'account': account, 'success': False, 'error': '缺少登录信息', 'logs': [], 'earned': 0, 'total': 0, 'ad_error': '', 'checkin': ''}
    acc, pwd, ua = parse_account_info(login_info)
    if not pwd:
        return {'account': account, 'success': False, 'error': '缺少密码', 'logs': [], 'earned': 0, 'total': 0, 'ad_error': '', 'checkin': ''}
    if not ua:
        ua = random.choice(BUILTIN_UAS)
    app = WuYouPlan(acc, pwd, ua=ua, proxy_api=proxy_api)
    try:
        return app.run()
    except Exception as exc:
        return {
            'account': account,
            'success': False,
            'error': clean_message(exc, 100),
            'logs': app.result_lines if hasattr(app, 'result_lines') else [],
            'earned': 0,
            'total': 0,
            'ad_error': '',
            'checkin': '',
        }


def execute_all(accounts: list, proxy_api: str, notify_owner: bool = True):
    """保留原 5 路并发；当前会话仅发送启动卡和最终报告。"""
    if not accounts:
        sender.reply('没有可执行的账号。')
        return []
    started_at = time.time()
    proxy_api = proxy_api or load_proxy_api()
    sender.reply(f'🚀 任务已启动\n👥 {len(accounts)} 个账号｜⚡ {min(len(accounts), 5)} 路并发\n💬 完成后自动发送汇总')
    indexed_results = {}
    with ThreadPoolExecutor(max_workers=min(len(accounts), 5)) as executor:
        future_to_data = {
            executor.submit(execute_account, account, proxy_api): (index, account)
            for index, account in enumerate(accounts, 1)
        }
        for future in as_completed(future_to_data):
            index, account = future_to_data[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {'account': account, 'success': False, 'error': clean_message(exc, 100), 'logs': [], 'earned': 0, 'total': 0, 'ad_error': '', 'checkin': ''}
            indexed_results[index] = result
            save_status(account, result)
            owner_id = get_account_owner(account)
            # 保留管理员批量执行时，对非当前操作者归属人的逐账号结果通知。
            if notify_owner and owner_id and owner_id != userid:
                sender.reply(f'{format_result(result, index)}\n[CQ:at,qq={owner_id}]')

    results = [indexed_results[index] for index in range(1, len(accounts) + 1)]
    sender.reply(format_summary(results, accounts=accounts, started_at=started_at))
    return results

def execute_selected(accounts: list):
    if not accounts:
        sender.reply('👤 未绑定账号\n发送「无忧计划 添加」开始。')
        return
    lines = ['🎯 选择账号']
    for index, account in enumerate(accounts, 1):
        lines.append(f'{keycap(index)} {short_name(account, index)} · {mask_account(account)}')
    lines.extend(['', '💬 all 全部｜1,3 指定｜q 取消'])
    selected_raw = ask_input('\n'.join(lines), 60000)
    if not selected_raw or selected_raw.lower() == 'q':
        sender.reply('已取消。')
        return
    if selected_raw.lower() in ('all', '全部'):
        selected = accounts
    else:
        selected = []
        seen = set()
        for token in re.split(r'[,，\s]+', selected_raw):
            try:
                index = int(token)
                if 1 <= index <= len(accounts) and index not in seen:
                    selected.append(accounts[index - 1])
                    seen.add(index)
            except ValueError:
                continue
    if not selected:
        sender.reply('❌ 没有识别到有效账号。')
        return
    preview = '、'.join(short_name(account, i) for i, account in enumerate(selected, 1))
    confirm = ask_input(f'⚠️ 即将执行 {len(selected)} 个账号\n👤 {preview}\n💬 回复 y 确认｜其他取消', 60000)
    if confirm.lower() != 'y':
        sender.reply('已取消。')
        return
    execute_all(selected, load_proxy_api())

def delete_account(accounts: list):
    if not accounts:
        sender.reply('👤 当前没有账号。')
        return
    lines = ['🗑️ 删除账号']
    for index, account in enumerate(accounts, 1):
        lines.append(f'{keycap(index)} {short_name(account, index)} · {mask_account(account)}')
    choice = ask_input('\n'.join(lines) + '\n\n💬 回复序号，q 取消', 60000)
    if not choice or choice.lower() == 'q':
        sender.reply('已取消。')
        return
    try:
        index = int(choice)
        if not 1 <= index <= len(accounts):
            raise ValueError
    except ValueError:
        sender.reply('❌ 账号序号无效。')
        return
    selected = accounts[index - 1]
    confirm = ask_input(f'🗑️ 删除 {short_name(selected, index)}？\n💬 回复 DELETE 确认', 60000)
    if confirm != 'DELETE':
        sender.reply('已取消。')
        return
    try:
        accounts.remove(selected)
        if accounts:
            middleware.bucketSet(bucket='dd_WuYou_bind', key=userid, value=json.dumps(accounts, ensure_ascii=False))
        else:
            middleware.bucketDel(bucket='dd_WuYou_bind', key=userid)
        middleware.bucketDel(bucket='dd_WuYou_login', key=selected)
        remove_account_owner(selected)
        delete_account_alias(selected)
        delete_status(selected)
        sender.reply(f'✅ 已删除：{mask_account(selected)}')
    except Exception as exc:
        sender.reply(f'❌ 删除失败：{clean_message(exc)}')

def rename_account(accounts: list, index_text: str):
    try:
        index = int(index_text)
        if not 1 <= index <= len(accounts):
            raise ValueError
    except ValueError:
        sender.reply('❌ 账号序号无效。')
        return
    account = accounts[index - 1]
    alias = ask_input(f'🏷️ {mask_account(account)} 的新别名：', 60000)
    if not alias or alias.lower() == 'q':
        sender.reply('已取消。')
        return
    set_account_alias(account, alias)
    sender.reply(f'✅ 已改名：{short_name(account, index)}')

def account_center(accounts: list):
    command = ask_input(render_account_list(accounts), 90000)
    if not command or command.lower() == 'q':
        sender.reply('已返回。')
        return
    if command in ('添加', '新增'):
        bind()
        return
    match = re.match(r'^改名\s*(\d+)$', command)
    if match:
        rename_account(accounts, match.group(1))
        return
    match = re.match(r'^删除\s*(\d+)$', command)
    if match:
        delete_account_by_index(accounts, match.group(1))
        return
    match = re.match(r'^执行\s*(\d+)$', command)
    if match:
        try:
            index = int(match.group(1))
            if not 1 <= index <= len(accounts):
                raise ValueError
            execute_selected([accounts[index - 1]])
        except ValueError:
            sender.reply('❌ 账号序号无效。')
        return
    sender.reply('💬 添加｜改名 1｜删除 1｜执行 1｜q')

def delete_account_by_index(accounts: list, index_text: str):
    try:
        index = int(index_text)
        if not 1 <= index <= len(accounts):
            raise ValueError
    except ValueError:
        sender.reply('❌ 账号序号无效。')
        return
    selected = accounts[index - 1]
    confirm = ask_input(f'🗑️ 删除 {short_name(selected, index)}？\n💬 回复 DELETE 确认', 60000)
    if confirm != 'DELETE':
        sender.reply('已取消。')
        return
    try:
        accounts.remove(selected)
        if accounts:
            middleware.bucketSet(bucket='dd_WuYou_bind', key=userid, value=json.dumps(accounts, ensure_ascii=False))
        else:
            middleware.bucketDel(bucket='dd_WuYou_bind', key=userid)
        middleware.bucketDel(bucket='dd_WuYou_login', key=selected)
        remove_account_owner(selected)
        delete_account_alias(selected)
        delete_status(selected)
        sender.reply(f'✅ 已删除：{mask_account(selected)}')
    except Exception as exc:
        sender.reply(f'❌ 删除失败：{clean_message(exc)}')

def render_help() -> str:
    return (
        '💡 使用说明\n'
        '无忧计划：打开菜单\n'
        '状态｜账户｜执行｜添加\n\n'
        '兼容旧命令：\n'
        '无忧计划执行｜任务检测｜无忧运行'
    )

def Administration():
    global uservalue
    accounts = parse_accounts(uservalue)
    menu = (
        f'📌 无忧计划　{len(accounts)} 个账号\n'
        '⏰ 每日 08:00 自动执行\n\n'
        '1️⃣ 添加账号　　2️⃣ 立即执行\n'
        '3️⃣ 删除账号　　4️⃣ 账号管理\n'
        '5️⃣ 今日状态　　6️⃣ 使用帮助'
    )
    if sender.isAdmin():
        menu += '\n9️⃣ 管理员执行'
    menu += '\n\n💬 回复数字操作｜q 退出'
    choice = ask_input(menu, 90000)
    if not choice or choice.lower() == 'q':
        sender.reply('已退出。')
        return
    accounts = parse_accounts(middleware.bucketGet(bucket='dd_WuYou_bind', key=userid))
    if choice == '1':
        bind()
    elif choice == '2':
        execute_selected(accounts)
    elif choice == '3':
        delete_account(accounts)
    elif choice == '4':
        account_center(accounts)
    elif choice == '5':
        sender.reply(render_status_dashboard(accounts))
    elif choice == '6':
        sender.reply(render_help())
    elif choice == '9' and sender.isAdmin():
        if not accounts:
            sender.reply('👤 管理员当前未绑定账号。')
            return
        confirm = ask_input(f'🛡️ 管理员执行\n👥 当前 {len(accounts)} 个账号\n💬 回复 y 确认｜其他取消', 60000)
        if confirm.lower() == 'y':
            execute_all(accounts, load_proxy_api(), notify_owner=True)
        else:
            sender.reply('已取消。')
    else:
        sender.reply('❌ 无效选择\n💡 发送「无忧计划 帮助」查看说明')

def main():
    global uservalue
    uservalue = middleware.bucketGet(bucket='dd_WuYou_bind', key=userid)
    message = (sender.getMessage() or '').strip()
    accounts = parse_accounts(uservalue)

    # 保留旧命令，不改变外部定时与既有调用方式。
    if message == '无忧计划任务检测':
        sender.reply(render_status_dashboard(accounts))
        return
    if message == '无忧计划执行':
        if not accounts:
            sender.reply('未绑定任何账号。')
            return
        execute_all(accounts, load_proxy_api())
        return
    if message == '无忧运行':
        if not accounts:
            return
        execute_all(accounts, load_proxy_api())
        return

    # 新增自然语言子命令，不影响原“无忧计划”入口。
    command = message[len('无忧计划'):].strip() if message.startswith('无忧计划') else ''
    if command in ('状态', '检测', '今日状态'):
        sender.reply(render_status_dashboard(accounts))
    elif command in ('账户', '账号', '管理'):
        account_center(accounts)
    elif command in ('执行', '运行', '开始'):
        execute_selected(accounts)
    elif command in ('添加', '新增'):
        bind()
    elif command in ('帮助', 'help', '?'):
        sender.reply(render_help())
    elif command:
        sender.reply('未识别的子命令。\n\n' + render_help())
    else:
        Administration()


main()

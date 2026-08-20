#[pin:false]
#[disable:false]
#[public:true]
#[rule: ^(无忧计划|无忧计划执行|无忧计划任务检测)$]
#[version: 3.11]
#[price: 0.00]
#[cron: 0 8 * * *]
#[title: 无忧计划]
#[author: sky2022]
#[admin: false]
#[icon: https://img.cdn1.vip/i/69d62b975e88c_1775643543.png]
#[description: 无忧计划自动任务插件，内置每日签到与看广告赚金币！支持立即执行与定时执行，无需抓包、无需验证码。<br>指令:无忧计划、无忧计划执行、无忧计划任务检测<br>格式：手机号#密码<br>内置定时检测与自动执行任务]

# 全局变量声明
today_date = None
today_time = None
proxy_manager = None

import re
import middleware
import requests
import json
import hashlib
import hmac
import urllib.parse
from datetime import datetime
import base64
import random
import secrets
import string
import time
import os
import sys
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# 禁用不安全请求警告
urllib3.disable_warnings(InsecureRequestWarning)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# [param: {"required":true,"key":"dd_WuYou_PluginsData.user_agent","bool":false,"placeholder":"必填项,真机抓包到的Android WebView UA","name":"User-Agent","desc":"建议填真机抓包到的UA保持一致,多账号可用&分隔按顺序对应"}]
# [param: {"required":false,"key":"dd_WuYou_PluginsData.proxy_api","bool":false,"placeholder":"可选,代理API地址","name":"代理API","desc":"执行任务使用的代理API接口(可选)"}]

senderID = middleware.getSenderID()
sender = middleware.Sender(senderID)
userid = sender.getUserID()
uservalue = middleware.bucketGet(bucket='dd_WuYou_bind', key=userid)

# ==================== 常量（来自 APK 逆向 assets/public/assets/index-*.js 的 VITE 配置） ====================

API_BASE = "https://api.dgccvi.com/api/app"     # VITE_API_BASE_URL
ADS_BASE = "https://ads.dgccvi.com/api/app"     # VITE_ADS_API_URL
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


def hmac_hex(key: str, msg: str) -> str:
    return hmac.new(key.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compact_json(payload) -> bytes:
    """与前端 JSON.stringify 一致的紧凑序列化（不转义中文）"""
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def gen_device_id() -> str:
    """复刻前端 deviceId 模块: `${Date.now()}-${Math.random().toString(36).slice(2)}`"""
    rand = "".join(random.choice(string.digits + string.ascii_lowercase) for _ in range(10))
    return f"{int(time.time() * 1000)}-{rand}"


def load_device_store() -> dict:
    """从 bucket 读取 device_id 持久化存储"""
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
    """保存 device_id 持久化到 bucket"""
    try:
        middleware.bucketSet(bucket='dd_WuYou_device', key='store', value=json.dumps(store, ensure_ascii=False))
    except Exception as e:
        print(f"⚠️ 保存 device_id 文件失败: {e}")


def load_ua_config() -> str:
    """从 param 配置读取 User-Agent"""
    return middleware.bucketGet(bucket='dd_WuYou_PluginsData', key='user_agent') or ''


def load_proxy_api() -> str:
    """从 param 配置读取代理 API"""
    return middleware.bucketGet(bucket='dd_WuYou_PluginsData', key='proxy_api') or ''


class ProxyManager:
    """从代理提取 API 获取并维护一个当前代理"""

    def __init__(self, api_url: str):
        self.api_url = api_url
        self.current_proxy = None

    def _extract_proxy(self, text: str):
        if "://" in text:
            return text.strip()
        match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5})', text)
        return match.group(1) if match else None

    def refresh(self):
        if not self.api_url:
            return None
        try:
            resp = requests.get(self.api_url, timeout=5)
            content = resp.text
            proxy_str = None

            if "socks" in content or "://" in content:
                proxy_str = self._extract_proxy(content)

            if not proxy_str:
                try:
                    data = resp.json()
                    if isinstance(data, dict):
                        if 'data' in data and isinstance(data['data'], list) and data['data']:
                            item = data['data'][0]
                            proxy_str = f"{item.get('ip', item.get('IP'))}:{item.get('port', item.get('PORT'))}"
                        elif 'ip' in data and 'port' in data:
                            proxy_str = f"{data['ip']}:{data['port']}"
                except ValueError:
                    pass

            if not proxy_str:
                proxy_str = self._extract_proxy(content)

            if proxy_str:
                if "://" in proxy_str:
                    self.current_proxy = {'http': proxy_str, 'https': proxy_str}
                else:
                    self.current_proxy = {'http': f'http://{proxy_str}', 'https': f'http://{proxy_str}'}
                return self.current_proxy
            return None
        except Exception:
            return None


class AppAttest:
    """App Attest 签名会话（逆向自 AppAttestBridge / AppAttestManager）

    1. POST /api/app/attest {integrity_token:"", device_id, ts, nonce, native_proof}
       native_proof = HMAC-SHA256(ATTEST_KEY, "attest\nts\nnonce\ndevice_id")
    2. 响应 {ok, session_id, session_secret, expires_in}
    3. 后续请求头:
       X-App-Session: session_id
       X-App-Ts:      unix 秒
       X-App-Nonce:   32 位随机 hex
       X-App-Sign:    HMAC-SHA256(session_secret, "METHOD\npath\nts\nnonce\nbody_sha256")
       其中 path 只取 URL 路径部分（不含 query），body_sha256 为请求体(无体则为空串)的 SHA-256 hex
    """

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
        """确保签名会话可用；App 端每 15 分钟刷新一次，这里按有效期提前 60 秒刷新"""
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
            self.log(f"⚠️ attest 失败: {str(data)[:200]}")
        except Exception as e:
            self.log(f"⚠️ attest 异常: {e}")
        return False

    def sign_headers(self, method: str, url: str, body: bytes) -> dict:
        """生成四个签名头；无会话时返回空 dict（服务端暂未强制所有接口验签）"""
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
    def __init__(self, account, password, device_id="", ua=""):
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
        # 代理管理
        self.proxy_api = load_proxy_api()
        self.proxy_mgr = ProxyManager(self.proxy_api)
        # device_id: 显式指定 > 本地持久化 > 新生成并持久化
        self.device_id = device_id or self._load_or_create_device_id()
        self.attest = AppAttest(self.session, self.device_id, self.log)
        self.token = None
        self.user_id = None
        self.user_info = None
        self.total_coins_earned = 0

    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {msg}")

    def _load_or_create_device_id(self) -> str:
        store = load_device_store()
        dev = store.get(self.account)
        if dev:
            return dev
        dev = gen_device_id()
        store[self.account] = dev
        save_device_store(store)
        return dev

    # ==================== 带签名的请求封装 ====================

    def _request(self, method: str, url: str, payload=None, params=None, retry_on_app_required=True):
        body = b"" if payload is None else compact_json(payload)
        headers = dict(self.attest.sign_headers(method, url, body))
        if payload is not None:
            headers["Content-Type"] = "application/json"
        resp = self.session.request(
            method, url, data=body if payload is not None else None,
            params=params, headers=headers, timeout=20,
        )
        # 服务端要求 App 签名时（403 + code=app_required），重新 attest 后重试一次
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

    # ==================== 登录 ====================

    def login(self):
        """登录获取 token（携带 device_id + app_version，与抓包一致）"""
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

        # 设备数量达上限: 换空 device_id 重试（不注册新设备）
        used_fallback = False
        if not token and data.get("code") == "device_limit":
            self.log("⚠️ 设备数量已达上限，尝试用空 device_id 登录（复用已绑定设备）...")
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
            self.log(f"✅ 登录成功 | 用户ID: {self.user_id} | device_id: {self.device_id or '(待回填)'}")
            # 兜底登录或本地无 device_id 时，从服务端回填已绑定设备
            if used_fallback or not self.device_id:
                if self.sync_device_from_server():
                    self.log(f"📱 已回填服务端绑定设备 device_id: {self.device_id}")
                else:
                    self.log("⚠️ 未能回填 device_id（账号可能未绑定任何设备），广告流程可能受限")
            return True
        else:
            self.log(f"❌ 登录失败: {str(data)[:300]}")
            return False

    def sync_device_from_server(self) -> bool:
        """从 /api/app/user-devices 回填当前账号已绑定的 device_id，并持久化 + 用新 device_id 重新 attest"""
        try:
            resp = self._get(USER_DEVICES_URL, params={"device_id": self.device_id})
            data = resp.json()
            devices = data.get("devices", [])
            chosen = next((d for d in devices if d.get("is_current")), None) or (devices[0] if devices else None)
            if chosen and chosen.get("device_id"):
                new_device_id = chosen["device_id"]
                if new_device_id != self.device_id:
                    self.device_id = new_device_id
                    # attest 会话绑定的是旧 device_id，必须用新 device_id 重新签名
                    self.attest.device_id = new_device_id
                    self.attest.session_id = None
                    self.attest.session_secret = None
                    self.attest.ensure(force=True)
                # 持久化，下次直接带上正确 device_id 登录
                store = load_device_store()
                store[self.account] = self.device_id
                save_device_store(store)
                return True
        except Exception as e:
            self.log(f"⚠️ 回填 device_id 失败: {e}")
        return False

    # ==================== 用户/任务信息 ====================

    def get_user_info(self):
        """查询用户信息（含金币余额）"""
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

    def show_tasks(self, data):
        tasks = data.get("tasks", [])
        today = data.get("today", "")
        pending = data.get("pending_claim", 0)
        lines = [f"📅 日期: {today} | 待领取: {pending}个"]
        lines.append("-" * 40)
        total_daily = 0
        total_weekly = 0
        for task in tasks:
            icon = task.get("icon", "📌")
            title = task.get("title", "")
            reward = task.get("reward_coins", 0)
            progress = task.get("current_progress", 0)
            target = task.get("condition_value", 0)
            completed = task.get("is_completed", False)
            claimed = task.get("is_claimed", False)
            period = task.get("period_type", "")
            task_key = task.get("task_key", "")
            if claimed:
                status = "✅ 已领取"
            elif completed:
                status = "🎁 可领取"
            else:
                status = f"⏳ {progress}/{target}"
            lines.append(f"  {icon} {title} | {status} | +{reward}金币 | [{period}] [{task_key}]")
            if period == "daily":
                total_daily += reward
            else:
                total_weekly += reward
        lines.append("-" * 40)
        lines.append(f"💰 每日奖励合计: {total_daily}金币 | 每周奖励合计: {total_weekly}金币")
        return "\n".join(lines)

    # ==================== 每日签到 ====================

    def checkin(self):
        self.log("📅 执行每日签到...")
        resp = self._post(CHECKIN_URL)
        try:
            data = resp.json()
        except Exception:
            data = {}
        coins = data.get("coins_awarded", 0)
        day = data.get("day_number", 0)
        msg = data.get("message", "")
        self.total_coins_earned += coins
        self.log(f"   {msg} | 连续第{day}天 | +{coins}金币")

        self.log("🎁 领取签到奖励...")
        try:
            resp2 = self._post(f"{DAILY_TASKS_URL}/daily_checkin/claim")
            data2 = resp2.json()
            if data2.get("ok"):
                claim_coins = data2.get("coins", 0)
                claim_msg = data2.get("message", "")
                self.total_coins_earned += claim_coins
                self.log(f"   {claim_msg} | +{claim_coins}金币")
            else:
                self.log(f"   ⚠️ 领取签到奖励失败: {str(data2)[:200]}")
        except Exception as e:
            self.log(f"   ⚠️ 领取签到奖励异常: {e}")
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
                self.log(f"   {msg} | +{coins}金币")
            else:
                self.log(f"   ⚠️ 领取失败 ({task_key}): {str(data)[:200]}")
            return data
        except Exception as e:
            self.log(f"   ⚠️ 领取异常 ({task_key}): {e}")
            return {}

    # ==================== 广告联盟（ads.dgccvi.com） ====================

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
        """完整广告观看流程（心跳节奏对齐真实 App）"""
        self.log("📺 开始广告流程...")
        ads_info = self.get_ads_info()

        enabled = ads_info.get("enabled", False)
        # 广告接口上限与账号等级上限取小（金币账户 V1=20 次/天）
        max_views = ads_info.get("max_views_per_day", 20)
        if account_max_views:
            max_views = min(max_views, account_max_views)
        items = ads_info.get("items", [])
        heartbeat_interval = ads_info.get("heartbeat_interval", 30)

        if not enabled:
            self.log("   ⚠️ 广告功能未启用")
            return 0, 0
        if max_views <= 0:
            self.log("   ⚠️ 今日广告次数已用完")
            return 0, 0
        self.log(f"   广告已启用 | 今日可看 {max_views} 次 | 共 {len(items)} 个广告可选")

        success_count = 0
        fail_count = 0

        for i in range(max_views):
            self.log(f"\n{'─' * 40}")
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

            # 模拟真实观看: 开播即报一次心跳
            time.sleep(random.uniform(0.2, 1.5))
            elapsed = random.uniform(0.1, 0.5)
            self.send_heartbeat(play_token, round(elapsed, 2))

            # 按 heartbeat_interval 周期上报（模拟视频 timeupdate）
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

            # 视频结束: 补两次心跳（ended 事件 + complete 前强制上报，与抓包一致）
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

            # 广告间隔: 服务端下发（当前 3-5 秒）
            if i < max_views - 1:
                interval = complete_data.get("next_request_available_in") or \
                    session_data.get("request_interval_seconds") or \
                    random.randint(3, 5)
                self.log(f"   ⏳ 等待 {interval} 秒后请求下一个广告...")
                time.sleep(interval)

        self.log(f"\n{'─' * 40}")
        self.log(f"📊 广告观看汇总: 成功 {success_count} 次 | 失败 {fail_count} 次 | 本次运行累计 +{self.total_coins_earned}金币")
        return success_count, fail_count

    # ==================== 完整执行一个账号 ====================

    def run(self) -> str:
        """执行一个账号的全部任务，返回结果文本"""
        self.log(f"🚀 无忧计划 - 账号: {self.account}")

        if self.proxy_api:
            self.proxy_mgr.refresh()
            self.session.proxies = self.proxy_mgr.current_proxy or {}

        if not self.login():
            return f"❌ 账号 {self.account} 登录失败"

        result_lines = []
        result_lines.append(f"👤 账号 {self.account} 开始执行")

        # 0. 查询当前金币余额与账号等级广告上限
        try:
            user = self.get_user_info()
            nickname = user.get("nickname", "")
            wallet = user.get("wallet", {})
            start_coins = wallet.get("gold_coins", 0)
            account_max_views = user.get("max_alliance_ads_per_day")
            level = (user.get("gold_level") or {}).get("name", "")
            self.log(f"👤 {nickname} | 等级: {level} | 当前金币: {start_coins} | 广告上限: {account_max_views}/天")
        except Exception as e:
            start_coins = 0
            account_max_views = None
            self.log(f"⚠️ 获取用户信息失败: {e}")

        # 1. 获取每日任务
        self.log("📋 获取任务列表...")
        tasks_data = self.get_daily_tasks()
        if tasks_data:
            result_lines.append(self.show_tasks(tasks_data))

        # 2. 每日签到
        self.checkin()

        # 3. 查询设备绑定信息
        try:
            devices_data = self.get_user_devices()
            max_devices = devices_data.get("max_devices", 0)
            used = devices_data.get("devices_used", 0)
            phone_masked = devices_data.get("phone_masked", "")
            self.log(f"📱 设备: {used}/{max_devices} | 手机号: {phone_masked}")
        except Exception as e:
            self.log(f"   ⚠️ 查询设备信息失败: {e}")

        # 4. 看广告赚金币
        self.watch_ads(account_max_views=account_max_views)

        # 5. 领取可领取的任务奖励
        tasks_data = self.get_daily_tasks()
        for task in tasks_data.get("tasks", []):
            task_key = task.get("task_key", "")
            if task.get("is_completed") and not task.get("is_claimed"):
                self.claim_task(task_key)

        # 6. 查询最终金币余额
        try:
            user2 = self.get_user_info()
            end_coins = user2.get("wallet", {}).get("gold_coins", 0)
            earned = end_coins - start_coins
            self.log(f"✨ 任务执行完毕 | 本次获得: {earned}金币 | 总金币: {end_coins}")
            result_lines.append(f"✨ 本次获得: +{earned}金币 | 总金币: {end_coins}")
        except Exception as e:
            self.log(f"⚠️ 查询最终余额失败: {e}")

        return "\n".join(result_lines)


# ==================== 机器人框架交互部分 ====================

def PluginsData():
    """获取插件配置数据（User-Agent / 代理API）"""
    ua = middleware.bucketGet(bucket='dd_WuYou_PluginsData', key='user_agent')
    proxy_api = middleware.bucketGet(bucket='dd_WuYou_PluginsData', key='proxy_api')

    if not ua:
        sender.reply('未配置User-Agent，请在插件配置中填写真机抓包到的Android WebView UA')
        return None
    if not proxy_api:
        print("[提示] 未配置代理API，将直连执行")
    return ua, proxy_api


def bind():
    """绑定账号"""
    sender.reply(
        "=====无忧计划=====\n"
        "🎵 请输入登录参数:\n"
        "📝 格式: 手机号#密码\n"
        "⚠️ 建议私聊登录,密码泄露风险自负\n"
        "⭐ 输入q退出操作\n"
        "====================="
    )

    login_value = sender.input(120000, 1, False)
    if not login_value:
        sender.reply('输入超时！')
        exit(0)
    elif login_value.lower() == 'q':
        sender.reply('退出操作！')
        exit(0)

    # 校验账号格式
    values = login_value.split('#')
    if len(values) < 2:
        sender.reply('登录参数格式错误，请使用 手机号#密码 格式')
        exit(0)
    account = values[0]

    middleware.bucketSet(bucket='dd_WuYou_login', key=account, value=login_value)

    if not uservalue:
        accounts = [account]
        middleware.bucketSet(bucket='dd_WuYou_bind', key=userid, value=f'{accounts}')
        sender.reply("=====绑定成功=====\n✅ 账号添加成功\n🎮 发送[无忧计划]管理账号\n===================")
    else:
        accounts = eval(uservalue)
        if account in accounts:
            sender.reply("更新账号成功，可对我说'无忧计划'对账号进行管理！")
        else:
            accounts.append(account)
            middleware.bucketSet(bucket='dd_WuYou_bind', key=userid, value=f'{accounts}')
            sender.reply("=====绑定成功=====\n✅ 账号添加成功\n🎮 发送[无忧计划]管理账号\n===================")


def execute_account(account, ua):
    """执行单个账号任务"""
    login_info = middleware.bucketGet(bucket='dd_WuYou_login', key=account)
    if not login_info:
        return f"账号 {account} 缺少登录信息，请重新绑定"
    values = login_info.split('#')
    password = values[1] if len(values) > 1 else ''
    if not password:
        return f"账号 {account} 缺少密码，请重新绑定"

    app = WuYouPlan(account, password, ua=ua)
    try:
        result = app.run()
        return result
    except Exception as e:
        return f"账号 {account} 执行异常: {str(e)}"


def execute_all(ua):
    """执行当前用户所有绑定的账号"""
    if not uservalue:
        sender.reply("未绑定任何账号,请先提交账号")
        return

    accounts = eval(uservalue)
    results = []
    for i, account in enumerate(accounts):
        sender.reply(f"正在执行第 {i+1}/{len(accounts)} 个账号: {account}")
        try:
            result = execute_account(account, ua)
            results.append(f"【账号 {i+1}】{result}")
        except Exception as e:
            results.append(f"【账号 {i+1}】{account} 执行异常: {e}")
        if i < len(accounts) - 1:
            time.sleep(random.uniform(1, 2))

    sender.reply("\n\n".join(results))


def Administration():
    """管理账号"""
    global uservalue

    base_message = (
        "=====无忧计划=====\n"
        "1️⃣ 提交账号\n"
        "2️⃣ 执行任务\n"
        "3️⃣ 删除账号\n"
        "4️⃣ 查看账号\n"
    )

    if sender.isAdmin():
        base_message += "5️⃣ 全体执行\n"

    base_message += "⚠️ 输入q退出操作\n==================="

    sender.reply(base_message)

    choice = sender.input(60000, 1, False)
    if choice.lower() == 'q':
        sender.reply('退出操作')
        return

    try:
        choice = int(choice)
        if choice == 1:
            bind()
            return

        elif choice == 2:
            # 执行任务
            if not uservalue:
                sender.reply("未绑定任何账号,请先提交账号")
                return

            accounts = eval(uservalue)
            # 确认执行
            sender.reply(
                f"=====确认执行=====\n"
                f"📱 绑定账号数: {len(accounts)}个\n"
                f"是否立即执行任务?\n"
                f"[y]是 | [n]否\n"
                f"==================="
            )
            confirm = sender.input(60000, 1, False)
            if confirm.lower() != 'y':
                sender.reply('已取消执行')
                return

            execute_all(load_ua_config())
            return

        elif choice == 3:
            # 删除账号
            if not uservalue:
                sender.reply("未绑定任何账号")
                return

            accounts = eval(uservalue)
            message = "=====选择账号=====\n"
            count = 1

            for account in accounts:
                message += f"[{count}] 账号: {account}\n-------------------\n"
                count += 1

            message += "⚠️ 输入q退出操作\n=================="
            sender.reply(message)

            acc_choice = sender.input(60000, 1, False)
            if acc_choice.lower() == 'q':
                sender.reply('退出操作')
                return

            try:
                acc_choice = int(acc_choice)
                if acc_choice < 1 or acc_choice >= count:
                    sender.reply('输入的账号序号无效')
                    return

                selected_account = accounts[acc_choice - 1]

                sender.reply(
                    f"=====删除确认=====\n"
                    f"📱 账号: {selected_account}\n"
                    f"是否确认删除?\n"
                    f"[y]确认 | [n]取消\n"
                    f"==================="
                )

                confirm = sender.input(60000, 1, False)
                if confirm.lower() == 'y':
                    try:
                        accounts.remove(selected_account)
                        if accounts:
                            middleware.bucketSet(bucket='dd_WuYou_bind', key=userid, value=f'{accounts}')
                        else:
                            middleware.bucketDel(bucket='dd_WuYou_bind', key=userid)

                        middleware.bucketDel(bucket='dd_WuYou_login', key=selected_account)
                        sender.reply('删除成功')
                    except Exception as e:
                        sender.reply(f'删除失败: {str(e)}')
                elif confirm.lower() == 'n':
                    sender.reply('已取消删除')
                else:
                    sender.reply('输入无效')

            except ValueError:
                sender.reply('输入无效')
                return

        elif choice == 4:
            # 查看账号
            if not uservalue:
                sender.reply("未绑定任何账号,请先提交账号")
                return

            accounts = eval(uservalue)
            message = "=====已绑定账号=====\n"
            for i, account in enumerate(accounts):
                message += f"[{i+1}] 账号: {account}\n"
            message += f"-------------------\n共 {len(accounts)} 个账号\n==================="
            sender.reply(message)
            return

        elif choice == 5 and sender.isAdmin():
            # 全体执行（管理员用）
            all_binds = middleware.bucketAll(bucket='dd_WuYou_bind')
            if not all_binds:
                sender.reply('没有找到任何用户绑定信息')
                return

            sender.reply("=====确认全体执行=====\n是否对所有用户执行任务?\n[y]是 | [n]否")
            confirm = sender.input(60000, 1, False)
            if confirm.lower() != 'y':
                sender.reply('已取消')
                return

            ua = load_ua_config()
            total = 0
            for uid, bind_value in all_binds.items():
                try:
                    accs = eval(bind_value)
                    for account in accs:
                        sender.reply(f"正在为账号 {account} 执行任务...")
                        result = execute_account(account, ua)
                        sender.reply(result)
                        total += 1
                        time.sleep(random.uniform(1, 2))
                except Exception as e:
                    print(f"[错误] 处理用户 {uid} 时出错: {str(e)}")
                    continue

            sender.reply(f"全体执行完成，共执行 {total} 个账号")
            return

        else:
            sender.reply('输入无效')

    except ValueError:
        sender.reply('输入无效')


def main():
    """主函数"""
    global today_date, today_time, proxy_manager

    today_date = datetime.now().date()
    today_time = str(today_date)

    ua = middleware.bucketGet(bucket='dd_WuYou_PluginsData', key='user_agent')
    proxy_api = middleware.bucketGet(bucket='dd_WuYou_PluginsData', key='proxy_api')
    proxy_manager = ProxyManager(proxy_api or '')

    message = sender.getMessage()

    if message == "无忧计划任务检测":
        # 任务检测：检查是否有绑定账号并发送通知
        if not uservalue:
            sender.reply("当前未绑定任何无忧计划账号")
            return

        accounts = eval(uservalue)
        sender.reply(
            "=====无忧计划任务状态=====\n"
            f"📱 绑定账号数: {len(accounts)}个\n"
            f"📅 今日日期: {today_time}\n"
            f"📌 任务将自动定时执行\n"
            "==================="
        )
        return

    if message == "无忧计划执行":
        # 立即执行任务
        if not uservalue:
            sender.reply("未绑定任何账号,请先提交账号")
            return
        if not ua:
            sender.reply('未配置User-Agent，请在插件配置中填写')
            return
        execute_all(ua)
        return

    Administration()


# 确保主函数被调用
main()

#[pin:false]
#[disable:false]
#[public:true]
#[rule: ^(无忧计划|无忧计划执行|无忧计划任务检测|无忧运行)(\s+.*)?$]
#[version: 5.0]
#[price: 0.00]
#[cron: 0 8 * * *]
#[title: 无忧计划 Pro]
#[author: Manus]
#[admin: false]
#[icon: https://img.cdn1.vip/i/6a8e00f74bda3_1787691255.webp]
#[description: 无忧计划 Pro：账户中心、任务状态、签到及已完成奖励领取、执行报告、历史记录与定时运行。\n主命令：无忧计划\n快捷命令：无忧计划 状态 / 账户 / 执行 / 记录 / 帮助\n说明：本插件不会模拟广告观看、伪造进度或规避服务端限制；需要用户完成的交互任务请在官方客户端内自行完成后，再刷新状态。]

"""
无忧计划 Pro v5.0

设计目标：
1. 一个主入口，兼容旧命令；
2. 账户数据按用户隔离，聊天输出与运行记录均脱敏；
3. 状态检查、签到、领取已完成奖励和报告展示职责清晰；
4. 全程保持 TLS 校验，不使用 eval，不把异常详情直接暴露给用户；
5. 不实现广告模拟、虚假心跳、设备/代理规避等能力。

注意：本文件依赖宿主环境提供 middleware 模块及 bucket 存储能力。
"""

import hashlib
import json
import re
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import middleware
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ─────────────────────────────────────────────────────────────────────────────
# 插件配置
# ─────────────────────────────────────────────────────────────────────────────
API_BASE = "https://api.dgccvi.com/api/app"
APP_VERSION = "1.0.9"
MAX_ACCOUNTS_PER_USER = 10
MAX_WORKERS = 3
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 20
HISTORY_LIMIT = 20

LOGIN_URL = f"{API_BASE}/auth/login"
ME_URL = f"{API_BASE}/me"
DAILY_TASKS_URL = f"{API_BASE}/daily-tasks"
CHECKIN_URL = f"{API_BASE}/checkin"
USER_DEVICES_URL = f"{API_BASE}/user-devices"

# 账户、设备、执行记录均按用户独立存放；不再以手机号作为全局主键。
ACCOUNTS_BUCKET = "dd_WuYou_v5_accounts"
DEVICES_BUCKET = "dd_WuYou_v5_devices"
HISTORY_BUCKET = "dd_WuYou_v5_history"
SETTINGS_BUCKET = "dd_WuYou_v5_settings"

DEFAULT_UA = (
    "Mozilla/5.0 (Linux; Android 14; Mobile) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Version/4.0 Chrome/120.0.0.0 Mobile Safari/537.36"
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ─────────────────────────────────────────────────────────────────────────────
# 通用工具
# ─────────────────────────────────────────────────────────────────────────────
def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_text() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def short_time(value: str) -> str:
    if not value:
        return "从未"
    return value[5:16] if len(value) >= 16 else value


def mask_account(account: str) -> str:
    """只用于展示，永不在聊天、日志中返回完整账号。"""
    account = str(account or "")
    if len(account) >= 7:
        return f"{account[:3]}****{account[-4:]}"
    if len(account) >= 3:
        return f"{account[:1]}***{account[-1:]}"
    return "***"


def clean_text(value: Any, limit: int = 80) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    return text[:limit]


def account_uid(owner_id: str, account: str) -> str:
    raw = f"{owner_id}:{account}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:18]


def safe_json_load(raw: Any, default: Any) -> Any:
    if not raw:
        return default
    try:
        data = json.loads(raw)
        return data
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def safe_bucket_get(bucket: str, key: str, default: str = "") -> str:
    try:
        return middleware.bucketGet(bucket=bucket, key=key) or default
    except Exception:
        return default


def safe_bucket_set(bucket: str, key: str, value: str) -> bool:
    try:
        middleware.bucketSet(bucket=bucket, key=key, value=value)
        return True
    except Exception:
        return False


def safe_bucket_del(bucket: str, key: str) -> bool:
    try:
        middleware.bucketDel(bucket=bucket, key=key)
        return True
    except Exception:
        return False


def normalize_alias(value: str, fallback: str) -> str:
    alias = re.sub(r"[\r\n\t]+", " ", value or "").strip()
    alias = re.sub(r"\s+", " ", alias)
    return alias[:16] if alias else fallback


def parse_index(text: str, upper: int) -> Optional[int]:
    try:
        index = int((text or "").strip())
        if 1 <= index <= upper:
            return index - 1
    except ValueError:
        pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 数据仓储
# ─────────────────────────────────────────────────────────────────────────────
class AccountRepository:
    """用户级账户仓储。旧版迁移只在同一用户旧绑定存在时触发。"""

    def __init__(self, owner_id: str):
        self.owner_id = str(owner_id)

    def _load(self) -> List[Dict[str, Any]]:
        data = safe_json_load(safe_bucket_get(ACCOUNTS_BUCKET, self.owner_id), [])
        if not isinstance(data, list):
            return []
        result = []
        for item in data:
            if isinstance(item, dict) and item.get("id") and item.get("account"):
                result.append(item)
        return result

    def _save(self, accounts: List[Dict[str, Any]]) -> bool:
        payload = json.dumps(accounts, ensure_ascii=False, separators=(",", ":"))
        return safe_bucket_set(ACCOUNTS_BUCKET, self.owner_id, payload)

    def list(self) -> List[Dict[str, Any]]:
        accounts = self._load()
        if not accounts:
            accounts = self._migrate_legacy_accounts()
        return accounts

    def get(self, record_id: str) -> Optional[Dict[str, Any]]:
        return next((x for x in self.list() if x.get("id") == record_id), None)

    def add(self, account: str, password: str, alias: str, ua: str = "") -> Tuple[bool, str]:
        account = re.sub(r"\s+", "", account or "")
        password = str(password or "").strip()
        if len(account) < 3:
            return False, "账号长度不足，请重新输入。"
        if len(password) < 1:
            return False, "密码不能为空。"

        records = self.list()
        existing = next((x for x in records if x.get("account") == account), None)
        fallback = f"账号 {len(records) + 1}"
        payload = {
            "id": account_uid(self.owner_id, account),
            "alias": normalize_alias(alias, fallback),
            "account": account,
            "password": password,
            "ua": clean_text(ua, 500) or DEFAULT_UA,
            "created_at": now_text(),
            "updated_at": now_text(),
            "last_run_at": existing.get("last_run_at", "") if existing else "",
            "last_status": existing.get("last_status", "未检查") if existing else "未检查",
            "last_earned": existing.get("last_earned", 0) if existing else 0,
        }
        if existing:
            records = [payload if x.get("id") == existing.get("id") else x for x in records]
            ok = self._save(records)
            return ok, "账户资料已更新。" if ok else "保存失败，请稍后重试。"
        if len(records) >= MAX_ACCOUNTS_PER_USER:
            return False, f"单个用户最多绑定 {MAX_ACCOUNTS_PER_USER} 个账户。"
        records.append(payload)
        ok = self._save(records)
        return ok, "账户已添加。" if ok else "保存失败，请稍后重试。"

    def update_alias(self, record_id: str, alias: str) -> Tuple[bool, str]:
        records = self.list()
        changed = False
        for item in records:
            if item.get("id") == record_id:
                item["alias"] = normalize_alias(alias, item.get("alias") or "未命名账户")
                item["updated_at"] = now_text()
                changed = True
        if not changed:
            return False, "账户不存在或不属于当前用户。"
        return (True, "账户名称已更新。") if self._save(records) else (False, "保存失败，请稍后重试。")

    def delete(self, record_id: str) -> Tuple[bool, str]:
        records = self.list()
        target = next((x for x in records if x.get("id") == record_id), None)
        if not target:
            return False, "账户不存在或不属于当前用户。"
        records = [x for x in records if x.get("id") != record_id]
        if not self._save(records):
            return False, "删除失败，请稍后重试。"
        safe_bucket_del(DEVICES_BUCKET, f"{self.owner_id}:{record_id}")
        return True, "账户已删除。"

    def update_run_state(self, record_id: str, result: Dict[str, Any]) -> None:
        records = self.list()
        for item in records:
            if item.get("id") == record_id:
                item["last_run_at"] = now_text()
                item["last_status"] = "成功" if result.get("ok") else result.get("code", "失败")
                item["last_earned"] = result.get("earned", 0) if result.get("ok") else 0
                item["updated_at"] = now_text()
        self._save(records)

    def _migrate_legacy_accounts(self) -> List[Dict[str, Any]]:
        """仅迁移当前 user_id 已绑定的旧账户；迁移失败不影响新版本运行。"""
        old_raw = safe_bucket_get("dd_WuYou_bind", self.owner_id)
        old_accounts = safe_json_load(old_raw, [])
        if not isinstance(old_accounts, list):
            return []
        migrated: List[Dict[str, Any]] = []
        for old_account in old_accounts[:MAX_ACCOUNTS_PER_USER]:
            account = str(old_account or "").strip()
            login_raw = safe_bucket_get("dd_WuYou_login", account)
            parts = login_raw.split("#", 2)
            if len(parts) < 2 or not parts[0] or not parts[1]:
                continue
            migrated.append({
                "id": account_uid(self.owner_id, parts[0]),
                "alias": f"迁移账户 {len(migrated) + 1}",
                "account": parts[0],
                "password": parts[1],
                "ua": parts[2] if len(parts) > 2 and parts[2] else DEFAULT_UA,
                "created_at": now_text(),
                "updated_at": now_text(),
                "last_run_at": "",
                "last_status": "已迁移，待检查",
                "last_earned": 0,
            })
        if migrated:
            self._save(migrated)
        return migrated


class DeviceRepository:
    def __init__(self, owner_id: str):
        self.owner_id = str(owner_id)

    def get_or_create(self, record_id: str) -> str:
        key = f"{self.owner_id}:{record_id}"
        value = safe_bucket_get(DEVICES_BUCKET, key)
        if value:
            return value
        generated = f"plugin-{uuid.uuid4().hex[:24]}"
        safe_bucket_set(DEVICES_BUCKET, key, generated)
        return generated


class HistoryRepository:
    def __init__(self, owner_id: str):
        self.owner_id = str(owner_id)

    def list(self) -> List[Dict[str, Any]]:
        data = safe_json_load(safe_bucket_get(HISTORY_BUCKET, self.owner_id), [])
        return data if isinstance(data, list) else []

    def append(self, item: Dict[str, Any]) -> None:
        history = self.list()
        # 记录中不保存 password、token、完整 account 或接口原文。
        history.insert(0, item)
        safe_bucket_set(
            HISTORY_BUCKET,
            self.owner_id,
            json.dumps(history[:HISTORY_LIMIT], ensure_ascii=False, separators=(",", ":")),
        )


# ─────────────────────────────────────────────────────────────────────────────
# HTTP API 客户端
# ─────────────────────────────────────────────────────────────────────────────
class ApiError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class WuYouApiClient:
    """仅封装用户主动触发的状态、签到和已完成奖励领取请求。"""

    def __init__(self, account: Dict[str, Any], device_id: str):
        self.account = account
        self.device_id = device_id
        self.session = requests.Session()
        retry = Retry(
            total=2,
            connect=2,
            read=2,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(("GET", "POST")),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.headers.update({
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "origin": "https://localhost",
            "referer": "https://localhost/",
            "x-requested-with": "com.dgccvi.app",
            "user-agent": account.get("ua") or DEFAULT_UA,
            "accept-language": "zh-CN,zh;q=0.9",
        })

    def _request(self, method: str, url: str, payload: Optional[Dict[str, Any]] = None,
                 params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=payload,
                params=params,
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                verify=True,
            )
        except requests.Timeout as exc:
            raise ApiError("NETWORK_TIMEOUT", "网络请求超时，请稍后重试。") from exc
        except requests.RequestException as exc:
            raise ApiError("NETWORK_ERROR", "网络连接失败，请检查网络后再试。") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise ApiError("BAD_RESPONSE", "服务返回格式异常，请稍后重试。") from exc

        if response.status_code == 401:
            raise ApiError("AUTH_EXPIRED", "登录信息已失效，请在账户管理中重新保存密码。")
        if response.status_code == 429:
            raise ApiError("RATE_LIMITED", "请求过于频繁，请稍后再试。")
        if response.status_code >= 500:
            raise ApiError("SERVICE_BUSY", "服务暂时繁忙，请稍后再试。")
        if response.status_code >= 400:
            message = clean_text(data.get("message") or data.get("error") or "请求失败", 80)
            raise ApiError("API_ERROR", message)
        if not isinstance(data, dict):
            raise ApiError("BAD_RESPONSE", "服务返回格式异常，请稍后重试。")
        return data

    def login(self) -> Dict[str, Any]:
        payload = {
            "account": self.account.get("account"),
            "password": self.account.get("password"),
            "device_id": self.device_id,
            "platform": "android",
            "app_version": APP_VERSION,
        }
        data = self._request("POST", LOGIN_URL, payload)
        token = data.get("token")
        if not token:
            msg = clean_text(data.get("message") or data.get("code") or "账号或密码错误", 80)
            raise ApiError("LOGIN_FAILED", msg)
        self.session.headers.update({"authorization": f"Bearer {token}"})
        return data

    def get_profile(self) -> Dict[str, Any]:
        data = self._request("GET", ME_URL, params={
            "device_id": self.device_id,
            "platform": "android",
            "app_version": APP_VERSION,
        })
        user = data.get("user")
        return user if isinstance(user, dict) else {}

    def get_daily_tasks(self) -> Dict[str, Any]:
        return self._request("GET", DAILY_TASKS_URL)

    def get_devices(self) -> Dict[str, Any]:
        return self._request("GET", USER_DEVICES_URL, params={"device_id": self.device_id})

    def checkin(self) -> Dict[str, Any]:
        return self._request("POST", CHECKIN_URL, {})

    def claim_task(self, task_key: str) -> Dict[str, Any]:
        return self._request("POST", f"{DAILY_TASKS_URL}/{task_key}/claim", {})


# ─────────────────────────────────────────────────────────────────────────────
# 业务服务
# ─────────────────────────────────────────────────────────────────────────────
class AccountService:
    def __init__(self, owner_id: str):
        self.owner_id = str(owner_id)
        self.accounts = AccountRepository(self.owner_id)
        self.devices = DeviceRepository(self.owner_id)

    def inspect(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """只读检查，不执行签到或领取。"""
        started = time.monotonic()
        try:
            client = WuYouApiClient(record, self.devices.get_or_create(record["id"]))
            client.login()
            profile = client.get_profile()
            tasks_data = client.get_daily_tasks()
            devices = client.get_devices()
            wallet = profile.get("wallet") or {}
            tasks = tasks_data.get("tasks") or []
            if not isinstance(tasks, list):
                tasks = []
            completed = sum(1 for task in tasks if isinstance(task, dict) and task.get("is_completed"))
            claimable = sum(
                1 for task in tasks
                if isinstance(task, dict) and task.get("is_completed") and not task.get("is_claimed")
            )
            return {
                "record_id": record["id"],
                "alias": record.get("alias", "未命名账户"),
                "account": mask_account(record.get("account", "")),
                "ok": True,
                "code": "OK",
                "nickname": clean_text(profile.get("nickname"), 18),
                "coins": wallet.get("gold_coins", 0),
                "level": clean_text((profile.get("gold_level") or {}).get("name"), 16),
                "tasks_total": len(tasks),
                "tasks_completed": completed,
                "tasks_claimable": claimable,
                "devices_used": devices.get("devices_used", "-"),
                "devices_max": devices.get("max_devices", "-"),
                "duration": round(time.monotonic() - started, 1),
            }
        except ApiError as exc:
            return self._failed(record, exc.code, exc.message, started)
        except Exception:
            return self._failed(record, "UNKNOWN_ERROR", "发生未知异常，请稍后重试。", started)

    def execute(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """执行用户允许自动完成的签到与已完成奖励领取；不包含广告自动化。"""
        started = time.monotonic()
        claimed: List[str] = []
        checkin_status = "未执行"
        try:
            client = WuYouApiClient(record, self.devices.get_or_create(record["id"]))
            client.login()
            before_profile = client.get_profile()
            before_coins = (before_profile.get("wallet") or {}).get("gold_coins", 0) or 0

            # 签到失败不终止后续“已完成奖励”的领取；服务端会负责幂等判断。
            try:
                checkin_data = client.checkin()
                checkin_status = clean_text(checkin_data.get("message") or "签到已处理", 40)
            except ApiError as exc:
                checkin_status = "已完成" if "已" in exc.message else "暂不可用"

            tasks_data = client.get_daily_tasks()
            tasks = tasks_data.get("tasks") or []
            if not isinstance(tasks, list):
                tasks = []
            for task in tasks:
                if not isinstance(task, dict):
                    continue
                task_key = clean_text(task.get("task_key"), 80)
                if not task_key or not task.get("is_completed") or task.get("is_claimed"):
                    continue
                try:
                    claim_data = client.claim_task(task_key)
                    if claim_data.get("ok"):
                        claimed.append(clean_text(task.get("title") or task_key, 20))
                except ApiError:
                    # 单个奖励领取失败不影响其他已经完成的奖励。
                    continue

            after_profile = client.get_profile()
            after_coins = (after_profile.get("wallet") or {}).get("gold_coins", before_coins) or before_coins
            result = {
                "record_id": record["id"],
                "alias": record.get("alias", "未命名账户"),
                "account": mask_account(record.get("account", "")),
                "ok": True,
                "code": "OK",
                "nickname": clean_text(after_profile.get("nickname"), 18),
                "earned": max(0, after_coins - before_coins),
                "coins": after_coins,
                "checkin": checkin_status,
                "claimed": claimed,
                "duration": round(time.monotonic() - started, 1),
            }
            self.accounts.update_run_state(record["id"], result)
            return result
        except ApiError as exc:
            result = self._failed(record, exc.code, exc.message, started)
            self.accounts.update_run_state(record["id"], result)
            return result
        except Exception:
            result = self._failed(record, "UNKNOWN_ERROR", "发生未知异常，请稍后重试。", started)
            self.accounts.update_run_state(record["id"], result)
            return result

    @staticmethod
    def _failed(record: Dict[str, Any], code: str, message: str, started: float) -> Dict[str, Any]:
        return {
            "record_id": record.get("id", ""),
            "alias": record.get("alias", "未命名账户"),
            "account": mask_account(record.get("account", "")),
            "ok": False,
            "code": code,
            "message": clean_text(message, 100),
            "earned": 0,
            "duration": round(time.monotonic() - started, 1),
        }


# ─────────────────────────────────────────────────────────────────────────────
# 消息呈现层
# ─────────────────────────────────────────────────────────────────────────────
def divider() -> str:
    return "────────────────────"


def render_home(accounts: List[Dict[str, Any]]) -> str:
    successful = sum(1 for item in accounts if item.get("last_status") == "成功")
    return (
        "无忧计划 Pro\n"
        f"{divider()}\n"
        f"账户：{len(accounts)} 个   最近成功：{successful} 个\n"
        "\n"
        "[1] 账户管理      [2] 今日状态\n"
        "[3] 立即执行      [4] 执行记录\n"
        "[5] 使用帮助      [0] 退出\n"
        "\n"
        "也可直接发送：无忧计划 状态 / 账户 / 执行 / 记录"
    )


def render_accounts(records: List[Dict[str, Any]]) -> str:
    if not records:
        return "账户管理\n────────────────────\n当前没有账户。输入“新增”开始添加，或输入 q 返回。"
    lines = ["账户管理", divider()]
    for index, record in enumerate(records, 1):
        last = record.get("last_status", "未检查")
        earned = record.get("last_earned", 0)
        lines.append(
            f"[{index}] {record.get('alias', '未命名')}  {mask_account(record.get('account', ''))}\n"
            f"    状态：{last}  最近：{short_time(record.get('last_run_at', ''))}  收益：+{earned}"
        )
    lines.extend([
        "",
        "输入：新增 / 编辑 1 / 删除 1 / 执行 1 / q 返回",
        "密码不会在列表、报告或运行记录中显示。",
    ])
    return "\n".join(lines)


def render_status(results: List[Dict[str, Any]]) -> str:
    if not results:
        return "今日状态\n────────────────────\n当前没有可检查的账户。"
    lines = ["今日状态", divider()]
    good = sum(1 for item in results if item.get("ok"))
    lines.append(f"检查：{len(results)} 个账户   正常：{good} 个   异常：{len(results) - good} 个")
    lines.append("")
    for item in results:
        if item.get("ok"):
            task_text = f"任务 {item.get('tasks_completed', 0)}/{item.get('tasks_total', 0)}"
            claimable = item.get("tasks_claimable", 0)
            extra = f"，可领 {claimable}" if claimable else ""
            nickname = f"（{item.get('nickname')}）" if item.get("nickname") else ""
            lines.append(
                f"{item.get('alias')}{nickname}  {item.get('account')}\n"
                f"  正常｜金币 {item.get('coins', 0)}｜{task_text}{extra}｜设备 {item.get('devices_used')}/{item.get('devices_max')}"
            )
        else:
            lines.append(
                f"{item.get('alias')}  {item.get('account')}\n"
                f"  待处理｜{item.get('message', '检查失败')}"
            )
    lines.append("\n提示：需要用户完成的互动任务，请在官方客户端完成后再执行“无忧计划 状态”刷新。")
    return "\n".join(lines)


def render_preview(records: List[Dict[str, Any]]) -> str:
    lines = ["执行预览", divider(), f"准备执行：{len(records)} 个账户", ""]
    for record in records:
        lines.append(f"• {record.get('alias', '未命名')}  {mask_account(record.get('account', ''))}")
    lines.extend([
        "",
        "将执行：每日签到、领取服务端标记为“已完成且未领取”的奖励。",
        "不会自动模拟广告观看、伪造进度或绕过限制。",
        "回复 y 开始；回复其他内容取消。",
    ])
    return "\n".join(lines)


def render_report(results: List[Dict[str, Any]], run_id: str, elapsed: float) -> str:
    total = len(results)
    good = sum(1 for item in results if item.get("ok"))
    earned = sum(int(item.get("earned", 0) or 0) for item in results if item.get("ok"))
    lines = [
        f"无忧计划 Pro · 执行报告 #{run_id}",
        divider(),
        f"执行：{total} 个   成功：{good} 个   待处理：{total - good} 个   收益：+{earned}",
        "",
    ]
    for item in results:
        if item.get("ok"):
            claimed = item.get("claimed") or []
            claim_text = f"；领取 {len(claimed)} 项" if claimed else ""
            lines.append(
                f"{item.get('alias')}  {item.get('account')}\n"
                f"  完成｜+{item.get('earned', 0)}｜总金币 {item.get('coins', 0)}｜签到：{item.get('checkin', '已处理')}{claim_text}"
            )
        else:
            next_step = "请检查网络后重试"
            if item.get("code") in ("AUTH_EXPIRED", "LOGIN_FAILED"):
                next_step = "请进入账户管理重新保存密码"
            lines.append(
                f"{item.get('alias')}  {item.get('account')}\n"
                f"  待处理｜{item.get('message', '执行失败')}｜{next_step}"
            )
    lines.extend([
        "",
        f"耗时：{elapsed:.1f} 秒   时间：{datetime.now().strftime('%H:%M')}",
        "发送“无忧计划 记录”可查看近期执行摘要。",
    ])
    return "\n".join(lines)


def render_history(items: List[Dict[str, Any]]) -> str:
    if not items:
        return "执行记录\n────────────────────\n暂无记录。"
    lines = ["执行记录", divider()]
    for item in items[:8]:
        lines.append(
            f"#{item.get('run_id', '--')}  {short_time(item.get('created_at', ''))}\n"
            f"  执行 {item.get('total', 0)}｜成功 {item.get('success', 0)}｜收益 +{item.get('earned', 0)}｜{item.get('trigger', '手动')}"
        )
    lines.append("\n仅保留最近 20 次脱敏摘要。")
    return "\n".join(lines)


def render_help() -> str:
    return (
        "无忧计划 Pro · 帮助\n"
        f"{divider()}\n"
        "无忧计划                 打开控制台\n"
        "无忧计划 账户            管理账户\n"
        "无忧计划 状态            只读检查账户、任务与余额\n"
        "无忧计划 执行            签到并领取已完成奖励\n"
        "无忧计划 记录            查看近期执行摘要\n"
        "\n"
        "旧命令兼容：无忧计划执行、无忧计划任务检测、无忧运行\n"
        "\n"
        "隐私说明：账号在输出中始终脱敏；密码、令牌和原始接口响应不会写入执行记录。"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 聊天控制器
# ─────────────────────────────────────────────────────────────────────────────
class PluginController:
    def __init__(self):
        self.sender_id = middleware.getSenderID()
        self.sender = middleware.Sender(self.sender_id)
        self.owner_id = str(self.sender.getUserID())
        self.repo = AccountRepository(self.owner_id)
        self.history = HistoryRepository(self.owner_id)
        self.service = AccountService(self.owner_id)

    def reply(self, text: str) -> None:
        self.sender.reply(text)

    def ask(self, prompt: str, timeout_ms: int = 120000) -> str:
        self.reply(prompt)
        value = self.sender.input(timeout_ms, 1, False)
        return (value or "").strip()

    def select_records(self, source: List[Dict[str, Any]], raw: str) -> List[Dict[str, Any]]:
        text = (raw or "").strip().lower()
        if text in ("", "all", "全部"):
            return source
        selected: List[Dict[str, Any]] = []
        seen = set()
        for part in re.split(r"[,，\s]+", text):
            if not part:
                continue
            if "-" in part:
                start_end = part.split("-", 1)
                try:
                    start, end = int(start_end[0]), int(start_end[1])
                except ValueError:
                    continue
                for index in range(max(1, start), min(len(source), end) + 1):
                    if index not in seen:
                        selected.append(source[index - 1])
                        seen.add(index)
                continue
            try:
                index = int(part)
                if 1 <= index <= len(source) and index not in seen:
                    selected.append(source[index - 1])
                    seen.add(index)
            except ValueError:
                continue
        return selected

    def run_parallel(self, records: List[Dict[str, Any]], mode: str) -> List[Dict[str, Any]]:
        if not records:
            return []
        worker = self.service.inspect if mode == "inspect" else self.service.execute
        indexed: Dict[str, Dict[str, Any]] = {}
        with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(records))) as executor:
            futures = {executor.submit(worker, record): record for record in records}
            for future in as_completed(futures):
                record = futures[future]
                try:
                    indexed[record["id"]] = future.result()
                except Exception:
                    indexed[record["id"]] = {
                        "record_id": record["id"],
                        "alias": record.get("alias", "未命名账户"),
                        "account": mask_account(record.get("account", "")),
                        "ok": False,
                        "code": "UNKNOWN_ERROR",
                        "message": "发生未知异常，请稍后重试。",
                        "earned": 0,
                    }
        return [indexed[record["id"]] for record in records]

    def add_account(self) -> None:
        account = self.ask("添加账户 · 第 1 步\n────────────────────\n请输入账号。建议在私聊中操作；输入 q 取消。")
        if not account or account.lower() == "q":
            self.reply("已取消添加。")
            return
        password = self.ask("添加账户 · 第 2 步\n────────────────────\n请输入密码。密码不会回显到聊天或运行记录；输入 q 取消。")
        if not password or password.lower() == "q":
            self.reply("已取消添加。")
            return
        alias = self.ask("添加账户 · 第 3 步\n────────────────────\n为该账户设置一个别名，例如“主号”；直接回复回车使用默认名称。")
        ua = self.ask("添加账户 · 可选设置\n────────────────────\n如需自定义 UA 请发送；回复 - 使用默认配置。")
        if ua == "-":
            ua = ""
        ok, message = self.repo.add(account, password, alias, ua)
        if ok:
            record = next((x for x in self.repo.list() if x.get("account") == re.sub(r"\s+", "", account)), None)
            alias_text = record.get("alias") if record else "新账户"
            self.reply(f"添加完成\n────────────────────\n{alias_text} · {mask_account(account)}\n\n建议下一步发送“无忧计划 状态”验证账户状态。")
        else:
            self.reply(f"添加失败\n────────────────────\n{message}")

    def manage_accounts(self) -> None:
        while True:
            records = self.repo.list()
            command = self.ask(render_accounts(records), 120000)
            if not command or command.lower() in ("q", "返回", "0"):
                self.reply("已返回控制台。")
                return
            if command in ("新增", "添加", "1"):
                self.add_account()
                continue
            match = re.match(r"^(编辑|改名)\s*(\d+)$", command)
            if match:
                index = parse_index(match.group(2), len(records))
                if index is None:
                    self.reply("账户序号无效。")
                    continue
                new_alias = self.ask(f"请输入“{records[index].get('alias')}”的新别名：")
                if new_alias and new_alias.lower() != "q":
                    ok, msg = self.repo.update_alias(records[index]["id"], new_alias)
                    self.reply(msg)
                continue
            match = re.match(r"^删除\s*(\d+)$", command)
            if match:
                index = parse_index(match.group(1), len(records))
                if index is None:
                    self.reply("账户序号无效。")
                    continue
                target = records[index]
                confirm = self.ask(
                    f"确认删除 {target.get('alias')} · {mask_account(target.get('account', ''))}？\n"
                    "回复 DELETE 确认；其他内容取消。",
                    60000,
                )
                if confirm == "DELETE":
                    _, msg = self.repo.delete(target["id"])
                    self.reply(msg)
                else:
                    self.reply("已取消删除。")
                continue
            match = re.match(r"^执行\s*(\d+)$", command)
            if match:
                index = parse_index(match.group(1), len(records))
                if index is None:
                    self.reply("账户序号无效。")
                    continue
                self.execute_records([records[index]], trigger="账户管理")
                continue
            self.reply("无法识别。可输入：新增 / 编辑 1 / 删除 1 / 执行 1 / q")

    def check_status(self) -> None:
        records = self.repo.list()
        if not records:
            self.reply("今日状态\n────────────────────\n尚未绑定账户。发送“无忧计划 账户”添加账户。")
            return
        self.reply(f"正在检查 {len(records)} 个账户，请稍候…")
        results = self.run_parallel(records, mode="inspect")
        self.reply(render_status(results))

    def execute_records(self, records: List[Dict[str, Any]], trigger: str = "手动") -> None:
        if not records:
            self.reply("没有可执行的账户。")
            return
        started = time.monotonic()
        self.reply(f"执行中\n────────────────────\n正在处理 {len(records)} 个账户；完成后会发送一条汇总报告。")
        results = self.run_parallel(records, mode="execute")
        elapsed = time.monotonic() - started
        run_id = datetime.now().strftime("%m%d%H%M")
        summary = {
            "run_id": run_id,
            "created_at": now_text(),
            "trigger": trigger,
            "total": len(results),
            "success": sum(1 for item in results if item.get("ok")),
            "earned": sum(int(item.get("earned", 0) or 0) for item in results if item.get("ok")),
        }
        self.history.append(summary)
        self.reply(render_report(results, run_id, elapsed))

    def execute_with_confirmation(self) -> None:
        records = self.repo.list()
        if not records:
            self.reply("立即执行\n────────────────────\n尚未绑定账户。请先在账户管理中添加。")
            return
        selection = self.ask(
            "选择执行账户\n────────────────────\n"
            + "\n".join(f"[{i}] {x.get('alias')}  {mask_account(x.get('account', ''))}" for i, x in enumerate(records, 1))
            + "\n\n回复 all 执行全部；或输入 1,3 / 2-4；输入 q 取消。"
        )
        if not selection or selection.lower() == "q":
            self.reply("已取消执行。")
            return
        selected = self.select_records(records, selection)
        if not selected:
            self.reply("未识别到有效账户序号。")
            return
        confirm = self.ask(render_preview(selected), 60000)
        if confirm.lower() != "y":
            self.reply("已取消执行。")
            return
        self.execute_records(selected, trigger="手动")

    def run_scheduled(self) -> None:
        records = self.repo.list()
        if not records:
            return
        self.execute_records(records, trigger="定时")

    def dispatch(self) -> None:
        raw = (self.sender.getMessage() or "").strip()
        # 兼容旧命令；定时任务可继续使用“无忧运行”。
        if raw == "无忧运行":
            self.run_scheduled()
            return
        if raw == "无忧计划执行":
            self.execute_with_confirmation()
            return
        if raw == "无忧计划任务检测":
            self.check_status()
            return

        command = raw[len("无忧计划"):].strip() if raw.startswith("无忧计划") else ""
        if command in ("状态", "检测", "今日状态"):
            self.check_status()
        elif command in ("账户", "账号", "管理"):
            self.manage_accounts()
        elif command in ("执行", "运行", "开始"):
            self.execute_with_confirmation()
        elif command in ("记录", "历史"):
            self.reply(render_history(self.history.list()))
        elif command in ("帮助", "help", "?"):
            self.reply(render_help())
        elif command:
            self.reply("未识别的子命令。\n\n" + render_help())
        else:
            self.open_home()

    def open_home(self) -> None:
        choice = self.ask(render_home(self.repo.list()), 90000)
        route = {
            "1": self.manage_accounts,
            "2": self.check_status,
            "3": self.execute_with_confirmation,
            "4": lambda: self.reply(render_history(self.history.list())),
            "5": lambda: self.reply(render_help()),
        }
        if choice in ("", "0", "q", "Q"):
            self.reply("无忧计划已退出。")
            return
        handler = route.get(choice)
        if handler:
            handler()
        else:
            self.reply("无效选择。发送“无忧计划 帮助”查看可用命令。")


def main() -> None:
    try:
        PluginController().dispatch()
    except Exception:
        # 不向聊天回显潜在敏感堆栈信息；便于用户重试且避免泄露内部数据。
        try:
            sender_id = middleware.getSenderID()
            middleware.Sender(sender_id).reply("无忧计划暂时不可用，请稍后重试。")
        except Exception:
            pass


main()

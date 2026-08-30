#[pin:false]
#[disable:false]
#[public:true]
#[rule: ^(知了快看|知了快看执行|知了快看任务检测|知了运行)$]
#[version: 1.0]
#[price: 0.00]
#[cron: 0 9 * * *]
#[title: 知了快看]
#[author: 知了快看插件版]
#[admin: false]
#[icon: https://img.cdn1.vip/i/6a8e00f74bda3_1787691255.webp]
#[description: 知了快看自动任务插件，刷视频领现金+金币+自动提现！<br>指令:知了快看、知了快看执行、知了快看任务检测、知了运行<br>格式：账号标识#凭据#UA(可选)<br>凭据支持: UID直登 / zqkd_param整串 / ZHILIAO键值对<br>内置定时检测与自动执行任务<br>增强代理与UA池]
#[param: {"required":false,"key":"dd_ZhiLiao_PluginsData.proxy_api","bool":false,"placeholder":"可选,代理API地址","name":"代理API","desc":"代理API接口地址,每个账号独立获取代理"}]

from __future__ import annotations
import re
import middleware
import os
import sys
import time
import random
import json
import hashlib
import hmac
import base64
import gzip
import string
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from typing import Any, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ==================== 增强UA池（20个真机Android UA）====================
BUILTIN_UAS = [
    "Mozilla/5.0 (Linux; Android 9; ELE-AL00 Build/HUAWEIELE-AL00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/66.0.3359.126 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; ELE-AL00 Build/HUAWEIELE-AL00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/76.0.3809.89 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; EML-AL00 Build/HUAWEIEML-AL00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.99 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; SEA-AL10 Build/HUAWEISEA-AL10; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.99 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; HMA-AL00 Build/HUAWEIHMA-AL00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/79.0.3945.93 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; OXF-AN10 Build/HUAWEIOXF-AN10; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/76.0.3809.89 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; HLK-AL00 Build/HONORHLK-AL00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.99 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 9; JSN-AL00a Build/HONORJSN-AL00a; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/76.0.3809.89 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; MI 9 Build/RKQ1.200826.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.99 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; Mi 10 Build/QKQ1.191117.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/76.0.3809.89 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; M2011K2C Build/RKQ1.200928.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.99 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; MI 8 SE Build/QKQ1.190828.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.99 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 9; MIX 2S Build/PKQ1.180729.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/76.0.3809.89 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; 21091116C Build/RP1A.200720.011; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.99 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; M2004J7BC Build/RP1A.200720.011; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.99 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 9; Redmi Note 8 Pro Build/PPR1.180610.011; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/66.0.3359.126 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 9; PACM00 Build/PPR1.180610.011; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/76.0.3809.89 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 8.1.0; OPPO R11s Build/OPM1.171019.011; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/76.0.3809.89 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 9; V1813BT Build/PKQ1.181030.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/76.0.3809.89 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; GM1910 Build/QKQ1.190716.003; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/78.0.3904.96 Mobile Safari/537.36",
]

PROXY_RETRY_TIMES = 3
PROXY_VALIDATE_URL = "http://httpbin.org/ip"
ENABLE_DIRECT_FALLBACK = True
REQUEST_TIMEOUT = 30

senderID = middleware.getSenderID()
sender = middleware.Sender(senderID)
userid = sender.getUserID()
uservalue = middleware.bucketGet(bucket='dd_ZhiLiao_bind', key=userid)

# ============================================================
# 一、加解密算法 (知了快看核心)
# ============================================================

try:
    from Crypto.Cipher import DES, AES
    from Crypto.Util.Padding import pad, unpad
except Exception as _e:
    sys.stderr.write("\n[错误] 缺少 pycryptodome: %s\n请先安装: pip install pycryptodome\n" % _e)
    sys.exit(1)

SPKI_B64 = ("MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA1E_mX-gaRQSNkmvPplyoSaa2k019s5jvfkw940Tf"
            "_gmjmxDQPyqJOePqK9gvA4lM0tdU5vGCCcQB6PgdgfIyhzs20kJzWSHtNJ0TvcM4f269UGVpZ0Ju8ErIy_ST"
            "6bFJLKLZzLewcttJUPwfvbeMtlKzDXa74zRkQqHS9MGZ4inKaFFILtOwFtJYHRzYRU5ctUP790FcxevpFK-q1"
            "5AXS3kRARqLmPUeh_BQUSqOZwMsMtMWyz56-c6ZBsLWKFGehfVjfZcAGVjeZ3nsEesXQf8J3xFFgULu9sj0Ou"
            "YgjolaRTdO9RJ-DMUWDwjdUAJLwaHPWZF2GsrixncrL9S8VQIDAQAB")

VERSION2_KEY = "jdvylqchJZrfw0o2DgAbsmCGUapF1YChc"
VERSION6_KEY = "zWpfzystJLrfw7o3SgGlMmGGPupK2YLhB"
VERSION15_KEY = ("AAAAB3NzaC1yc2EAAAADAQABAAABAQC1WAth281wjZj5XhGU9Iza5EXzOy5U/AKgGxF14svnCEWrTH6i"
                 "3lZd+lMTFLvTakGI5l1RJmutFRku6CvDVCEc7dJURVWsrgQTFNBuu0t5WOkoUY0zNa05pejDmBC4w4Msc"
                 "H2OexCrKfHNEYi/FpjBJv1bwjU0luxt/cvsjBjlthgY47I4KNy+T953CpBiYQmkSJZUBzsN2Zz+jEA+CvL"
                 "EK9BPHBlKcz0GupalgnHHSnS/JoUz8+RTjZr1O2sjSyrcg0LL+vWeCnJN07Uv4jJaTDqc6Ig1Mw+TJrrsAR"
                 "xoA+Frc66Qo7GFxACimuJ1LeCc9iFlMzZNZly3JxYAR019")

_RND = string.digits + string.ascii_letters

LEMON = "https://lemon-api.52leho.com"
TBC = "https://tbc-svc.52leho.com"
APP_PKG = "new.liao.view"
UA = "android"
AD_UA = "okhttp/3.12.2"
MEDIA_APP_ID = "sspJA8HT1eIS373e"

BRUSH_SUBMIT_SECONDS = 60
BRUSH_INTERVAL = 8
READTIME_SECONDS = 300
DEFAULT_MINUTES = 30
SLOT_PRICE_MIN = 20000.0
SLOT_PRICE_MAX = 39999.9
WITHDRAW_TARGET = 1.5
KEEPALIVE_DURATION = 300
KEEPALIVE_INTERVAL = 20


def _udp(v: Any) -> str:
    bs = str(v).encode("utf-8")
    out = []
    for b in bs:
        if (48 <= b <= 57) or (65 <= b <= 90) or (97 <= b <= 122) or b in (45, 46, 95, 126):
            out.append(chr(b))
        elif b == 0x20:
            out.append("+")
        else:
            out.append("%%%02X" % b)
    return "".join(out)


def uzw(c: str) -> str:
    b64 = SPKI_B64
    s = b64[9:]
    s = s[:len(s) - 5]
    s = s[len(s) - 36:]
    s = s[:len(s) - (ord(c) % 10)]
    return s


def des_key_for(cFtr: str) -> bytes:
    return uzw(cFtr).encode("utf-8")[:8]


def aes_key() -> bytes:
    return uzw("a").encode("utf-8")[:16]


def _jenc(v: Any) -> str:
    bs = str(v).encode("utf-8")
    out = []
    for b in bs:
        if (48 <= b <= 57) or (65 <= b <= 90) or (97 <= b <= 122) or b in (45, 46, 95, 126):
            out.append(chr(b))
        elif b == 0x20:
            out.append("+")
        else:
            out.append("%%%02X" % b)
    return "".join(out)


def _enc_params_str(params: Dict[str, Any]) -> str:
    return "&".join("%s=%s" % (k, _jenc(v)) for k, v in params.items())


def _ar_aor(key: str, params_str: str) -> str:
    md5k = hashlib.md5(key.encode("utf-8")).digest()[:8]
    str3 = base64.urlsafe_b64encode(md5k).decode()
    iv = str3[:8].encode("utf-8")
    des_key = key.encode("utf-8")[:8]
    ct = DES.new(des_key, DES.MODE_CBC, iv).encrypt(pad(params_str.encode("utf-8"), 8))
    return str3 + base64.urlsafe_b64encode(ct).decode()


def _mou_aor(c: str, inner: str) -> str:
    i = (ord(c) % 10) % 3
    tail = "".join(random.choice(_RND) for _ in range(i))
    return c + inner + tail


def _encrypt_str(plaintext: str) -> str:
    cFtr = random.choice(_RND)
    key = uzw(cFtr)
    inner = _ar_aor(key, plaintext)
    return _mou_aor(cFtr, inner)


def build_param(params: Dict[str, Any], extra: Optional[Dict[str, Any]] = None) -> str:
    p = dict(params)
    if extra:
        p.update(extra)
    params_str = _enc_params_str(p)
    return _encrypt_str(params_str)


def build_ssp_q(params: Dict[str, Any]) -> str:
    cFtr = random.choice(_RND)
    key = uzw(cFtr)
    return _mou_aor(cFtr, _ar_aor(key, _enc_params_str(params)))


def sign_sorted_md5(params: Dict[str, Any], tail: str = VERSION2_KEY) -> str:
    S = "".join("%s=%s" % (k, params[k]) for k in sorted(params) if k != "sign" and params[k] != "")
    return hashlib.md5((S + tail).encode("utf-8")).hexdigest()


def token_sorted_md5(params: Dict[str, Any], tail: str = VERSION6_KEY) -> str:
    S = "".join("%s=%s" % (k, params[k]) for k in sorted(params) if k != "token" and params[k] != "")
    return hashlib.md5((S + tail).encode("utf-8")).hexdigest()


def make_jwt(claims: Dict[str, Any], key: str = VERSION15_KEY) -> str:
    header = base64.urlsafe_b64encode(
        json.dumps({"typ": "JWT", "alg": "HS512"}, separators=(",", ":")).encode()
    ).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({k: _udp(v) for k, v in sorted(claims.items()) if v != ""},
                   separators=(",", ":")).encode()
    ).rstrip(b"=").decode()
    signing_input = "%s.%s" % (header, payload)
    sig = hmac.new(key.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha512).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
    return "%s.%s" % (signing_input, sig_b64)


def build_signed_single_md5(params, extra=None) -> str:
    p = dict(params)
    if extra:
        p.update(extra)
    p["sign"] = sign_sorted_md5(p)
    return build_param(p)


def build_signed_single_token(params, extra=None) -> str:
    p = dict(params)
    if extra:
        p.update(extra)
    p["token"] = token_sorted_md5(p)
    return build_param(p)


def build_signed_single_jwt(params, extra=None) -> str:
    p = dict(params)
    if extra:
        p.update(extra)
    p["token"] = make_jwt(p)
    return build_param(p)


def build_signed_double_plain(device, business=None) -> str:
    full = dict(device)
    if business:
        full.update(business)
    full.pop("sign", None)
    full.pop("token", None)
    S = "".join("%s=%s" % (k, full[k]) for k in sorted(full) if full[k] != "")
    sign = S + VERSION2_KEY
    linked = {k: _udp(full[k]) for k in full}
    linked["sign"] = sign
    p_plaintext = "&".join("%s=%s" % (k, _udp(v)) for k, v in linked.items())
    p_value = _encrypt_str(p_plaintext)
    outer = dict(device)
    if business:
        outer.update(business)
    outer["p"] = p_value
    return build_param(outer)


def dec_param(val: str) -> Dict[str, str]:
    cFtr = val[0]
    rest = val[1:]
    i = (ord(cFtr) % 10) % 3
    if i:
        rest = rest[:-i]
    str3 = rest[:12]
    body = rest[12:]
    iv = str3[:8].encode("utf-8")
    des_key = uzw(cFtr).encode("utf-8")[:8]
    raw = base64.urlsafe_b64decode(body)
    plain = unpad(DES.new(des_key, DES.MODE_CBC, iv).decrypt(raw), 8).decode("utf-8", "replace")
    out = {}
    for seg in plain.split("&"):
        if not seg:
            continue
        k, _, v = seg.partition("=")
        out[k] = v
    return out


def dec_resp(text: str) -> dict:
    text = text.strip()
    if text.startswith("{"):
        try:
            return json.loads(text)
        except Exception:
            pass
    raw = base64.b64decode(text)
    plain = unpad(AES.new(aes_key(), AES.MODE_ECB).decrypt(raw), 16).decode("utf-8", "replace")
    return json.loads(plain)


class StaticProvider:
    def encrypt(self, params, extra=None, need_sign=False, sign_mode="none"):
        if not need_sign:
            return build_param(params, extra)
        if sign_mode == "md5":
            return build_signed_single_md5(params, extra)
        if sign_mode == "token":
            return build_signed_single_token(params, extra)
        if sign_mode == "jwt":
            return build_signed_single_jwt(params, extra)
        if sign_mode == "double":
            return build_signed_double_plain(params, extra)
        raise ValueError("unknown sign_mode: %r" % sign_mode)

    def decrypt(self, zqkd_param):
        return dec_param(zqkd_param)

    def decrypt_resp(self, text):
        return dec_resp(text)


# ============================================================
# 二、插件数据管理
# ============================================================

def mask_account(account: str) -> str:
    if len(account) >= 7:
        return account[:3] + "****" + account[-4:]
    return account


def get_account_owner(account: str) -> str:
    return middleware.bucketGet(bucket='dd_ZhiLiao_owner', key=account) or ""


def set_account_owner(account: str, owner_id: str):
    middleware.bucketSet(bucket='dd_ZhiLiao_owner', key=account, value=owner_id)


def remove_account_owner(account: str):
    middleware.bucketDel(bucket='dd_ZhiLiao_owner', key=account)


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


def register_user(user_id: str):
    users_str = middleware.bucketGet(bucket='dd_ZhiLiao_global', key='registered_users') or '[]'
    try:
        users = json.loads(users_str)
        if not isinstance(users, list):
            users = []
    except Exception:
        users = []
    if user_id not in users:
        users.append(user_id)
        try:
            middleware.bucketSet(bucket='dd_ZhiLiao_global', key='registered_users', value=json.dumps(users, ensure_ascii=False))
        except Exception as e:
            print(f"注册全局用户失败: {e}")


def get_all_accounts_global() -> list:
    users_str = middleware.bucketGet(bucket='dd_ZhiLiao_global', key='registered_users') or '[]'
    try:
        users = json.loads(users_str)
        if not isinstance(users, list):
            users = []
    except Exception:
        users = []
    all_accounts = []
    for uid in users:
        user_value = middleware.bucketGet(bucket='dd_ZhiLiao_bind', key=uid)
        user_accounts = parse_accounts(user_value)
        for acc in user_accounts:
            if acc and acc not in all_accounts:
                all_accounts.append(acc)
    return all_accounts


def load_proxy_api() -> str:
    return middleware.bucketGet(bucket='dd_ZhiLiao_PluginsData', key='proxy_api') or ''


# ============================================================
# 三、代理管理器 (适配 urllib)
# ============================================================

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
            proxy_support = urllib.request.ProxyHandler(proxies)
            opener = urllib.request.build_opener(proxy_support)
            req = urllib.request.Request(PROXY_VALIDATE_URL)
            resp = opener.open(req, timeout=15)
            if resp.getcode() == 200:
                try:
                    self.proxy_ip = json.loads(resp.read().decode()).get("origin", "未知")
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
                resp = urllib.request.urlopen(self.api_url, timeout=15)
                proxy_info = self._parse_proxy_response(resp.read().decode())
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

    def get_opener(self):
        if self.current_proxy:
            return urllib.request.build_opener(urllib.request.ProxyHandler(self.current_proxy))
        return urllib.request.build_opener()


# ============================================================
# 四、HTTP 通用层 (带代理支持)
# ============================================================

DEVICE_DEFAULT = {
    "app_name": "new_liao_view",
    "app_pkg": "new.liao.view",
    "app_version": "1.7.5",
    "app-version": "1.7.5",
    "appid": "wxdb76b366c1f1b2e4",
    "version_code": "45",
    "inner_version": "202608191646",
    "channel": "c1002",
    "device_brand": "Xiaomi",
    "device_model": "24053PY09C",
    "device_platform": "android",
    "device_type": "2",
    "os_version": "UKQ1.240116.001 release-keys",
    "os_api": "34",
    "resolution": "1236x2474",
    "dpi": "3.0",
    "memory": "11",
    "storage": "227.02",
    "language": "zh-CN",
    "carrier": "中国电信",
    "network_type": "WIFI",
    "access": "WIFI",
    "mobile_type": "1",
    "mi": "1",
    "is_debug": "0",
    "dev_mode": "0",
    "sim": "1",
    "rom_version": "UKQ1.240116.001 release-keys",
}

TASK_CONFIG = {
    "common": {},
    "scoreTime": {"sign_mode": "md5", "params": {"type": "1", "time": str(BRUSH_SUBMIT_SECONDS)}},
    "rewardView": {"sign_mode": "md5", "params": {"rid": ""}},
    "readTime": {"sign_mode": "md5", "params": {"type": "2", "time": str(READTIME_SECONDS)}},
    "readScore": {"sign_mode": "md5", "params": {}},
    "readWithdraw": {"sign_mode": "md5", "params": {"type": "2"}},
    "userinfo": {"sign_mode": "md5", "params": {}, "method": "GET"},
    "userdata": {"sign_mode": "md5", "params": {}, "method": "GET"},
    "bonusWithdraw": {"sign_mode": "jwt", "params": {"type": "61"}},
    "getPaymentList": {"sign_mode": "jwt", "params": {}},
    "redWithdraw": {"sign_mode": "jwt", "params": {"type": "__DYNAMIC__", "score": "__DYNAMIC__"}},
    "adConversion": {"sign_mode": "md5", "params": {"extra": "[]", "is_install": "0"}},
    "rewardVideoCrv": {"sign_mode": "md5", "params": {}},
    "csjCpa": {"sign_mode": "md5", "params": {}},
    "ylhCpa": {"sign_mode": "md5", "params": {}},
    "getTaskList": {"sign_mode": "jwt", "params": {"install_alipay": "1"}},
    "machine": {"sign_mode": "md5", "params": {}},
    "biTf": {"sign_mode": "none", "params": {}},
    "BiCollect": {"sign_mode": "double", "params": {}},
    "exchange": {"sign_mode": "double", "params": {}},
    "getFeedBrowseTaskList": {"sign_mode": "double", "params": {}},
    "adlickstart": {"sign_mode": "double", "params": {"task_id": "__DYNAMIC__"}},
    "adlickend": {"sign_mode": "double", "params": {"task_id": "__DYNAMIC__", "task_click": "0", "task_click_num": "0"}},
    "bannerstatus": {"sign_mode": "double", "params": {"task_id": "__DYNAMIC__", "page_click": "3", "page_slide": "9", "page_stay": "101"}},
    "readRewardClaim": {"sign_mode": "double", "params": {"action": "task_score_optimize", "param": "", "video_id": "0", "media_extra": "", "extra": ""}},
    "readWithdrawClaim": {"sign_mode": "double", "params": {"action": "read_withdraw", "param": "", "video_id": "0", "media_extra": "__DYNAMIC__", "extra": ""},
        "media_extra_template": {"media_app_id": "sspJA8HT1eIS373e", "media_scene_id": "010", "media_slot_id": "20120118", "media_verify": "__DYNAMIC__", "position_id": "1032", "slot_platform": "BQT", "slot_price": "__RANDOM_SLOT_PRICE__", "slot_type": "RewardVideo", "tactics_mold": "bidding"}},
    "toGetReward": {"sign_mode": "double", "params": {"action": "bonus_video_ad_award", "param": "1", "video_id": "0", "media_extra": "__DYNAMIC__"},
        "media_extra_template": {"media_app_id": "sspJA8HT1eIS373e", "media_replace_score": 0, "media_scene_id": "47", "media_slot_id": "986301995", "media_verify": "__DYNAMIC__", "params_action_type": "DEEPLINK", "params_app_name": "淘宝", "params_app_package": "com.taobao.taobao", "params_slot_type": "RewardVideo", "params_storage": {}, "position_id": "1032", "slot_platform": "CSJ", "slot_price": "367.71", "slot_type": "RewardVideo", "tactics_mold": "bidding"}},
    "openRedEnvelopeCash": {"sign_mode": "md5", "params": {}},
    "claimRedEnvelope": {"sign_mode": "md5", "params": {"index": "__DYNAMIC__", "media_extra": "__DYNAMIC__"},
        "media_extra_template": {"media_app_id": "sspJA8HT1eIS373e", "media_replace_score": 0, "media_scene_id": "010", "media_slot_id": "20120118", "media_verify": "__DYNAMIC__", "params_action_type": "DOWNLOAD", "params_app_name": "百度", "params_app_package": "com.baidu.searchbox", "params_slot_type": "RewardVideo", "params_storage": {}, "position_id": "1032", "slot_platform": "BQT", "slot_price": "__RANDOM_SLOT_PRICE__", "slot_type": "RewardVideo", "tactics_mold": "bidding"}},
    "adlist": {"params": {}},
    "getBonusPaymentList": {"sign_mode": "jwt", "params": {}},
    "configInfo": {"sign_mode": "none", "params": {}, "method": "GET"},
    "configAudit": {"sign_mode": "jwt", "params": {}},
    "configDid": {"sign_mode": "jwt", "params": {}},
    "countStart": {"sign_mode": "md5", "params": {}},
    "getinfo": {"sign_mode": "none", "params": {}, "method": "GET"},
    "mediaConfig": {"sign_mode": "none", "params": {}, "method": "GET"},
    "appUpdate": {"sign_mode": "jwt", "params": {}},
}

_idx = [0]
def _next_index():
    _idx[0] += 1
    return str(_idx[0])


def random_slot_price():
    return f"{round(random.uniform(SLOT_PRICE_MIN, SLOT_PRICE_MAX), 1)}"


class ZhiLiaoHTTP:
    def __init__(self, proxy_mgr: ProxyManager = None):
        self.proxy_mgr = proxy_mgr
        self.session_cookie = ""
        self._auth = {}

    def _capture_session_cookie(self, resp):
        try:
            cookies = resp.headers.get_all("Set-Cookie") or []
        except Exception:
            cookies = []
        if not cookies:
            single = resp.headers.get("Set-Cookie")
            if single:
                cookies = [single]
        for c in cookies:
            head = c.split(";")[0].strip()
            if head.lower().startswith("phpsessid="):
                val = head[len("PHPSESSID="):]
                if val and val != self.session_cookie:
                    self.session_cookie = val
                    print(f"[session] 已自动更新 PHPSESSID")
                return

    def _update_session_from_resp_obj(self, obj):
        if not isinstance(obj, dict):
            return
        candidates = []
        items = obj.get("items")
        if isinstance(items, dict):
            candidates.append(items)
        candidates.append(obj)
        for c in candidates:
            for k in ("PHPSESSID", "phpsessid", "session", "sessid", "sess_id"):
                v = c.get(k)
                if v and isinstance(v, str) and len(v) >= 8 and v != self.session_cookie:
                    self.session_cookie = v
                    print(f"[session] 已自动获取PHPSESSID")
                    return

    def request(self, method, url, data=None, headers=None, timeout=30):
        req = urllib.request.Request(url, data=data, method=method)
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        opener = self.proxy_mgr.get_opener() if self.proxy_mgr else urllib.request.build_opener()
        try:
            resp = opener.open(req, timeout=timeout)
            raw = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            text = raw.decode("utf-8", "replace")
            self._capture_session_cookie(resp)
            return {"success": True, "text": text, "status": resp.getcode()}
        except urllib.error.HTTPError as e:
            return {"success": False, "http": e.code, "raw": e.read().decode("utf-8", "replace")[:200]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def http_post(self, path, base, task_key, provider, runtime_extra=None, plain=False):
        cfg = TASK_CONFIG.get(task_key, {})
        sign_mode = cfg.get("sign_mode", "none")
        params = dict(TASK_CONFIG.get("common", {}))
        params.update(cfg.get("params", {}))
        if runtime_extra:
            params.update(runtime_extra)

        common = dict(DEVICE_DEFAULT)
        common.update(self._auth)
        common["request_time"] = str(int(time.time()))
        if sign_mode == "md5":
            common["device_type"] = "2"
            common["channel_code"] = "c1002"
        else:
            common["device_type"] = "android"
        if sign_mode == "double":
            common["index"] = _next_index()
        if task_key == "getFeedBrowseTaskList":
            common["support_wechat"] = "0"
        if not common.get("uid"):
            common.pop("uid", None)
            common.pop("account", None)

        zq = provider.encrypt(common, extra=params, need_sign=(sign_mode != "none"), sign_mode=sign_mode)
        url = base + path
        data = ("zqkd_param=" + urllib.parse.quote(zq, safe="")).encode("utf-8")
        headers = {
            "User-Agent": UA,
            "device-platform": "android",
            "app-pkg": APP_PKG,
            "Accept-Encoding": "gzip",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        if self.session_cookie:
            headers["Cookie"] = f"PHPSESSID={self.session_cookie}"
        r = self.request("POST", url, data=data, headers=headers, timeout=30)
        if not r["success"]:
            return {"success": False, "http": r.get("http", 0), "raw": r.get("raw", "")}
        if plain:
            try:
                return json.loads(r["text"])
            except Exception:
                return {"success": False, "error": "json_fail", "raw": r["text"][:200]}
        result = provider.decrypt_resp(r["text"])
        self._update_session_from_resp_obj(result)
        return result

    def http_get(self, path, base, task_key, provider, runtime_extra=None):
        cfg = TASK_CONFIG.get(task_key, {})
        sign_mode = cfg.get("sign_mode", "none")
        params = dict(TASK_CONFIG.get("common", {}))
        params.update(cfg.get("params", {}))
        if runtime_extra:
            params.update(runtime_extra)
        common = dict(DEVICE_DEFAULT)
        common.update(self._auth)
        common["request_time"] = str(int(time.time()))
        if sign_mode == "md5":
            common["device_type"] = "2"
            common["channel_code"] = "c1002"
        else:
            common["device_type"] = "android"
        if not common.get("uid"):
            common.pop("uid", None)
            common.pop("account", None)
        zq = provider.encrypt(common, extra=params, need_sign=(sign_mode != "none"), sign_mode=sign_mode)
        url = base + path + "?zqkd_param=" + urllib.parse.quote(zq, safe="")
        headers = {
            "User-Agent": UA,
            "device-platform": "android",
            "app-pkg": APP_PKG,
            "Accept-Encoding": "gzip",
        }
        if self.session_cookie:
            headers["Cookie"] = f"PHPSESSID={self.session_cookie}"
        r = self.request("GET", url, headers=headers, timeout=30)
        if not r["success"]:
            return {"success": False, "http": r.get("http", 0), "raw": r.get("raw", "")}
        result = provider.decrypt_resp(r["text"])
        self._update_session_from_resp_obj(result)
        return result

    def set_auth(self, auth_dict):
        self._auth = auth_dict


# ============================================================
# 五、凭据解析与管理
# ============================================================

def parse_account_info(login_info: str):
    parts = login_info.split('#')
    if len(parts) >= 3:
        return parts[0], parts[1], '#'.join(parts[2:])
    elif len(parts) == 2:
        return parts[0], parts[1], ""
    return parts[0], "", ""


def detect_cred_type(cred: str) -> str:
    cred = cred.strip()
    if not cred:
        return "unknown"
    if cred.isdigit():
        return "uid"
    if len(cred) > 50 and '=' in cred and '&' not in cred:
        return "param"
    if '=' in cred and ('#' in cred or '&' in cred or 'uid=' in cred or 'zqkey=' in cred):
        return "zhiliao"
    if len(cred) > 30:
        return "param"
    return "unknown"


def apply_uid(uid_str, http):
    auth = {
        "uid": uid_str.strip(), "account": uid_str.strip(),
        "union_id": "", "user_cert": "0",
        "zqkey": "", "zqkey_id": "", "s_ad": "",
        "oaid": "", "openudid": "", "androidid": "",
        "device_id": "", "sm_device_id": "", "app_device_id": "",
    }
    http.set_auth(auth)
    return auth


def apply_param(raw, http):
    _pd = dec_param(raw)
    auth = {
        "uid": "", "account": "",
        "union_id": "", "user_cert": "0",
        "zqkey": "", "zqkey_id": "", "s_ad": "",
        "oaid": "", "openudid": "", "androidid": "",
        "device_id": "", "sm_device_id": "", "app_device_id": "",
    }
    if _pd.get("device_id"): auth["device_id"] = urllib.parse.unquote_plus(_pd["device_id"])
    if _pd.get("openudid"): auth["openudid"] = urllib.parse.unquote_plus(_pd["openudid"])
    if _pd.get("oaid"): auth["oaid"] = urllib.parse.unquote_plus(_pd["oaid"])
    if _pd.get("androidid"): auth["androidid"] = urllib.parse.unquote_plus(_pd["androidid"])
    if _pd.get("sm_device_id"): auth["sm_device_id"] = urllib.parse.unquote_plus(_pd["sm_device_id"])
    if _pd.get("app_device_id"): auth["app_device_id"] = urllib.parse.unquote_plus(_pd["app_device_id"])
    if _pd.get("uid"): auth["uid"] = urllib.parse.unquote_plus(_pd["uid"])
    if _pd.get("account") and not auth["uid"]: auth["uid"] = urllib.parse.unquote_plus(_pd["account"])
    if _pd.get("union_id"): auth["union_id"] = urllib.parse.unquote_plus(_pd["union_id"])
    if _pd.get("user_cert"): auth["user_cert"] = urllib.parse.unquote_plus(_pd["user_cert"])
    if _pd.get("zqkey"): auth["zqkey"] = urllib.parse.unquote_plus(_pd["zqkey"])
    if _pd.get("zqkey_id"): auth["zqkey_id"] = urllib.parse.unquote_plus(_pd["zqkey_id"])
    if _pd.get("s_ad"): auth["s_ad"] = urllib.parse.unquote_plus(_pd["s_ad"])
    auth["account"] = auth["uid"]
    http.set_auth(auth)
    return auth


def apply_zhiliao(raw, http):
    kv = {}
    for seg in raw.split("#"):
        seg = seg.strip()
        if not seg or "=" not in seg:
            continue
        k, v = seg.split("=", 1)
        kv[k.strip()] = v.strip()
    auth = {
        "uid": kv.get("uid", ""), "account": kv.get("uid", ""),
        "union_id": kv.get("union_id", ""), "user_cert": kv.get("user_cert", "0"),
        "zqkey": kv.get("zqkey", ""), "zqkey_id": kv.get("zqkey_id", ""), "s_ad": kv.get("s_ad", ""),
        "oaid": kv.get("oaid", ""), "openudid": kv.get("openudid", ""), "androidid": kv.get("androidid", ""),
        "device_id": kv.get("device_id", ""), "sm_device_id": kv.get("sm_device_id", ""), "app_device_id": kv.get("app_device_id", ""),
    }
    if kv.get("session"):
        http.session_cookie = kv.get("session")
    http.set_auth(auth)
    return auth


# ============================================================
# 六、企业微信通知
# ============================================================

def _qywx_request(url, data=None, method="GET"):
    req = urllib.request.Request(url, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        req.data = body
    resp = urllib.request.urlopen(req, timeout=10)
    return json.loads(resp.read().decode("utf-8"))


def get_qywx_token(corpid, corpsecret):
    url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corpid}&corpsecret={corpsecret}"
    try:
        data = _qywx_request(url)
        if data.get("errcode") == 0:
            return data.get("access_token")
    except Exception:
        pass
    return None


def send_qywx_msg(content):
    qywx_am = os.environ.get("QYWX_AM", "").strip()
    if not qywx_am:
        return False
    parts = qywx_am.split(",")
    if len(parts) < 4:
        print("[通知] QYWX_AM 格式错误")
        return False
    corpid, corpsecret, touser, agentid = parts[0], parts[1], parts[2], parts[3]
    token = get_qywx_token(corpid, corpsecret)
    if not token:
        return False
    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
    payload = {"touser": touser, "msgtype": "text", "agentid": int(agentid), "text": {"content": content}}
    try:
        data = _qywx_request(url, data=payload, method="POST")
        if data.get("errcode") == 0:
            print("[通知] 企业微信消息发送成功")
            return True
        else:
            print(f"[通知] 企业微信消息发送失败: {data}")
            return False
    except Exception as e:
        print(f"[通知] 企业微信消息发送异常: {e}")
        return False


# ============================================================
# 七、任务实现 (Bot)
# ============================================================

def _brief(r):
    if not isinstance(r, dict):
        return str(r)[:80]
    code = r.get("code") or r.get("error_code")
    msg = r.get("message", "")
    if code in (0, "0") or msg in ("执行成功", "success"):
        return "成功"
    if code == 10001 or "参数" in str(msg):
        return "参数错误"
    if code == 10002 or "登录" in str(msg) or "session" in str(msg).lower():
        return "登录失效"
    if "message" in r:
        return f"{msg}" if msg else f"错误码{code}"
    if "items" in r and isinstance(r["items"], dict):
        keys = list(r["items"].keys())[:4]
        return "数据:" + ",".join(keys)
    return json.dumps(r, ensure_ascii=False)[:80]


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


class Bot:
    def __init__(self, http: ZhiLiaoHTTP, provider, proxy_mgr=None):
        self.http = http
        self.p = provider
        self.proxy_mgr = proxy_mgr
        self.total_seconds = 0
        self.username = ""
        self.stats = {
            "cash_gained": 0.0,
            "red_gained": 0.0,
            "withdraw_amount": 0.0,
            "withdraw_ok": False,
            "bonus_withdraw": 0.0,
            "bonus_withdraw_ok": False,
            "red_withdraw": 0.0,
            "red_withdraw_ok": False,
        }
        self.result_lines = []
        self.ad_error = ""
        self.checkin_status = ""

    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}"
        self.result_lines.append(line)
        print(line)

    def score_time_once(self):
        return self.http.http_post("/v18/feed/scoreTime.json", LEMON, "scoreTime", self.p)

    def read_time_once(self):
        return self.http.http_post("/v18/feed/readTime.json", LEMON, "readTime", self.p)

    def reward_view_once(self):
        return self.http.http_post("/v18/feed/rewardView.json", LEMON, "rewardView", self.p)

    def machine_once(self):
        return self.http.http_post("/v15/config/machine.json", LEMON, "machine", self.p)

    def bi_tf_once(self):
        return self.http.http_post("/v18/bi/tf.json", LEMON, "biTf", self.p)

    def bi_collect_once(self):
        return self.http.http_post("/v18/Bi/collect.json", LEMON, "BiCollect", self.p)

    def exchange_once(self):
        return self.http.http_post("/v17/TaskScoreOptimize/exchange.json", LEMON, "exchange", self.p)

    def get_bonus_payment_list(self):
        return self.http.http_post("/v17/UserRed/getBonusPaymentList.json", LEMON, "getBonusPaymentList", self.p)

    def config_info_once(self):
        return self.http.http_get("/v15/config/info.json", LEMON, "configInfo", self.p)

    def config_audit_once(self):
        return self.http.http_post("/v15/config/audit.json", LEMON, "configAudit", self.p)

    def config_did_once(self):
        return self.http.http_post("/v15/config/did.json", LEMON, "configDid", self.p)

    def count_start_once(self):
        return self.http.http_post("/v6/count/start.json", LEMON, "countStart", self.p)

    def getinfo_once(self):
        return self.http.http_get("/v3/user/getinfo.json", LEMON, "getinfo", self.p)

    def media_config_once(self):
        return self.http.http_get("/v15/config/media_config.json", LEMON, "mediaConfig", self.p)

    def app_update_once(self):
        return self.http.http_post("/V17/Menu/appUpdate.json", LEMON, "appUpdate", self.p)

    def read_score_once(self):
        return self.http.http_post("/v18/task/readScore.json", LEMON, "readScore", self.p)

    def read_withdraw_once(self):
        return self.http.http_post("/v18/task/readWithdraw.json", LEMON, "readWithdraw", self.p)

    def get_task_list(self):
        return self.http.http_post("/v17/TaskScoreOptimize/getTaskList.json", LEMON, "getTaskList", self.p)

    def csj_cpa_once(self):
        return self.http.http_post("/v18/task/csjCpa.json", LEMON, "csjCpa", self.p)

    def ad_conversion_once(self):
        return self.http.http_post("/v18/task/adConversion.json", LEMON, "adConversion", self.p)

    def reward_video_crv_once(self):
        return self.http.http_post("/v18/task/rewardVideoCrv.json", LEMON, "rewardVideoCrv", self.p)

    def claim_read_reward(self, max_rounds=8):
        gained = 0
        for i in range(max_rounds):
            r = self.http.http_post("/v18/task/readScore.json", LEMON, "readScore", self.p, {"type": "2"})
            items = (r.get("items") or {})
            lst = items.get("list") or []
            claimable = [t for t in lst if str(t.get("status")) == "1"]
            if not claimable:
                break
            sra = items.get("send_reward_action") or {"reward_action": "look_video_article_get_score"}
            if isinstance(sra, str):
                sra = {"reward_action": sra}
            param = json.dumps(sra, ensure_ascii=False, separators=(",", ":"))
            cfg = dict(TASK_CONFIG.get("readRewardClaim", {}))
            cfg_params = dict(cfg.get("params", {}))
            cfg_params["param"] = param
            cfg["params"] = cfg_params
            TASK_CONFIG["readRewardClaim"] = cfg
            g = self.http.http_post("/v5/CommonReward/toGetReward.json", LEMON, "readRewardClaim", self.p)
            g_items = (g.get("items") or {})
            sc = g_items.get("score")
            if g.get("success") or g.get("error_code") in (0, "0"):
                try:
                    gained += int(float(sc))
                except (TypeError, ValueError):
                    pass
                self.log(f"  [领金币] 第{i+1}次 +{sc} (累计 {gained})")
            else:
                self.log(f"  [领金币] 第{i+1}次领取失败: {g.get('message')}")
                break
        if gained:
            self.log(f"[领金币] 本轮共领 {gained} 金币")
        return gained

    def query_cash_task(self):
        r = self.http.http_post("/v18/task/readWithdraw.json", LEMON, "readWithdraw", self.p, {"type": "2"})
        items = (r.get("items") or {})
        lst = items.get("list") or []
        milestones = []
        for m in lst:
            try:
                val = int(m.get("value", 0))
            except (TypeError, ValueError):
                val = 0
            try:
                st = int(m.get("status", 0))
            except (TypeError, ValueError):
                st = 0
            milestones.append({"score": m.get("score"), "value": val, "status": st, "title": m.get("title", "")})
        if not milestones:
            return {"milestones": [], "claimable": [], "top_value": 0, "top_reached": False,
                    "all_done": False, "title": items.get("title", ""), "raw": r}
        top_value = max(m["value"] for m in milestones)
        top_reached = any(m["value"] == top_value and m["status"] != 0 for m in milestones)
        all_done = not any(m["status"] == 0 for m in milestones)
        claimable = [m for m in milestones if m["status"] == 1]
        return {"milestones": milestones, "claimable": claimable, "top_value": top_value,
                "top_reached": top_reached, "all_done": all_done, "title": items.get("title", "")}

    def get_userinfo(self):
        r = self.http.http_get("/v3/user/userinfo.json", LEMON, "userinfo", self.p)
        items = (r.get("items") or {})
        return {"nickname": items.get("nickname", ""),
                "treasury": _to_float(items.get("mini_balance")), "raw": r}

    def get_userdata(self):
        r = self.http.http_get("/v15/user/userdata.json", LEMON, "userdata", self.p)
        items = (r.get("items") or {})
        return {"treasury": _to_float(items.get("mini")), "raw": r}

    def get_cash_balance(self):
        try:
            d = self.get_userdata()
            if d["treasury"] is not None:
                return d["treasury"], None
        except Exception:
            pass
        try:
            u = self.get_userinfo()
            return u["treasury"], None
        except Exception:
            return None, None

    def withdraw_cash(self, amount_yuan, username):
        try:
            cents = int(round(float(amount_yuan) * 100))
        except (TypeError, ValueError):
            self.log(f"  [提现] 金额 {amount_yuan} 无效, 跳过")
            return False
        if cents <= 0:
            self.log(f"  [提现] 金额 {amount_yuan} 无效, 跳过")
            return False
        common = dict(DEVICE_DEFAULT)
        common.update(self.http._auth)
        common["request_time"] = str(int(time.time()))
        token = make_jwt({k: common[k] for k in common})
        business = {"score": str(cents), "type": "61", "username": username, "token": token}
        allp = dict(common)
        allp.update(business)
        zq = build_param(allp)
        url = LEMON + "/v17/UserRed/bonusWithdraw.json"
        data = ("zqkd_param=" + urllib.parse.quote(zq, safe="")).encode("utf-8")
        headers = {"User-Agent": UA, "device-platform": "android", "app-pkg": APP_PKG,
                   "Accept-Encoding": "gzip", "Content-Type": "application/x-www-form-urlencoded"}
        if self.http.session_cookie:
            headers["Cookie"] = f"PHPSESSID={self.http.session_cookie}"
        r = self.http.request("POST", url, data=data, headers=headers, timeout=30)
        if not r["success"]:
            self.log(f"  [提现] HTTP {r.get('http', 0)}")
            return False
        result = self.p.decrypt_resp(r["text"])
        items_r = (result.get("items") or {})
        if result.get("success") or result.get("error_code") in (0, "0"):
            self.log(f"  [提现] 成功: {amount_yuan}元 → 微信 (单号{items_r.get('order_id', '')})")
            self.stats["withdraw_amount"] += float(amount_yuan)
            self.stats["withdraw_ok"] = True
            self.stats["bonus_withdraw"] += float(amount_yuan)
            self.stats["bonus_withdraw_ok"] = True
            return True
        self.log(f"  [提现] 失败: {_brief(result)}")
        return False

    def get_red_payment_list(self):
        r = self.http.http_post("/v17/UserRed/getPaymentList.json", LEMON, "getPaymentList", self.p, {})
        if r.get("success") or r.get("error_code") in (0, "0"):
            return (r.get("items") or {})
        return {}

    def red_withdraw(self, amount_yuan):
        items = self.get_red_payment_list()
        bal = items.get("red")
        try:
            bal_f = float(bal)
        except (TypeError, ValueError):
            bal_f = None
        if bal_f is None:
            try:
                fallback_bal, _ = self.get_cash_balance()
                if fallback_bal is not None:
                    bal_f = fallback_bal
                    self.log(f"  [提现] getPaymentList未返回, 用小金库余额{fallback_bal}元兜底")
            except Exception:
                pass
        red_pay = items.get("red_payment") or []
        if bal is not None:
            self.log(f"\n[提现] 红包余额={bal}元, 目标提现={amount_yuan}元")
        else:
            self.log(f"\n[提现] 红包余额查询未返回, 目标提现={amount_yuan}元")
        TIERS = {0.3: ("40", "30"), 1.5: ("41", "150"), 10.0: ("42", "1000")}
        target = None
        for p in red_pay:
            try:
                if abs(float(p.get("money")) - float(amount_yuan)) < 1e-6:
                    target = p
                    break
            except (TypeError, ValueError):
                continue
        if not target:
            best = min(TIERS.keys(), key=lambda x: abs(x - float(amount_yuan)))
            if abs(best - float(amount_yuan)) < 1e-6:
                t, s = TIERS[best]
                target = {"type": t, "score": s, "money": best}
        if not target:
            self.log(f"  [提现] 未找到金额={amount_yuan}元的红包提现档位")
            return False
        typ = str(target.get("type"))
        score = str(target.get("score"))
        amt = target.get("money")
        if bal_f is not None and bal_f + 1e-9 < float(amt):
            self.log(f"  [提现] 红包余额不足 {bal_f}元 < {amt}元, 跳过")
            return False
        self.log(f"  [提现] 选档 type={typ}/score={score}")
        common = dict(DEVICE_DEFAULT)
        common.update(self.http._auth)
        common["request_time"] = str(int(time.time()))
        business = {"type": typ, "score": score, "username": self.username or ""}
        allp = dict(common)
        allp.update(business)
        token = make_jwt({k: allp[k] for k in allp})
        allp["token"] = token
        zq = build_param(allp)
        url = LEMON + "/v17/UserRed/redWithdraw.json"
        data = ("zqkd_param=" + urllib.parse.quote(zq, safe="")).encode("utf-8")
        headers = {"User-Agent": UA, "device-platform": "android", "app-pkg": APP_PKG,
                   "Accept-Encoding": "gzip", "Content-Type": "application/x-www-form-urlencoded"}
        if self.http.session_cookie:
            headers["Cookie"] = f"PHPSESSID={self.http.session_cookie}"
        r = self.http.request("POST", url, data=data, headers=headers, timeout=30)
        if not r["success"]:
            self.log(f"  [提现] HTTP {r.get('http', 0)}")
            return False
        result = self.p.decrypt_resp(r["text"])
        items_r = (result.get("items") or {})
        if result.get("success") or result.get("error_code") in (0, "0"):
            self.log(f"  [提现] 红包提现成功: {amt}元 → 微信 (单号{items_r.get('order_id', '')})")
            self.stats["withdraw_amount"] += float(amt)
            self.stats["withdraw_ok"] = True
            self.stats["red_withdraw"] += float(amt)
            self.stats["red_withdraw_ok"] = True
            return True
        self.log(f"  [提现] 红包提现失败: {_brief(result)}")
        return False

    def maybe_withdraw(self, task_ended=False):
        bal, _ = self.get_cash_balance()
        if bal is None:
            self.log("  [提现] 查不到余额, 跳过")
            return False
        if task_ended:
            if bal > 0.1:
                self.log(f"  [提现] 任务结束, 余额 {bal}元 > 0.1, 触发提现")
                return self.withdraw_cash(bal, self.username)
            self.log(f"  [提现] 任务结束, 余额 {bal}元 <= 0.1, 不提")
            return False
        if bal >= 0.8:
            self.log(f"  [提现] 余额 {bal}元 >= 0.8, 触发提现")
            return self.withdraw_cash(bal, self.username)
        self.log(f"  [提现] 余额 {bal}元 < 0.8, 暂不提(继续领)")
        return False

    def maybe_withdraw_target(self, target=WITHDRAW_TARGET):
        return self.red_withdraw(target)

    def claim_all_cash_stages(self):
        gained = 0.0
        attempts = 0
        MAX_ATTEMPTS = 60
        rate_keys = ("不要着急", "着急", "频繁", "太快", "过快", "稍后", "稍等", "稍候",
                     "请稍", "retry", "limit", "操作过快", "too frequent", "rate")
        while attempts < MAX_ATTEMPTS:
            attempts += 1
            info = self.query_cash_task()
            claimable = info.get("claimable") or []
            if not claimable:
                left = sum(1 for m in info["milestones"] if m["status"] == 0)
                self.log(f"  [领现金] 无可领阶段(待达成 {left} 个)")
                break
            me_tmpl = TASK_CONFIG.get("readWithdrawClaim", {}).get("media_extra_template", {})
            me = dict(me_tmpl)
            me["slot_price"] = random_slot_price()
            me["media_verify"] = ""
            media_extra = json.dumps(me, ensure_ascii=False, separators=(",", ":"))
            g = self.http.http_post("/v5/CommonReward/toGetReward.json", LEMON, "readWithdrawClaim", self.p,
                      {"media_extra": media_extra})
            g_items = (g.get("items") or {})
            sc = g_items.get("score")
            if g.get("success") or g.get("error_code") in (0, "0"):
                try:
                    amt = float(sc)
                except (TypeError, ValueError):
                    amt = 0.0
                gained += amt
                self.log(f"  [领现金] +{sc}元 (累计 {gained:.2f}元)")
                self.maybe_withdraw(task_ended=False)
                continue
            msg = str(g.get("message", ""))
            if any(k in msg for k in rate_keys):
                wait = random.uniform(15, 20)
                self.log(f"  [领现金] 随机等待 {wait:.0f}s")
                time.sleep(wait)
                continue
            self.log(f"  [领现金] 失败: {msg}")
            if "验证" in msg or "广告" in msg or "media" in msg.lower():
                self.log(f"  [领现金] 疑似需 media_verify, 纯脚本不可领该阶段, 停止本轮")
            break
        if gained:
            self.log(f"[领现金] 本轮共领 {gained:.2f} 元")
        self.stats["cash_gained"] = gained
        return gained

    def brush_until_stages_full(self, cap_minutes=DEFAULT_MINUTES):
        total = 12
        n = 0
        last_reachable = -1
        stable = 0
        try:
            cap_rounds = max(10, int(cap_minutes) * 60 // max(READTIME_SECONDS, 1)) if cap_minutes else 80
        except Exception:
            cap_rounds = 80
        self.log(f"[刷视频] 目标: 刷到12阶段全部可领/已领才停; 每{BRUSH_INTERVAL}s上报{READTIME_SECONDS}s (上限{cap_rounds}轮)")
        while n < cap_rounds:
            r = self.read_time_once()
            ok = r.get("success") or r.get("code") in (0, "0", 200) or "data" in r or "items" in r
            n += 1
            if n % 2 == 0 or not ok:
                info = self.query_cash_task()
                milestones = info.get("milestones") or []
                reachable = sum(1 for m in milestones if m["status"] in (1, 2))
                claim_n = len(info.get("claimable") or [])
                top = info.get("top_value", 0)
                self.log(f"  第{n}轮 | {_brief(r)} | 进度{reachable}/{total} 可领{claim_n}个 下阶段{top}s")
                if reachable >= total:
                    self.log(f"[刷视频] 12 阶段已全部可领/已领, 停止刷时长")
                    break
                if reachable == last_reachable:
                    stable += 1
                    if stable >= 3:
                        self.log(f"[刷视频] 进度已稳定于 {reachable} 阶段(疑似封顶), 转领取")
                        break
                else:
                    stable = 0
                    last_reachable = reachable
            else:
                self.log(f"  第{n}轮 {_brief(r)}")
            if not ok:
                self.log("  ⚠ 上报失败, 可能已过期")
            time.sleep(BRUSH_INTERVAL)
        self.log(f"[刷视频] 刷时长结束, 共上报 {n} 轮")

    def open_red_envelope(self):
        return self.http.http_post("/v18/task/openRedEnvelopeCash.json", LEMON, "openRedEnvelopeCash", self.p)

    def claim_red_envelope(self, index, media_extra):
        c = self.http.http_post("/v18/task/claimRedEnvelope.json", LEMON, "claimRedEnvelope", self.p,
                  {"index": str(index), "media_extra": media_extra})
        self.log(f"  [红包广告] 第{index}个 → {_brief(c)}")
        return c

    def _parse_red(self, r):
        if not isinstance(r, dict):
            return None
        items = r.get("items") or {}
        lst = items.get("list") or []
        out = []
        for m in lst:
            try:
                idx = int(m.get("index", 0))
            except (TypeError, ValueError):
                idx = 0
            try:
                st = int(m.get("status", 0))
            except (TypeError, ValueError):
                st = 0
            try:
                vid = int(m.get("video", 0))
            except (TypeError, ValueError):
                vid = 0
            out.append({"index": idx, "status": st, "money": _to_float(m.get("money")), "video": vid})
        return {"list": out, "money": _to_float(items.get("money")),
                "total_money": _to_float(items.get("total_money")),
                "next_time": _to_float(items.get("next_time"))}

    def _watch_one_ad_for_red(self):
        me_tmpl = TASK_CONFIG.get("toGetReward", {}).get("media_extra_template", {})
        me = dict(me_tmpl)
        me["slot_price"] = random_slot_price()
        me["media_verify"] = ""
        media_extra = json.dumps(me, ensure_ascii=False, separators=(",", ":"))
        g = self.http.http_post("/v5/CommonReward/toGetReward.json", LEMON, "toGetReward", self.p, {"media_extra": media_extra})
        if isinstance(g, dict) and str(g.get("error_code", "0")) != "0":
            self.log(f"  [红包广告] 广告奖励上报成功")
        return g

    def run_red_envelope(self):
        self.log("\n========== 开红包领现金任务 ==========")
        r = self.open_red_envelope()
        guard = 0
        MAX_GUARD = 50
        total_money = 0.0
        while guard < MAX_GUARD:
            guard += 1
            info = self._parse_red(r)
            if info is None or not info["list"]:
                self.log("[红包] 响应异常或无红包列表, 停止")
                break
            opened = [x for x in info["list"] if x["status"] == 2]
            pending = [x for x in info["list"] if x["status"] == 1]
            total_money = info.get("total_money") or 0.0
            self.log(f"[红包] 进度: 已开 {len(opened)}/{len(info['list'])} 待开 {len(pending)} 累计 {total_money}元 本次 {info.get('money')}元")
            if not pending:
                self.log("[红包] 全部红包已开完")
                break
            i = pending[0]
            idx, v = i["index"], i["video"]
            if v == 0:
                self.log(f"[红包] 第 {idx} 个无需看广告, 直接领取(claim 解锁)")
            else:
                self.log(f"[红包] 第 {idx} 个需看 {v} 个广告, 开始观看...")
                for k in range(v):
                    self._watch_one_ad_for_red()
                    time.sleep(random.uniform(3, 8))
            me_tmpl = TASK_CONFIG.get("claimRedEnvelope", {}).get("media_extra_template", {})
            me = dict(me_tmpl)
            me["slot_price"] = random_slot_price()
            me["media_verify"] = ""
            media_extra = json.dumps(me, ensure_ascii=False, separators=(",", ":"))
            self.claim_red_envelope(idx, media_extra)
            r = self.open_red_envelope()
            time.sleep(random.uniform(5, 12))
        self.red_withdraw(WITHDRAW_TARGET)
        self.log("[红包] 任务结束")
        self.stats["red_gained"] = total_money
        return total_money

    def keepalive_after_withdraw(self, duration=None, interval=None):
        dur = duration or KEEPALIVE_DURATION
        ivl = interval or KEEPALIVE_INTERVAL
        if dur <= 0:
            return
        try:
            before_bal, _ = self.get_cash_balance()
        except Exception:
            before_bal = None
        self.log(f"\n[保活] 提现后模拟app完整启动流程 (最长 {dur}s)...")
        end = time.time() + dur
        round_n = 0
        arrived = False
        while time.time() < end:
            round_n += 1
            try: self.config_info_once()
            except Exception: pass
            try: self.getinfo_once()
            except Exception: pass
            try: self.config_audit_once()
            except Exception: pass
            try: self.media_config_once()
            except Exception: pass
            try: self.config_did_once()
            except Exception: pass
            try: self.count_start_once()
            except Exception: pass
            time.sleep(random.uniform(1, 3))
            try: self.get_bonus_payment_list()
            except Exception: pass
            try: self.get_task_list()
            except Exception: pass
            try: self.machine_once()
            except Exception: pass
            try: self.read_score_once()
            except Exception: pass
            try: self.http.http_get("/v3/user/userinfo.json", LEMON, "userinfo", self.p)
            except Exception: pass
            try: self.app_update_once()
            except Exception: pass
            try: self.read_withdraw_once()
            except Exception: pass
            try: self.bi_collect_once()
            except Exception: pass
            time.sleep(random.uniform(2, 4))
            try:
                r = self.get_bonus_payment_list()
                self.log(f"  [保活] 第{round_n}轮 查提现列表 → {_brief(r)}")
            except Exception as e:
                self.log(f"  [保活] 第{round_n}轮 查提现列表异常: {e}")
            try:
                bal, _ = self.get_cash_balance()
                if bal is not None:
                    if before_bal is not None and bal < before_bal:
                        self.log(f"  [保活] 余额 {before_bal}→{bal}元, 已到账!")
                        arrived = True
                        break
                    self.log(f"  [保活] 余额 {bal}元 (提现前 {before_bal}元)")
            except Exception:
                pass
            remaining = max(0, int(end - time.time()))
            if remaining <= 0:
                break
            time.sleep(min(ivl, remaining))
        if arrived:
            self.log("[保活] 已到账, 保活结束")
        else:
            self.log(f"[保活] 等待{dur}秒超时, 保活结束")

    def run(self, minutes=DEFAULT_MINUTES, no_red=False):
        self.log(f"========== 开始执行任务 ==========")
        if self.proxy_mgr and self.proxy_mgr.current_proxy:
            self.log(f"已获取代理 | 出口IP: {self.proxy_mgr.proxy_ip}")
        else:
            self.log("直连执行 (无代理)")

        # 启动初始化
        try: self.config_info_once()
        except Exception: pass
        try: self.getinfo_once()
        except Exception: pass
        try: self.config_audit_once()
        except Exception: pass
        try: self.media_config_once()
        except Exception: pass
        try: self.config_did_once()
        except Exception: pass
        try: self.count_start_once()
        except Exception: pass
        try: self.bi_tf_once()
        except Exception: pass
        try: self.bi_collect_once()
        except Exception: pass

        nickname = ""
        try:
            ui = self.get_userinfo()
            self.username = ui.get("nickname") or ""
            nickname = self.username
            self.log(f"[信息] 微信昵称={self.username} 小金库余额={ui.get('treasury')}元")
        except Exception as ex:
            self.log(f"[警告] 取昵称失败: {ex}")

        try:
            self.machine_once()
        except Exception:
            pass

        # 主流程: 刷到12阶段填满 -> 领取
        last_claimed = -1
        last_reachable = -1
        stuck = 0
        for cycle in range(12):
            try:
                self.get_task_list()
            except Exception:
                pass
            try:
                self.machine_once()
            except Exception:
                pass
            try:
                self.ad_conversion_once()
            except Exception:
                pass
            try:
                self.exchange_once()
            except Exception:
                pass
            try:
                self.bi_collect_once()
            except Exception:
                pass

            self.brush_until_stages_full(minutes)
            self.log(f"\n[阶段2] 第{cycle+1}轮 领取阶段奖励...")
            self.claim_all_cash_stages()

            info = self.query_cash_task()
            claimed = sum(1 for m in info["milestones"] if m["status"] == 2)
            reachable = sum(1 for m in info["milestones"] if m["status"] in (1, 2))
            self.log(f"[进度] 第{cycle+1}轮: 已领={claimed}/12 当前可领={len(info['claimable'])} 可达={reachable}/12")
            if info.get("all_done") or claimed >= 12:
                self.log("[进度] 12 阶段全部领取完成")
                break
            if claimed == last_claimed and reachable == last_reachable:
                stuck += 1
                if stuck >= 2:
                    self.log("[进度] 连续无新增, 停止")
                    break
            else:
                stuck = 0
            last_claimed, last_reachable = claimed, reachable

        info = self.query_cash_task()
        claimed_final = sum(1 for m in info["milestones"] if m["status"] == 2)
        all_done = info.get("all_done") or claimed_final >= 12
        self.log(f"\n[阶段3] 任务结束判定: all_done={all_done} 已领={claimed_final}/12")
        self.maybe_withdraw(task_ended=all_done)

        if not no_red:
            try:
                self.run_red_envelope()
            except Exception as _e:
                self.log(f"[红包] 任务异常: {_e}")

        if self.stats["withdraw_ok"]:
            self.keepalive_after_withdraw()
        else:
            self.log("[info] 未发生提现, 跳过保活")

        self.log("[done] 账号任务结束")

        try:
            bal, _ = self.get_cash_balance()
            bal_str = f"{bal}元" if bal is not None else "未知"
        except Exception:
            bal_str = "未知"

        total_income = self.stats["cash_gained"] + self.stats["red_gained"]
        withdraw_info = f"提现: {self.stats['withdraw_amount']}元" if self.stats["withdraw_ok"] else "未提现"
        bonus_info = f"小金库提现: {self.stats['bonus_withdraw']}元" if self.stats["bonus_withdraw_ok"] else ""
        red_info = f"红包提现: {self.stats['red_withdraw']}元" if self.stats["red_withdraw_ok"] else ""
        withdraw_detail = " | ".join(filter(None, [withdraw_info, bonus_info, red_info]))

        return {
            "success": True,
            "nickname": nickname,
            "cash_gained": self.stats["cash_gained"],
            "red_gained": self.stats["red_gained"],
            "total_income": total_income,
            "withdraw_detail": withdraw_detail,
            "balance": bal_str,
            "logs": self.result_lines,
            "proxy_ip": self.proxy_mgr.proxy_ip if self.proxy_mgr else "-",
        }


# ============================================================
# 八、插件交互层
# ============================================================

def format_result(result: dict) -> str:
    nickname = result.get("nickname", "")
    name = f"〔{nickname}〕" if nickname else ""
    lines = [f"✅ {name}"]
    lines.append(f"   💰 刷视频现金 +{result['cash_gained']:.2f}元")
    lines.append(f"   🧧 红包收入 +{result['red_gained']:.2f}元")
    lines.append(f"   📊 今日总收益 +{result['total_income']:.2f}元")
    if result.get("withdraw_detail"):
        lines.append(f"   💸 {result['withdraw_detail']}")
    lines.append(f"   💳 小金库余额: {result['balance']}")
    proxy_ip = result.get("proxy_ip", "-")
    if proxy_ip and proxy_ip != "-":
        lines.append(f"   🌐 代理 {proxy_ip}")
    return "\n".join(lines)


def format_summary(results: list) -> str:
    total = len(results)
    success = sum(1 for r in results if r.get("success"))
    fail = total - success
    total_income = sum(r.get("total_income", 0) for r in results if r.get("success"))
    lines = [
        "📊 执行汇总",
        "────────────────────",
        f"📱 账号 {total} 个",
        f"✅ 成功 {success}",
        f"❌ 失败 {fail}",
        f"💰 总收益 +{total_income:.2f}元",
    ]
    fails = [r for r in results if not r.get("success")]
    if fails:
        lines.append("")
        lines.append("⚠️ 失败详情")
        for r in fails:
            lines.append(f"   {r.get('error', '未知')}")
    return "\n".join(lines)


def bind():
    sender.reply(
        "🎯 知了快看\n"
        "────────────────────\n"
        "📱 凭据支持三种模式:\n"
        "  1️⃣ UID直登: 只填纯数字UID\n"
        "  2️⃣ zqkd_param: 填抓包的整串参数\n"
        "  3️⃣ ZHILIAO键值对: uid=xxx#session=xxx#...\n"
        "────────────────────\n"
        "格式: 账号标识#凭据#UA(可选)\n"
        "示例1: 我的账号1#54475743\n"
        "示例2: 我的账号2#EsBz4arTkukU=...#UA\n"
        "示例3: 我的账号3#uid=54475743#session=xxx\n"
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
            "格式: 账号标识#凭据#UA(可选)"
        )
        return
    account = parts[0]
    cred = parts[1]
    ua = '#'.join(parts[2:]) if len(parts) >= 3 else ""
    cred_type = detect_cred_type(cred)
    if cred_type == "unknown":
        sender.reply(
            "❌ 凭据类型无法识别\n"
            "────────────────────\n"
            "请确保凭据为以下之一:\n"
            "  • 纯数字UID\n"
            "  • zqkd_param整串(长串base64风格)\n"
            "  • ZHILIAO键值对(uid=xxx#...)"
        )
        return
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
                "格式: 账号标识#凭据#UA"
            )
            return
    full_info = f"{account}#{cred}#{ua}"
    middleware.bucketSet(bucket='dd_ZhiLiao_login', key=account, value=full_info)
    set_account_owner(account, userid)
    accounts = parse_accounts(uservalue)
    if account in accounts:
        middleware.bucketSet(bucket='dd_ZhiLiao_bind', key=userid, value=json.dumps(accounts, ensure_ascii=False))
        sender.reply(f"✅ {mask_account(account)} 已更新")
    else:
        accounts.append(account)
        middleware.bucketSet(bucket='dd_ZhiLiao_bind', key=userid, value=json.dumps(accounts, ensure_ascii=False))
        sender.reply(
            "✅ 绑定成功\n"
            "────────────────────\n"
            f"📱 账号：{mask_account(account)}\n"
            f"🔑 凭据类型：{cred_type}\n"
            f"📊 共 {len(accounts)} 个账号"
        )
    register_user(userid)


def init_account(account: str, proxy_api: str = ""):
    """初始化账号，返回 (http, provider, proxy_mgr, cred_type, error_msg)"""
    login_info = middleware.bucketGet(bucket='dd_ZhiLiao_login', key=account)
    if not login_info:
        return None, None, None, None, "缺少登录信息"
    acc, cred, ua = parse_account_info(login_info)
    if not cred:
        return None, None, None, None, "缺少凭据"
    if not ua:
        ua = random.choice(BUILTIN_UAS)

    proxy_mgr = ProxyManager(proxy_api, account) if proxy_api else None
    if proxy_mgr:
        proxy_mgr.refresh()

    http = ZhiLiaoHTTP(proxy_mgr)
    provider = StaticProvider()
    cred_type = detect_cred_type(cred)

    try:
        if cred_type == "uid":
            apply_uid(cred, http)
        elif cred_type == "param":
            apply_param(cred, http)
        elif cred_type == "zhiliao":
            apply_zhiliao(cred, http)
        else:
            return None, None, None, None, f"未知凭据类型: {cred_type}"
    except Exception as e:
        return None, None, None, None, f"凭据解析失败: {e}"

    return http, provider, proxy_mgr, cred_type, ""


def execute_account(account: str, proxy_api: str = "", minutes=DEFAULT_MINUTES, no_red=False) -> dict:
    http, provider, proxy_mgr, cred_type, error = init_account(account, proxy_api)
    if error:
        return {"account": account, "success": False, "error": error, "logs": [], "proxy_ip": "-"}

    bot = Bot(http, provider, proxy_mgr)
    try:
        result = bot.run(minutes=minutes, no_red=no_red)
        result["account"] = account
        return result
    except Exception as e:
        return {"account": account, "success": False, "error": str(e), "logs": bot.result_lines if hasattr(bot, 'result_lines') else [], "proxy_ip": proxy_mgr.proxy_ip if proxy_mgr else "-"}


def query_account_status(account: str) -> dict:
    http, provider, proxy_mgr, cred_type, error = init_account(account, "")
    if error:
        return {"account": account, "success": False, "error": error, "nickname": "", "balance": "未知", "cash_status": "未知"}
    bot = Bot(http, provider, proxy_mgr)
    try:
        ui = bot.get_userinfo()
        nickname = ui.get("nickname", "")
        bal = ui.get("treasury")
        bal_str = f"{bal}元" if bal is not None else "未知"

        info = bot.query_cash_task()
        claimed = sum(1 for m in info["milestones"] if m["status"] == 2)
        total = len(info["milestones"])
        cash_status = f"已领{claimed}/{total}阶段"

        return {
            "account": account,
            "success": True,
            "nickname": nickname,
            "balance": bal_str,
            "cash_status": cash_status,
            "all_done": info.get("all_done", False),
        }
    except Exception as e:
        return {"account": account, "success": False, "error": str(e), "nickname": "", "balance": "未知", "cash_status": "未知"}


def format_query(result: dict) -> str:
    acc = mask_account(result["account"])
    if not result["success"]:
        return f"❌ {acc}\n   查询失败：{result.get('error', '未知')}"
    nickname = result.get("nickname", "")
    name = f"〔{nickname}〕" if nickname else ""
    icon = "✅" if result.get("all_done") else "⏳"
    lines = [f"{icon} {acc} {name}"]
    lines.append(f"   💳 小金库余额 {result['balance']}")
    lines.append(f"   💰 刷视频领现金 {result['cash_status']}")
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
        future_to_account = {executor.submit(query_account_status, acc): acc for acc in accounts}
        for future in as_completed(future_to_account):
            account = future_to_account[future]
            try:
                result = future.result()
            except Exception as e:
                result = {"account": account, "success": False, "error": str(e), "nickname": "", "balance": "未知", "cash_status": "未知"}
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


def execute_all(accounts: list, proxy_api: str, notify_owner: bool = True):
    if not accounts:
        sender.reply("未绑定任何账号")
        return []
    proxy_api = proxy_api or load_proxy_api()
    sender.reply(f"🚀 执行 {len(accounts)} 个账号...")
    results = []
    with ThreadPoolExecutor(max_workers=min(len(accounts), 3)) as executor:
        future_to_account = {
            executor.submit(execute_account, acc, proxy_api): acc
            for acc in accounts
        }
        for future in as_completed(future_to_account):
            account = future_to_account[future]
            try:
                result = future.result()
            except Exception as e:
                result = {"account": account, "success": False, "error": str(e), "logs": [], "proxy_ip": "-"}
            results.append(result)
            formatted = format_result(result) if result.get("success") else f"❌ {mask_account(account)}\n   失败：{result.get('error', '未知')}"
            owner_id = get_account_owner(account)
            if notify_owner and owner_id and owner_id != userid:
                try:
                    owner_sender = middleware.Sender(owner_id)
                    owner_sender.reply(formatted)
                except Exception:
                    sender.reply(f"{formatted}\n[CQ:at,qq={owner_id}]")
            else:
                sender.reply(formatted)
    summary = format_summary(results)
    sender.reply(summary)
    return results


def Administration():
    global uservalue
    base_message = (
        "🎯 知了快看\n"
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
                    middleware.bucketSet(bucket='dd_ZhiLiao_bind', key=userid, value=json.dumps(accounts, ensure_ascii=False))
                else:
                    middleware.bucketDel(bucket='dd_ZhiLiao_bind', key=userid)
                middleware.bucketDel(bucket='dd_ZhiLiao_login', key=selected)
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
        all_accounts = get_all_accounts_global()
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
    uservalue = middleware.bucketGet(bucket='dd_ZhiLiao_bind', key=userid)
    message = sender.getMessage()
    if message == "知了快看任务检测":
        accounts = parse_accounts(uservalue)
        sender.reply(
            "📊 任务状态\n"
            "────────────────────\n"
            f"📱 绑定：{len(accounts)} 个账号\n"
            f"📅 日期：{datetime.now().strftime('%Y-%m-%d')}\n"
            "⏰ 定时：每天 9:00"
        )
        return
    if message == "知了快看执行":
        accounts = parse_accounts(uservalue)
        if not accounts:
            sender.reply("未绑定任何账号")
            return
        execute_all(accounts, load_proxy_api())
        return
    if message == "知了运行":
        accounts = parse_accounts(uservalue)
        if not accounts:
            sender.reply("未绑定任何账号")
            return
        sender.reply(f"🚀 一键运行 {len(accounts)} 个账号...")
        execute_all(accounts, load_proxy_api())
        return
    Administration()


main()

import base64
import json
import random
import time
from typing import Any, Dict, Optional


class OrderedMap:
    def __init__(self) -> None:
        self.keys = []
        self.values = {}

    def add(self, key: str, value: Any) -> None:
        if key not in self.values:
            self.keys.append(key)
        self.values[key] = value


def _turnstile_to_str(value: Any) -> str:
    if value is None:
        return "undefined"
    if isinstance(value, float):
        return str(value)
    if isinstance(value, str):
        special = {
            "window.Math": "[object Math]",
            "window.Reflect": "[object Reflect]",
            "window.performance": "[object Performance]",
            "window.localStorage": "[object Storage]",
            "window.Object": "function Object() { [native code] }",
            "window.Reflect.set": "function set() { [native code] }",
            "window.performance.now": "function () { [native code] }",
            "window.Object.create": "function create() { [native code] }",
            "window.Object.keys": "function keys() { [native code] }",
            "window.Math.random": "function random() { [native code] }",
        }
        return special.get(value, value)
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return ",".join(value)
    return str(value)


def _xor_string(text: str, key: str) -> str:
    if not key:
        return text
    return "".join(chr(ord(ch) ^ ord(key[i % len(key)])) for i, ch in enumerate(text))


def solve_turnstile_token(dx: str, p: str) -> Optional[str]:
    try:
        decoded = base64.b64decode(dx).decode()
        token_list = json.loads(_xor_string(decoded, p))
    except Exception:
        return None

    process_map: Dict[Any, Any] = {}
    start_time = time.time()
    result = ""

    def func_1(e: float, t: float) -> None:
        process_map[e] = _xor_string(_turnstile_to_str(process_map[e]), _turnstile_to_str(process_map[t]))

    def func_2(e: float, t: Any) -> None:
        process_map[e] = t

    def func_3(e: str) -> None:
        nonlocal result
        result = base64.b64encode(e.encode()).decode()

    def func_5(e: float, t: float) -> None:
        current = process_map[e]
        incoming = process_map[t]
        if isinstance(current, (list, tuple)):
            process_map[e] = list(current) + [incoming]
            return
        if isinstance(current, (str, float)) or isinstance(incoming, (str, float)):
            process_map[e] = _turnstile_to_str(current) + _turnstile_to_str(incoming)
            return
        process_map[e] = "NaN"

    def func_6(e: float, t: float, n: float) -> None:
        tv = process_map[t]
        nv = process_map[n]
        if isinstance(tv, str) and isinstance(nv, str):
            value = f"{tv}.{nv}"
            process_map[e] = "https://chatgpt.com/" if value == "window.document.location" else value

    def func_7(e: float, *args: float) -> None:
        target = process_map[e]
        values = [process_map[arg] for arg in args]
        if isinstance(target, str) and target == "window.Reflect.set":
            obj, key_name, val = values
            obj.add(str(key_name), val)
        elif callable(target):
            target(*values)

    def func_8(e: float, t: float) -> None:
        process_map[e] = process_map[t]

    def func_11(e: float, t: float) -> None:
        process_map[e] = "https://chatgpt.com/backend-api/sentinel/sdk.js"

    def func_12(e: float) -> None:
        process_map[e] = process_map

    def func_13(e: float, t: float, *args: float) -> None:
        try:
            target = process_map.get(t)
            if callable(target):
                process_map[e] = target(*[process_map.get(a) for a in args])
        except Exception as err:
            process_map[e] = str(err)

    def func_14(e: float, t: float) -> None:
        process_map[e] = json.loads(process_map[t])

    def func_15(e: float, t: float) -> None:
        process_map[e] = json.dumps(process_map[t])

    def func_17(e: float, t: float, *args: float) -> None:
        call_args = [process_map[arg] for arg in args]
        target = process_map[t]
        if target == "window.performance.now":
            elapsed_ns = time.time_ns() - int(start_time * 1e9)
            process_map[e] = (elapsed_ns + random.random()) / 1e6
        elif target == "window.Object.create":
            process_map[e] = OrderedMap()
        elif target == "window.Object.keys":
            if call_args and call_args[0] == "window.localStorage":
                process_map[e] = [
                    "STATSIG_LOCAL_STORAGE_INTERNAL_STORE_V4",
                    "STATSIG_LOCAL_STORAGE_STABLE_ID",
                    "client-correlated-secret",
                    "oai/apps/capExpiresAt",
                    "oai-did",
                    "STATSIG_LOCAL_STORAGE_LOGGING_REQUEST",
                    "UiState.isNavigationCollapsed.1",
                ]
        elif target == "window.Math.random":
            process_map[e] = random.random()
        elif callable(target):
            process_map[e] = target(*call_args)

    def func_18(e: float) -> None:
        process_map[e] = base64.b64decode(_turnstile_to_str(process_map[e])).decode()

    def func_19(e: float) -> None:
        process_map[e] = base64.b64encode(_turnstile_to_str(process_map[e]).encode()).decode()

    def func_20(e: float, t: float, n: float, *args: float) -> None:
        if process_map[e] == process_map[t]:
            target = process_map[n]
            if callable(target):
                target(*[process_map[arg] for arg in args])

    def func_21(*_: Any) -> None:
        return

    def func_22(e: float, t: Any) -> None:
        try:
            sub_tokens = list(t) if isinstance(t, (list, tuple)) else []
            for sub in sub_tokens:
                s_op = sub[0]
                s_fn = process_map.get(s_op)
                if callable(s_fn):
                    s_fn(*sub[1:])
        except Exception as err:
            process_map[e] = str(err)

    def func_23(e: float, t: float, *args: float) -> None:
        if process_map.get(e) is not None and callable(process_map.get(t)):
            process_map[t](*args)

    def func_24(e: float, t: float, n: float) -> None:
        tv = process_map[t]
        nv = process_map[n]
        if isinstance(tv, str) and isinstance(nv, str):
            process_map[e] = f"{tv}.{nv}"

    def func_25(*_: Any) -> None:
        pass

    def func_26(*_: Any) -> None:
        pass

    def func_27(e: float, t: float) -> None:
        current = process_map.get(e)
        target = process_map.get(t)
        if isinstance(current, list):
            if target in current:
                current.remove(target)
        else:
            try:
                process_map[e] = float(current) - float(target)
            except Exception:
                process_map[e] = 0

    def func_28(*_: Any) -> None:
        pass

    def func_29(e: float, t: float, n: float) -> None:
        try:
            process_map[e] = bool(process_map.get(t) < process_map.get(n))
        except Exception:
            process_map[e] = False

    def func_30(e: float, t: float, n: Any, r: Any = None) -> None:
        has_params = isinstance(r, list)
        params = n if has_params else []
        body = (r if has_params else n) or []
        def generated_func(*args: Any) -> Any:
            if has_params:
                for idx, p_name in enumerate(params):
                    if idx < len(args):
                        process_map[p_name] = args[idx]
            for sub in (body if isinstance(body, list) else []):
                if isinstance(sub, list) and sub:
                    s_fn = process_map.get(sub[0])
                    if callable(s_fn):
                        s_fn(*sub[1:])
            return process_map.get(t)
        process_map[e] = generated_func

    def func_33(e: float, t: float, n: float) -> None:
        try:
            process_map[e] = float(process_map.get(t)) * float(process_map.get(n))
        except Exception:
            process_map[e] = 0

    def func_34(e: float, t: float) -> None:
        process_map[e] = process_map.get(t)

    def func_35(e: float, t: float, n: float) -> None:
        try:
            divisor = float(process_map.get(n))
            process_map[e] = float(process_map.get(t)) / divisor if divisor != 0 else 0
        except Exception:
            process_map[e] = 0

    process_map.update({
        1: func_1,
        2: func_2,
        3: func_3,
        5: func_5,
        6: func_6,
        7: func_7,
        8: func_8,
        9: token_list,
        10: "window",
        11: func_11,
        12: func_12,
        13: func_13,
        14: func_14,
        15: func_15,
        16: p,
        17: func_17,
        18: func_18,
        19: func_19,
        20: func_20,
        21: func_21,
        22: func_22,
        23: func_23,
        24: func_24,
        25: func_25,
        26: func_26,
        27: func_27,
        28: func_28,
        29: func_29,
        30: func_30,
        33: func_33,
        34: func_34,
        35: func_35,
    })

    for token in token_list:
        try:
            fn = process_map.get(token[0])
            if callable(fn):
                fn(*token[1:])
        except Exception:
            continue
    return result or None

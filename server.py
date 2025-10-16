from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import sys
from typing import Any, Callable, Iterable, Optional

HOST = "0.0.0.0"
PORT = 8000
DEFAULT_TZ = "America/Bogota"  

#  ESTRUCTURA: Lista Circular Doble

class _Node:
    __slots__ = ("value", "prev", "next")
    def __init__(self, value: Any):
        self.value = value
        self.prev: Optional[_Node] = None
        self.next: Optional[_Node] = None

class CircularDoublyLinkedList:

    def __init__(self, capacity: Optional[int] = None):
        if capacity is not None and capacity <= 0:
            raise ValueError("capacity debe ser > 0 o None")
        self.capacity = capacity
        self._head: Optional[_Node] = None
        self._len = 0

    def _link_between(self, left: _Node, right: _Node, node: _Node) -> None:
        left.next = node
        node.prev = left
        node.next = right
        right.prev = node

    def _insert_head_empty(self, node: _Node) -> None:
        node.next = node.prev = node
        self._head = node
        self._len = 1

    def _remove_node(self, node: _Node) -> Any:
        val = node.value
        if self._len == 1:  
            self._head = None
            self._len = 0
            return val
        node.prev.next = node.next
        node.next.prev = node.prev
        if node is self._head:
            self._head = node.next
        self._len -= 1
        return val

    def __len__(self) -> int:
        return self._len

    def is_empty(self) -> bool:
        return self._len == 0

    def head_value(self) -> Any:
        if not self._head:
            raise IndexError("lista vacía")
        return self._head.value

    def tail_value(self) -> Any:
        if not self._head:
            raise IndexError("lista vacía")
        return self._head.prev.value

    def append(self, value: Any) -> None:
        node = _Node(value)
        if self._head is None:
            self._insert_head_empty(node)
        else:
            tail = self._head.prev
            self._link_between(tail, self._head, node)
            self._len += 1
        if self.capacity is not None and self._len > self.capacity:
            self.popleft()

    def prepend(self, value: Any) -> None:
        node = _Node(value)
        if self._head is None:
            self._insert_head_empty(node)
        else:
            tail = self._head.prev
            self._link_between(tail, self._head, node)
            self._head = node  
            self._len += 1
        if self.capacity is not None and self._len > self.capacity:
            self.pop()

    def pop(self) -> Any:
        if not self._head:
            raise IndexError("pop de lista vacía")
        return self._remove_node(self._head.prev)

    def popleft(self) -> Any:
        if not self._head:
            raise IndexError("popleft de lista vacía")
        return self._remove_node(self._head)

    def clear(self) -> None:
        self._head = None
        self._len = 0

    def rotate(self, steps: int) -> None:
        if not self._head or self._len <= 1 or steps == 0:
            return
        steps = steps % self._len
        for _ in range(steps):
            self._head = self._head.prev  

    def find(self, pred: Callable[[Any], bool]) -> Optional[Any]:
        if not self._head:
            return None
        cur = self._head
        for _ in range(self._len):
            if pred(cur.value):
                return cur.value
            cur = cur.next
        return None

    def remove_value(self, value: Any, all_occurrences: bool = False) -> int:
        """Elimina la(s) primera(s) coincidencias de valor. Devuelve cuántos eliminó."""
        if not self._head:
            return 0
        removed = 0
        cur = self._head
        for _ in range(self._len):
            nxt = cur.next
            if cur.value == value:
                self._remove_node(cur)
                removed += 1
                if not all_occurrences:
                    break
            cur = nxt
            if self._len == 0:
                break
        return removed

    def __iter__(self) -> Iterable[Any]:
        if not self._head:
            return
        cur = self._head
        for _ in range(self._len):
            yield cur.value
            cur = cur.next

    def to_list(self, from_tail: bool = False) -> list:
        if not self._head:
            return []
        out = []
        if from_tail:
            cur = self._head.prev
            for _ in range(self._len):
                out.append(cur.value)
                cur = cur.prev
            return out
        else:
            cur = self._head
            for _ in range(self._len):
                out.append(cur.value)
                cur = cur.next
            return out

    def __repr__(self) -> str:
        return f"CDLL(len={self._len}, capacity={self.capacity}, values={self.to_list()})"

RECENT_TIME_PAYLOADS = CircularDoublyLinkedList(capacity=100)


def make_time_payload(tz: str, fmt: str):
    try:
        now = datetime.now(ZoneInfo(tz))
        tz_ok = True
        tz_used = tz
    except Exception:
        tz_ok = False
        tz_used = DEFAULT_TZ
        now = datetime.now(ZoneInfo(tz_used))

    hour24 = now.hour
    hour12 = hour24 % 12 or 12
    minute = now.minute
    second = now.second + now.microsecond / 1_000_000.0

    hour_angle = ((hour24 % 12) + minute / 60.0 + second / 3600.0) * 30.0
    minute_angle = (minute + second / 60.0) * 6.0
    second_angle = second * 6.0

    payload = {
        "timezone_requested": tz,
        "timezone_used": tz_used,
        "timezone_ok": tz_ok,
        "iso_time": now.isoformat(),
        "hour": hour12 if fmt == "12" else hour24,
        "hour_24": hour24,
        "hour_12": hour12,
        "minute": minute,
        "second": second,
        "angles": {
            "hour": hour_angle,
            "minute": minute_angle,
            "second": second_angle,
        },
        "format": fmt,
    }
    return payload


class Handler(BaseHTTPRequestHandler):
    def _write(self, status: int, payload: dict, content_type="application/json; charset=utf-8"):
        body = (json.dumps(payload)).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/health":
            self._write(200, {"ok": True, "status": "healthy"})
            return

        if parsed.path == "/api/time":
            qs = parse_qs(parsed.query or "")
            tz = (qs.get("tz", [DEFAULT_TZ])[0] or DEFAULT_TZ).strip()
            fmt = (qs.get("format", ["24"])[0] or "24").strip()
            if fmt not in ("12", "24"):
                fmt = "24"

            try:
                payload = make_time_payload(tz, fmt)
                RECENT_TIME_PAYLOADS.append({
                    "iso_time": payload["iso_time"],
                    "timezone_used": payload["timezone_used"],
                    "format": payload["format"],
                    "h": payload["hour"],
                    "m": payload["minute"],
                    "s": payload["second"],
                })
                self._write(200, payload)
            except Exception as e:
                self._write(500, {"error": "Internal Server Error", "detail": str(e)})
            return

        # --------- List (circular doble) ---------
        if parsed.path == "/api/list":
            qs = parse_qs(parsed.query or "")
            op = (qs.get("op", ["state"])[0] or "state").strip().lower()

            # operaciones simples:
            if op == "state":
                self._write(200, {
                    "len": len(RECENT_TIME_PAYLOADS),
                    "capacity": RECENT_TIME_PAYLOADS.capacity,
                    "items": RECENT_TIME_PAYLOADS.to_list(),
                })
                return

            if op == "append":
                val = qs.get("value", [None])[0]
                if val is None:
                    self._write(400, {"error": "Falta parámetro 'value'"})
                    return
                RECENT_TIME_PAYLOADS.append(val)
                self._write(200, {"ok": True, "len": len(RECENT_TIME_PAYLOADS)})
                return

            if op == "prepend":
                val = qs.get("value", [None])[0]
                if val is None:
                    self._write(400, {"error": "Falta parámetro 'value'"})
                    return
                RECENT_TIME_PAYLOADS.prepend(val)
                self._write(200, {"ok": True, "len": len(RECENT_TIME_PAYLOADS)})
                return

            if op == "pop":
                try:
                    v = RECENT_TIME_PAYLOADS.pop()
                    self._write(200, {"popped": v, "len": len(RECENT_TIME_PAYLOADS)})
                except IndexError as e:
                    self._write(400, {"error": str(e)})
                return

            if op == "popleft":
                try:
                    v = RECENT_TIME_PAYLOADS.popleft()
                    self._write(200, {"popleft": v, "len": len(RECENT_TIME_PAYLOADS)})
                except IndexError as e:
                    self._write(400, {"error": str(e)})
                return

            if op == "clear":
                RECENT_TIME_PAYLOADS.clear()
                self._write(200, {"ok": True, "len": len(RECENT_TIME_PAYLOADS)})
                return

            if op == "rotate":
                try:
                    steps = int(qs.get("steps", ["0"])[0])
                except ValueError:
                    self._write(400, {"error": "'steps' debe ser entero"})
                    return
                RECENT_TIME_PAYLOADS.rotate(steps)
                self._write(200, {"ok": True, "len": len(RECENT_TIME_PAYLOADS), "items": RECENT_TIME_PAYLOADS.to_list()})
                return

            if op == "remove":
                val = qs.get("value", [None])[0]
                if val is None:
                    self._write(400, {"error": "Falta parámetro 'value'"})
                    return
                all_occ = qs.get("all", ["0"])[0] in ("1", "true", "True")
                removed = RECENT_TIME_PAYLOADS.remove_value(val, all_occurrences=all_occ)
                self._write(200, {"removed": removed, "len": len(RECENT_TIME_PAYLOADS)})
                return

            self._write(400, {"error": "Operación no soportada", "op": op})
            return

        self._write(404, {"error": "Not Found", "path": parsed.path})


def run():
    print(f"Backend en http://{HOST}:{PORT}")
    print("   • /health")
    print("   • /api/time?tz=America/Bogota&format=24")
    print("   • /api/list?op=state | append | prepend | pop | popleft | clear | rotate&steps=K | remove&value=X&all=0/1")
    with HTTPServer((HOST, PORT), Handler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        print("Info: Windows: si obtienes error de zona horaria, instala la base de datos con:")
        print("    py -m pip install tzdata")
    try:
        run()
    except KeyboardInterrupt:
        print("\nServidor detenido.")

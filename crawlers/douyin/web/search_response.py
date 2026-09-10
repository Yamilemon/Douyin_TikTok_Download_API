"""Decode search responses without changing the shared crawler JSON parser."""
import json
import re


def parse_search_response(text: str, stream: bool = False, search_id: str = "") -> dict:
    text = text.lstrip("\ufeff").strip()
    decoder = json.JSONDecoder()
    chunks = []
    position = 0
    while position < len(text):
        start = text.find("{", position)
        prefix = text[position:start] if start >= 0 else text[position:]
        # Accept only the hex/whitespace separators observed in supplied captures.
        # HTTP transfer decoding itself is handled by httpx.
        if prefix.strip() and (not stream or not re.fullmatch(r"[0-9a-fA-F\s]+", prefix)):
            raise ValueError("无法识别搜索响应格式")
        if start < 0:
            if prefix.strip() not in ("", "0"):
                raise ValueError("搜索响应末尾不完整")
            break
        chunk, position = decoder.raw_decode(text, start)
        if not isinstance(chunk, dict):
            raise ValueError("搜索响应块不是对象")
        chunks.append(chunk)
        if not stream and text[position:].strip():
            raise ValueError("single 响应包含多个对象或多余内容")

    business = [c for c in chunks if "status_code" in c]
    if not business:
        raise ValueError("搜索响应没有业务数据")
    for chunk in business:
        if str(chunk["status_code"]) != "0":
            result = dict(chunk)
            if stream:
                result["stream_chunks"] = chunks
            return result
        if not isinstance(chunk.get("data"), list):
            raise ValueError("搜索响应缺少 data 列表")
    if stream and business[-1].get("result_status") != 4:
        raise ValueError("搜索流未收到完整结束块，不能推进游标")

    result = dict(business[-1])
    if stream:
        result["data"] = [item for chunk in business for item in chunk["data"]]
        result["stream_chunks"] = chunks
    # A later page's impr_id is a request log ID, not a replacement session ID.
    result["search_id"] = search_id if search_id and search_id != "0" else (
        (business[0].get("log_pb") or {}).get("impr_id")
        or (business[0].get("extra") or {}).get("logid") or "")
    return result

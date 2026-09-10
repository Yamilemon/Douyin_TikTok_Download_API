"""Search request defaults and browser fields derived from the configured UA."""
import json
import re
from urllib.parse import quote


def prepare_search_request(headers, keyword, offset, count, sort_type, publish_time,
                           filter_duration, search_id, need_filter_settings,
                           content_type, search_range):
    headers = dict(headers)
    ua = headers.get("User-Agent", "")
    cookies = dict(part.strip().split("=", 1) for part in headers.get("Cookie", "").split(";") if "=" in part)
    filters = {"sort_type": str(sort_type), "publish_time": str(publish_time),
               "content_type": str(content_type)}
    # Keep 0 as the previously supported 'unlimited' input.
    duration = "" if str(filter_duration) in ("", "0") else str(filter_duration)
    if duration not in ("", "0-1", "1-5", "5-10000"):
        raise ValueError("filter_duration 应为 0、空值、0-1、1-5 或 5-10000")
    if duration:
        filters["filter_duration"] = duration
    if search_range:
        filters["search_range"] = str(search_range)
    params = {
        "device_platform": "webapp", "aid": "6383", "channel": "channel_pc_web",
        "search_channel": "aweme_general", "enable_history": 1,
        "filter_selected": json.dumps(filters, ensure_ascii=False, separators=(",", ":")),
        "keyword": keyword, "search_source": "tab_search", "query_correct_type": 1,
        "is_filter_search": 1, "from_group_id": "", "disable_rs": 0,
        "offset": offset, "count": count,
        "need_filter_settings": (1 if offset == 0 else 0) if need_filter_settings is None else need_filter_settings,
        "list_type": "single", "pc_search_top_1_params": '{"enable_ai_search_top_1":1}',
        "update_version_code": "0" if offset == 0 else "170400",
        "pc_client_type": 1, "pc_libra_divert": "Windows",
        "support_h265": 1, "support_dash": 1, "cpu_core_num": 12,
        "version_code": "190600", "version_name": "19.6.0", "cookie_enabled": "true",
        "screen_width": 1920, "screen_height": 1080, "browser_language": "zh-CN",
        "browser_online": "true", "device_memory": 16, "platform": "PC",
        "downlink": "10", "effective_type": "4g", "round_trip_time": "50",
    }
    headers.update({"Accept": "application/json, text/plain, */*",
                    "Referer": f"https://www.douyin.com/search/{quote(keyword, safe='')}?type=general",
                    "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "same-origin"})
    chrome = re.search(r"Chrome/([\d.]+)", ua)
    firefox = re.search(r"Firefox/([\d.]+)", ua)
    edge = re.search(r"Edg/([\d.]+)", ua)
    if chrome:
        name, version = ("Edge", edge[1]) if edge else ("Chrome", chrome[1])
        params.update(browser_name=name, browser_version=version,
                      engine_name="Blink", engine_version=chrome[1])
        brand = "Microsoft Edge" if edge else "Google Chrome"
        headers["sec-ch-ua"] = f'"Chromium";v="{chrome[1].split(".")[0]}", "{brand}";v="{version.split(".")[0]}"'
        headers["sec-ch-ua-mobile"] = "?0"
    elif firefox:
        params.update(browser_name="Firefox", browser_version=firefox[1],
                      engine_name="Gecko", engine_version=firefox[1])
    if "Windows" in ua:
        params.update(browser_platform="Win32", os_name="Windows", os_version="10")
        platform = "Windows"
    elif "Macintosh" in ua:
        params.update(browser_platform="MacIntel", os_name="Mac OS")
        platform = "macOS"
    else:
        params.update(browser_platform="Linux x86_64", os_name="Linux")
        platform = "Linux"
    params["pc_libra_divert"] = platform
    if chrome:
        headers["sec-ch-ua-platform"] = f'"{platform}"'
    if search_id and search_id != "0":
        params["search_id"] = search_id
    if cookies.get("UIFID"):
        params["uifid"] = cookies["UIFID"]
        headers["uifid"] = cookies["UIFID"]
    if cookies.get("s_v_web_id"):
        params.update(fp=cookies["s_v_web_id"], verifyFp=cookies["s_v_web_id"])
    return headers, params, cookies

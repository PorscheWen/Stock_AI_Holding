#!/usr/bin/env python3
"""
LINE Rich Menu 部署：3×2 六格，以 URI 開啟 PWA 不同錨點（切換畫面）。

環境變數：
  LINE_CHANNEL_ACCESS_TOKEN（或 CHANNEL_ACCESS_TOKEN）
  APP_URL — 完整 PWA 入口，例如 https://your-domain.com/app

執行：python setup_rich_menu.py
"""
from __future__ import annotations

import io
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

# Windows 主控台常為 cp950，避免 emoji 在 print 時觸發 UnicodeEncodeError
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN") or os.getenv("CHANNEL_ACCESS_TOKEN", "")
APP_URL = (os.getenv("APP_URL", "") or "").strip().rstrip("/")

API = "https://api.line.me/v2/bot"
# 上傳選單圖必須使用 data API（用 api.line.me 會回 404）
API_DATA = "https://api-data.line.me/v2/bot"


def _headers_json():
    return {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def _headers_binary(ct: str):
    return {"Authorization": f"Bearer {TOKEN}", "Content-Type": ct}


def pwa_base() -> str:
    if not APP_URL:
        sys.exit("❌ 請設定 APP_URL，例如 https://xxx.onrender.com/app")
    if APP_URL.endswith("/app"):
        return APP_URL
    return APP_URL + "/app"


def menu_cells():
    """每格：(emoji, 中文標題, PWA URI)。emoji 僅用於選單圖，不影響點擊區域。"""
    b = pwa_base()
    return [
        ("🏠", "首頁", f"{b}#home"),
        ("📈", "持股", f"{b}#holdings"),
        ("📷", "截圖", f"{b}#screenshot"),
        ("⚙️", "設定", f"{b}#settings"),
        ("💡", "說明", f"{b}#help"),
        ("🔙", "回首頁", f"{b}#home"),
    ]


def build_areas():
    W, H = 2500, 1686
    cw = W // 3
    ch_top = H // 2
    ch_bot = H - ch_top
    cells = menu_cells()
    areas = []
    idx = 0
    for row in range(2):
        y = 0 if row == 0 else ch_top
        height = ch_top if row == 0 else ch_bot
        for col in range(3):
            x = col * cw if col < 2 else 2 * cw
            width = cw if col < 2 else (W - 2 * cw)
            _em, _title, uri = cells[idx]
            idx += 1
            areas.append(
                {
                    "bounds": {"x": x, "y": y, "width": width, "height": height},
                    "action": {"type": "uri", "uri": uri},
                }
            )
    return areas


def draw_menu_jpeg() -> bytes:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        sys.exit("❌ 請 pip install Pillow")

    # 相對原本 52 / 28 約三倍
    TITLE_SZ = 52 * 3
    SUB_SZ = 28 * 3
    EMOJI_SZ = int(52 * 2.9)

    W, H = 2500, 1686
    cw = W // 3
    ch_top = H // 2
    ch_bot = H - ch_top
    # 無深色底色：白底、不畫格線／填色區塊
    img = Image.new("RGB", (W, H), "#FFFFFF")
    draw = ImageDraw.Draw(img)

    def font_text(sz: int):
        for path in (
            "C:/Windows/Fonts/msjhbd.ttc",
            "C:/Windows/Fonts/msjh.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ):
            try:
                return ImageFont.truetype(path, sz)
            except OSError:
                continue
        return ImageFont.load_default()

    def font_emoji(sz: int):
        for path in (
            "C:/Windows/Fonts/seguiemj.ttf",
            "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
            "/System/Library/Fonts/Supplemental/Apple Color Emoji.ttc",
        ):
            try:
                return ImageFont.truetype(path, sz)
            except OSError:
                continue
        return ImageFont.load_default()

    f_lg = font_text(TITLE_SZ)
    f_sm = font_text(SUB_SZ)
    f_em = font_emoji(EMOJI_SZ)

    cells = menu_cells()
    idx = 0
    for row in range(2):
        y0 = 0 if row == 0 else ch_top
        h = ch_top if row == 0 else ch_bot
        for col in range(3):
            x0 = col * cw if col < 2 else 2 * cw
            w = cw if col < 2 else (W - 2 * cw)
            emoji_ch, label, _uri = cells[idx]
            idx += 1
            cx = x0 + w // 2
            cy = y0 + h // 2
            em_y = cy - int(h * 0.22)
            title_y = cy + int(h * 0.06)
            sub_y = cy + int(h * 0.26)

            try:
                draw.text(
                    (cx, em_y),
                    emoji_ch,
                    font=f_em,
                    anchor="mm",
                    embedded_color=True,
                )
            except TypeError:
                draw.text((cx, em_y), emoji_ch, font=f_em, anchor="mm", fill="#222222")

            draw.text((cx, title_y), label, fill="#111111", font=f_lg, anchor="mm")
            draw.text(
                (cx, sub_y),
                "Stock Holding",
                fill="#555555",
                font=f_sm,
                anchor="mm",
            )

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return buf.getvalue()


def delete_all_richmenus():
    r = requests.get(f"{API}/richmenu/list", headers=_headers_json(), timeout=30)
    r.raise_for_status()
    for item in r.json().get("richmenus", []):
        rid = item["richMenuId"]
        requests.delete(f"{API}/richmenu/{rid}", headers=_headers_json(), timeout=30)
        print(f"  🗑  刪除舊選單 {rid}")


def main():
    if not TOKEN:
        sys.exit("❌ 請設定 LINE_CHANNEL_ACCESS_TOKEN（或 CHANNEL_ACCESS_TOKEN）")

    print("\n[1/4] 清除既有 Rich Menu…")
    try:
        delete_all_richmenus()
    except requests.HTTPError as e:
        print(f"  （清除時）{e}")

    body = {
        "size": {"width": 2500, "height": 1686},
        "selected": True,
        "name": "StockHoldingPWA",
        "chatBarText": "持股選單",
        "areas": build_areas(),
    }

    print("\n[2/4] 建立 Rich Menu…")
    r = requests.post(f"{API}/richmenu", headers=_headers_json(), json=body, timeout=30)
    if not r.ok:
        sys.exit(f"❌ 建立失敗 {r.status_code}: {r.text}")
    rid = r.json()["richMenuId"]
    print(f"  ✅ richMenuId = {rid}")

    print("\n[3/4] 上傳選單圖…")
    jpeg = draw_menu_jpeg()
    os.makedirs("static", exist_ok=True)
    with open("static/rich_menu_preview.jpg", "wb") as f:
        f.write(jpeg)
    print("  💾 預覽 static/rich_menu_preview.jpg")

    r2 = requests.post(
        f"{API_DATA}/richmenu/{rid}/content",
        headers=_headers_binary("image/jpeg"),
        data=jpeg,
        timeout=60,
    )
    if not r2.ok:
        sys.exit(f"❌ 上傳圖片失敗 {r2.status_code}: {r2.text}")

    print("\n[4/4] 設為預設選單…")
    r3 = requests.post(
        f"{API}/user/all/richmenu/{rid}",
        headers=_headers_json(),
        timeout=30,
    )
    if not r3.ok:
        sys.exit(f"❌ 設定預設失敗 {r3.status_code}: {r3.text}")

    print("\n🎉 完成。請用手機開啟官方帳號查看底部選單。\n")


if __name__ == "__main__":
    main()

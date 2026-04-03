"""
OCR 识别与金额日期提取服务。

此模块提供了 OCR 识别功能，并从文本中提取金额和日期。
"""

from __future__ import annotations

import io
import re
from datetime import date
from functools import lru_cache
from typing import Any

import numpy as np
from PIL import Image

from ..core.constants import EXPENSE_CATEGORIES, INCOME_CATEGORIES

# 正则表达式用于匹配金额和日期
_AMOUNT_RE = re.compile(r"(?<!\d)(\d+(?:\.\d{1,2})?)(?!\d)")
_DATE_RE = re.compile(r"(20\d{2})[\-/年\.](\d{1,2})[\-/月\.](\d{1,2})")

# 定义关键词字典
_INCOME_KEYWORDS = {
    "工资": "工资",
    "薪资": "工资",
    "奖金": "奖金",
    "报销": "其他收入",
    "转入": "其他收入",
    "收款": "其他收入",
    "利息": "理财收益",
    "收益": "理财收益",
    "红包": "红包",
}

# 定义关键词字典
_EXPENSE_KEYWORDS = {
    "餐": "餐饮",
    "外卖": "餐饮",
    "滴滴": "交通",
    "地铁": "交通",
    "公交": "交通",
    "加油": "交通",
    "超市": "购物",
    "淘宝": "购物",
    "京东": "购物",
    "拼多多": "购物",
    "便利店": "日用",
    "房租": "房租",
    "物业": "水电煤",
    "电费": "水电煤",
    "水费": "水电煤",
    "燃气": "水电煤",
    "话费": "通讯",
    "电影": "娱乐",
    "游戏": "娱乐",
    "医院": "医疗",
    "药": "医疗",
    "培训": "教育",
    "机票": "旅行",
    "酒店": "旅行",
}

# 用于过滤掉这些无关金额的文本行
_IGNORE_LINE_WORDS = {"小计", "合计", "总计", "订单号", "交易单号", "流水号"}


# 从识别结果中提取交易记录的相关信息，包括交易类型、分类、金额、日期和备注等
@lru_cache(maxsize=1)
def _get_ocr_engine():
    # 使用 LRU 缓存装饰器缓存 OCR 引擎实例，避免重复创建，提高性能
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


# 提取日期
def _extract_date(raw_text: str) -> date:
    """
    从文本中提取日期。

    Args:
        raw_text (str): 原始文本。

    Returns:
        date: 提取的日期。
    """
    match = _DATE_RE.search(raw_text)
    if not match:
        return date.today()
    year, month, day = [int(x) for x in match.groups()]
    try:
        return date(year, month, day)
    except ValueError:
        return date.today()


# 提取金额
def _pick_amount(text: str) -> float | None:
    matches = _AMOUNT_RE.findall(text)
    if not matches:
        return None

    numbers = [float(item) for item in matches]
    valid = [x for x in numbers if 0 < x < 1_000_000]
    if not valid:
        return None
    return valid[-1]


# 根据文本内容推断交易类型和分类
def _infer_type_and_category(text: str) -> tuple[str, str]:
    lowered = text.lower()

    for keyword, category in _INCOME_KEYWORDS.items():
        if keyword in lowered:
            return "income", category

    for keyword, category in _EXPENSE_KEYWORDS.items():
        if keyword in lowered:
            return "expense", category

    if any(k in lowered for k in ("收入", "入账", "到账", "转入")):
        return "income", "其他收入"

    return "expense", "其他支出"


# 清理备注文本
def _clean_note(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:200]


# 判断文本行是否可以忽略
def _is_ignorable_line(text: str) -> bool:
    if len(text.strip()) < 2:
        return True
    return any(word in text for word in _IGNORE_LINE_WORDS)


# 主函数：运行 OCR 识别并提取交易信息
def run_ocr(image_bytes: bytes) -> dict[str, Any]:
    # 将字节流转换为 PIL 图像对象，并确保图像是 RGB 模式
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image_np = np.array(image)

    # 获取 OCR 引擎实例，并运行 OCR 识别，获取识别结果
    ocr_engine = _get_ocr_engine()
    result, _ = ocr_engine(image_np)

    # 从 OCR 识别结果中提取文本行，并从中提取金额、日期、交易类型、分类和备注等信息，构建候选交易记录列表
    lines: list[str] = []
    if result:
        for item in result:
            text = item[1] if len(item) > 1 else ""
            if text:
                lines.append(str(text))

    # 将提取的文本行连接成原始文本，并从中提取日期
    raw_text = "\n".join(lines)
    txn_date = _extract_date(raw_text)

    # 遍历文本行，过滤掉无关行，并从中提取金额、交易类型、分类和备注等信息，构建候选交易记录列表，去重后返回最终结果
    candidates = []
    seen = set()
    for line in lines:
        if _is_ignorable_line(line):
            continue

        amount = _pick_amount(line)
        if amount is None:
            continue

        # 根据文本内容推断交易类型和分类，并清理备注信息，构建一个唯一键用于去重，如果该键已经存在于 seen 集合中，则跳过，否则添加到 seen 集合中，并将提取的信息添加到候选交易记录列表中
        txn_type, category = _infer_type_and_category(line)
        note = _clean_note(line)
        key = (txn_type, category, amount, note)
        if key in seen:
            continue
        seen.add(key)

        candidates.append(
            {
                "selected": True,
                "type": txn_type,
                "category": category,
                "amount": amount,
                "note": note,
                "txn_date": txn_date,
            }
        )

    return {
        "raw_text": raw_text,
        "items": candidates[:50],
        "categories": {
            "income": INCOME_CATEGORIES,
            "expense": EXPENSE_CATEGORIES,
        },
    }

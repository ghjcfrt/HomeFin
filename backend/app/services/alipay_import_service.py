from __future__ import annotations

import csv
import hashlib
from datetime import datetime
from typing import Any

from ..core.constants import EXPENSE_CATEGORIES, INCOME_CATEGORIES
from .import_common import ImportValidationError, make_issue

ALIPAY_GUIDE_URL = "https://b.alipay.com/page/mbillexprod/account/detail"

REQUIRED_HEADERS_DISPLAY = [
    "入账时间",
    "支付宝交易号",
    "支付宝流水号",
    "收入（+元）",
    "支出（-元）",
]


def _normalize_header(value: str) -> str:
    table = str.maketrans({"（": "(", "）": ")", "＋": "+", "－": "-", " ": ""})
    return value.strip().translate(table)


def _decode_csv(content: bytes) -> str:
    for encoding in ("gb2312", "gb18030", "gbk", "utf-8-sig", "utf-8"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ImportValidationError(
        code="ALIPAY_ENCODING_UNSUPPORTED",
        message="CSV 编码无法识别，请确认使用支付宝导出的 GB2312/GBK/GB18030/UTF-8 CSV",
        field="file",
    )


def _parse_amount(raw: str) -> float:
    value = (raw or "").strip().replace(",", "")
    if not value:
        return 0.0
    return float(value)


def _parse_txn_date(raw: str):
    value = (raw or "").strip()
    if not value:
        raise ValueError("入账时间为空")
    for fmt, slice_len in (("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%d", 10)):
        try:
            return datetime.strptime(value[:slice_len], fmt).date()
        except ValueError:
            continue
    raise ValueError(f"无法解析入账时间: {raw}")


def _infer_category(txn_type: str, text: str) -> str:
    lowered = text.lower()

    income_rules = {
        "工资": ["工资", "薪", "salary"],
        "奖金": ["奖金", "bonus"],
        "红包": ["红包"],
        "理财收益": ["收益", "分红", "利息", "理财"],
    }
    expense_rules = {
        "餐饮": ["餐", "奶茶", "咖啡", "外卖", "美团", "饿了么"],
        "交通": ["地铁", "公交", "滴滴", "打车", "高铁", "机票"],
        "购物": ["淘宝", "天猫", "京东", "拼多多", "闲鱼", "超市", "商城"],
        "日用": ["纸巾", "洗衣", "清洁", "日用"],
        "水电煤": ["电费", "水费", "燃气", "煤气"],
        "通讯": ["话费", "流量", "宽带", "通信"],
        "娱乐": ["电影", "游戏", "会员", "娱乐", "音乐"],
        "医疗": ["医院", "药", "诊所", "医疗", "医保"],
        "教育": ["学费", "培训", "课程", "教育"],
        "旅行": ["酒店", "住宿", "旅行", "旅游"],
        "房租": ["房租", "租金", "物业"],
    }

    rules = income_rules if txn_type == "income" else expense_rules
    default_category = "其他收入" if txn_type == "income" else "其他支出"
    valid_categories = INCOME_CATEGORIES if txn_type == "income" else EXPENSE_CATEGORIES

    for category, keywords in rules.items():
        if any(keyword in lowered for keyword in keywords):
            return category if category in valid_categories else default_category

    return default_category


def parse_alipay_csv(
    content: bytes,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    decoded = _decode_csv(content)
    issues: list[dict[str, Any]] = []
    filtered_lines = []
    for line in decoded.splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("#"):
            continue
        filtered_lines.append(line)

    if not filtered_lines:
        raise ImportValidationError(
            code="IMPORT_EMPTY_FILE",
            message="CSV 内容为空或不包含账单数据",
            field="file",
        )

    reader = csv.reader(filtered_lines)
    rows = list(reader)
    if not rows:
        raise ImportValidationError(
            code="ALIPAY_CSV_PARSE_FAILED",
            message="CSV 内容无法解析",
            field="file",
        )

    raw_headers = rows[0]
    header_map = {_normalize_header(name): idx for idx, name in enumerate(raw_headers)}

    required_headers = [_normalize_header(name) for name in REQUIRED_HEADERS_DISPLAY]
    missing = [
        REQUIRED_HEADERS_DISPLAY[idx]
        for idx, normalized_name in enumerate(required_headers)
        if normalized_name not in header_map
    ]
    if missing:
        raise ImportValidationError(
            code="ALIPAY_MISSING_HEADERS",
            message=f"缺少必须表头: {', '.join(missing)}",
            field="headers",
        )

    optional_aliases = {
        "账务类型": ["账务类型"],
        "对方名称": ["对方名称"],
        "商品名称": ["商品名称"],
        "业务描述": ["业务描述"],
        "备注": ["备注"],
        "付款备注": ["付款备注"],
        "商户订单号": ["商户订单号"],
    }

    def get_value(row: list[str], header: str) -> str:
        idx = header_map.get(_normalize_header(header))
        if idx is None or idx >= len(row):
            return ""
        return (row[idx] or "").strip()

    def get_optional(row: list[str], key: str) -> str:
        for alias in optional_aliases[key]:
            idx = header_map.get(_normalize_header(alias))
            if idx is not None and idx < len(row):
                return (row[idx] or "").strip()
        return ""

    results: list[dict[str, Any]] = []
    for row_idx, row in enumerate(rows[1:], start=2):
        if not row:
            continue
        try:
            income = _parse_amount(get_value(row, "收入（+元）"))
            expense = _parse_amount(get_value(row, "支出（-元）"))

            if income <= 0 and expense <= 0:
                issues.append(
                    make_issue(
                        code="ALIPAY_ROW_SKIPPED_NO_AMOUNT",
                        message="收入和支出均为空或不大于 0，已跳过",
                        row=row_idx,
                        field="amount",
                    )
                )
                continue

            txn_type = "income" if income > 0 else "expense"
            amount = income if txn_type == "income" else expense
            txn_date = _parse_txn_date(get_value(row, "入账时间"))
            trade_no = get_value(row, "支付宝交易号")
            flow_no = get_value(row, "支付宝流水号")

            biz_type = get_optional(row, "账务类型")
            counterparty = get_optional(row, "对方名称")
            product_name = get_optional(row, "商品名称")
            biz_desc = get_optional(row, "业务描述")
            memo = get_optional(row, "备注")
            pay_memo = get_optional(row, "付款备注")
            merchant_order = get_optional(row, "商户订单号")

            note_parts = [
                part
                for part in [
                    biz_type,
                    counterparty,
                    product_name,
                    biz_desc,
                    memo,
                    pay_memo,
                ]
                if part
            ]
            note = " | ".join(note_parts)[:200] if note_parts else None

            category_text = " ".join(note_parts)
            category = _infer_category(txn_type, category_text)

            import_source = "alipay_csv"
            fingerprint = "|".join(
                [
                    import_source,
                    trade_no,
                    flow_no,
                    merchant_order,
                    str(txn_date),
                    f"{amount:.2f}",
                    txn_type,
                ]
            )
            import_key = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()

            results.append(
                {
                    "selected": True,
                    "type": txn_type,
                    "category": category,
                    "amount": amount,
                    "txn_date": txn_date,
                    "note": note,
                    "external_id": trade_no or flow_no or import_key[:12],
                    "source": import_source,
                    "import_key": import_key,
                }
            )
        except ValueError as exc:
            issues.append(
                make_issue(
                    code="ALIPAY_ROW_PARSE_FAILED",
                    message=f"第 {row_idx} 行解析失败: {exc}",
                    severity="error",
                    row=row_idx,
                )
            )

    if not results:
        issues.append(
            make_issue(
                code="ALIPAY_NO_VALID_ROWS",
                message="未解析到可导入记录",
                severity="error",
            )
        )

    return results, issues

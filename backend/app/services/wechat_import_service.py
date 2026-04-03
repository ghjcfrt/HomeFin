"""
微信账单导入解析服务。

此模块提供了解析微信账单 XLSX 文件的功能，包括解析金额、日期和分类。
"""

from __future__ import annotations

import hashlib
import io
import re
import zipfile
from datetime import datetime, timedelta
from typing import Any
from xml.etree import ElementTree as ET

from ..core.constants import EXPENSE_CATEGORIES, INCOME_CATEGORIES
from .import_common import ImportValidationError, make_issue

# 微信账单 XLSX 文件中必须包含的表头，规范化后用于匹配和解析
REQUIRED_HEADERS_DISPLAY = [
    "交易时间",  # 交易发生时间
    "交易类型",  # 交易类型（如转账、消费等）
    "交易对方",  # 交易对方名称
    "商品",  # 商品名称
    "收/支",  # 收入或支出
    "金额(元)",  # 金额
    "支付方式",  # 支付方式
    "当前状态",  # 当前交易状态
    "交易单号",  # 微信交易单号
    "商户单号",  # 商户订单号
    "备注",  # 备注信息
]


# 定义 XLSX 相关 XML 命名空间
_XML_NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


# 规范化 XLSX 表头，去除空格和中英文括号差异
def _normalize_header(value: str) -> str:
    """
    规范化 XLSX 表头。

    Args:
        value (str): 原始表头字符串。

    Returns:
        str: 规范化后的表头字符串。
    """
    table = str.maketrans({"（": "(", "）": ")", " ": ""})
    return str(value or "").strip().translate(table)


# 转换为列索引（1 开始）
def _column_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch.upper()) - 64)
    return idx


# 解析 XLSX 的 sharedStrings.xml，返回所有字符串值列表
def _parse_shared_strings(book_zip: zipfile.ZipFile) -> list[str]:
    shared_strings_path = "xl/sharedStrings.xml"
    if shared_strings_path not in book_zip.namelist():
        return []

    root = ET.fromstring(book_zip.read(shared_strings_path))
    values: list[str] = []
    for si in root.findall("m:si", _XML_NS):
        texts = [t.text or "" for t in si.findall(".//m:t", _XML_NS)]
        values.append("".join(texts))
    return values


# 解析 workbook.xml，获取第一个工作表的路径
def _resolve_first_sheet_path(book_zip: zipfile.ZipFile) -> str:
    workbook = ET.fromstring(book_zip.read("xl/workbook.xml"))
    first_sheet = workbook.find("m:sheets/m:sheet", _XML_NS)
    if first_sheet is None:
        raise ImportValidationError(
            code="WECHAT_XLSX_NO_SHEET",
            message="XLSX 缺少工作表",
            field="file",
        )

    rel_id = first_sheet.attrib.get(
        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    )
    if not rel_id:
        raise ImportValidationError(
            code="WECHAT_XLSX_BAD_RELATION",
            message="XLSX 工作表引用损坏",
            field="file",
        )

    rels = ET.fromstring(book_zip.read("xl/_rels/workbook.xml.rels"))
    target = None
    for rel in rels:
        if rel.attrib.get("Id") == rel_id:
            target = rel.attrib.get("Target")
            break
    if not target:
        raise ImportValidationError(
            code="WECHAT_XLSX_RELATION_MISSING",
            message="XLSX 工作表关系缺失",
            field="file",
        )

    # 返回工作表文件的路径，确保路径以 xl/ 开头
    if target.startswith("/"):
        return target.lstrip("/")
    if target.startswith("xl/"):
        return target
    return f"xl/{target}"


# 提取 XLSX 文件中第一个工作表的所有行数据，返回二维字符串列表
def _extract_rows(content: bytes) -> list[list[str]]:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as book_zip:
            sheet_path = _resolve_first_sheet_path(book_zip)
            shared_strings = _parse_shared_strings(book_zip)
            sheet_root = ET.fromstring(book_zip.read(sheet_path))
    except zipfile.BadZipFile as exc:
        raise ImportValidationError(
            code="WECHAT_XLSX_INVALID_FILE",
            message="文件不是有效的 XLSX 格式",
            field="file",
        ) from exc
    except KeyError as exc:
        raise ImportValidationError(
            code="WECHAT_XLSX_INCOMPLETE",
            message="XLSX 内容不完整，无法解析",
            field="file",
        ) from exc

    rows: list[list[str]] = []
    for row in sheet_root.findall(".//m:sheetData/m:row", _XML_NS):
        # 提取每个单元格的值，构建一个以列索引为键、单元格值为值的字典
        cells: dict[int, str] = {}
        max_idx = 0
        for cell in row.findall("m:c", _XML_NS):
            ref = cell.attrib.get("r", "")
            idx = _column_index(ref) if ref else 0
            if idx <= 0:
                continue

            cell_type = cell.attrib.get("t")
            value_node = cell.find("m:v", _XML_NS)
            inline_node = cell.find("m:is", _XML_NS)

            value = ""
            if cell_type == "s" and value_node is not None:
                try:
                    value = shared_strings[int(value_node.text or "0")]
                except (ValueError, IndexError):
                    value = ""
            elif cell_type == "inlineStr" and inline_node is not None:
                value = "".join(
                    [txt.text or "" for txt in inline_node.findall(".//m:t", _XML_NS)]
                )
            elif value_node is not None and value_node.text is not None:
                value = value_node.text

            cells[idx] = value.strip()
            if idx > max_idx:
                max_idx = idx

        if not cells:
            rows.append([])
            continue

        # 构造完整行，缺失的列补空字符串
        line = ["" for _ in range(max_idx)]
        for idx, value in cells.items():
            line[idx - 1] = value
        rows.append(line)

    return rows


# 解析金额字符串，去除千分位分隔符，转为 float
def _parse_amount(raw: str) -> float:
    value = str(raw or "").strip().replace(",", "")
    if not value:
        return 0.0
    return float(value)


# 解析交易时间字符串，支持多种格式和 Excel 序列号
def _parse_txn_date(raw: str):
    value = str(raw or "").strip()
    if not value:
        raise ValueError("交易时间为空")

    # Excel 日期序列号
    if re.fullmatch(r"\d+(\.\d+)?", value):
        serial = float(value)
        base = datetime(1899, 12, 30)
        return (base + timedelta(days=serial)).date()

    # 常见日期格式
    for fmt, size in (
        ("%Y-%m-%d %H:%M:%S", 19),
        ("%Y-%m-%d %H:%M", 16),
        ("%Y-%m-%d", 10),
        ("%Y/%m/%d %H:%M:%S", 19),
        ("%Y/%m/%d", 10),
    ):
        try:
            return datetime.strptime(value[:size], fmt).date()
        except ValueError:
            continue
    raise ValueError(f"无法解析交易时间: {raw}")


# 根据交易类型和文本内容智能推断分类
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
        "购物": ["淘宝", "天猫", "京东", "拼多多", "闲鱼", "超市", "商城", "罗森"],
        "日用": ["纸巾", "洗衣", "清洁", "日用", "打印"],
        "水电煤": ["电费", "水费", "燃气", "煤气"],
        "通讯": ["话费", "流量", "宽带", "通信"],
        "娱乐": ["电影", "游戏", "会员", "娱乐", "音乐"],
        "医疗": ["医院", "药", "诊所", "医疗", "医保"],
        "教育": ["学费", "培训", "课程", "教育", "考试费"],
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


# 解析微信账单 XLSX 文件主入口，返回解析结果和问题列表
def parse_wechat_xlsx(
    content: bytes,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = _extract_rows(content)
    issues: list[dict[str, Any]] = []
    if not rows:
        raise ImportValidationError(
            code="IMPORT_EMPTY_FILE",
            message="XLSX 内容为空",
            field="file",
        )

    required_headers = [
        _normalize_header(header) for header in REQUIRED_HEADERS_DISPLAY
    ]
    header_index = -1
    header_map: dict[str, int] = {}

    # 查找表头行及其索引映射
    for idx, row in enumerate(rows):
        normalized = [_normalize_header(cell) for cell in row]
        if all(name in normalized for name in required_headers):
            header_index = idx
            header_map = {name: normalized.index(name) for name in required_headers}
            break

    if header_index < 0:
        raise ImportValidationError(
            code="WECHAT_MISSING_HEADERS",
            message="未找到微信账单固定表头，请确认使用微信导出的 XLSX 文件",
            field="headers",
        )

    results: list[dict[str, Any]] = []
    for row_idx, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
        # 跳过空行
        if not row or all(not str(cell or "").strip() for cell in row):
            continue

        def get_value(name: str) -> str:
            pos = header_map[name]
            if pos >= len(row):
                return ""
            return str(row[pos] or "").strip()

        try:
            status = get_value(_normalize_header("当前状态"))
            # 只导入支付成功/已收款的记录
            if status and status not in {"支付成功", "已收款"}:
                issues.append(
                    make_issue(
                        code="WECHAT_ROW_SKIPPED_STATUS",
                        message=f"交易状态为 {status}，已跳过",
                        row=row_idx,
                        field="当前状态",
                    )
                )
                continue

            inout = get_value(_normalize_header("收/支"))
            if inout not in {"收入", "支出"}:
                issues.append(
                    make_issue(
                        code="WECHAT_ROW_SKIPPED_INOUT",
                        message="收/支 字段非法，已跳过",
                        row=row_idx,
                        field="收/支",
                    )
                )
                continue

            amount = _parse_amount(get_value(_normalize_header("金额(元)")))
            if amount <= 0:
                issues.append(
                    make_issue(
                        code="WECHAT_ROW_SKIPPED_NO_AMOUNT",
                        message="金额不大于 0，已跳过",
                        row=row_idx,
                        field="金额(元)",
                    )
                )
                continue

            txn_type = "income" if inout == "收入" else "expense"
            txn_date = _parse_txn_date(get_value(_normalize_header("交易时间")))
            txn_scene = get_value(_normalize_header("交易类型"))
            counterparty = get_value(_normalize_header("交易对方"))
            product = get_value(_normalize_header("商品"))
            pay_method = get_value(_normalize_header("支付方式"))
            trade_no = get_value(_normalize_header("交易单号"))
            merchant_no = get_value(_normalize_header("商户单号"))
            memo = get_value(_normalize_header("备注"))

            # 组合备注信息
            note_parts = [
                part
                for part in [txn_scene, counterparty, product, pay_method, status, memo]
                if part and part != "/"
            ]
            note = " | ".join(note_parts)[:200] if note_parts else None

            # 分类推断
            category_text = " ".join([txn_scene, counterparty, product, memo])
            category = _infer_category(txn_type, category_text)

            import_source = "wechat_xlsx"
            fingerprint = "|".join(
                [
                    import_source,
                    trade_no,
                    merchant_no,
                    str(txn_date),
                    f"{amount:.2f}",
                    txn_type,
                    counterparty,
                    product,
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
                    "external_id": trade_no or merchant_no or import_key[:12],
                    "source": import_source,
                    "import_key": import_key,
                }
            )
        except ValueError as exc:
            issues.append(
                make_issue(
                    code="WECHAT_ROW_PARSE_FAILED",
                    message=f"第 {row_idx} 行解析失败: {exc}",
                    severity="error",
                    row=row_idx,
                )
            )

    if not results:
        issues.append(
            make_issue(
                code="WECHAT_NO_VALID_ROWS",
                message="未解析到可导入记录",
                severity="error",
            )
        )

    return results, issues

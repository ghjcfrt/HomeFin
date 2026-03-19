# 家庭财务小管家

一个轻量、可本地运行的家庭记账项目，支持手工录入、OCR 图片导入、支付宝 CSV 导入、微信 XLSX 导入，并提供分类统计和月度趋势图。

## 项目特性

- 前后端分离，部署和调试简单
- 支持收入/支出分类管理与可视化
- 支持单笔录入 + 批量导入
- 导入支持幂等去重，重复文件可安全重试

## 技术栈

- 后端：FastAPI + SQLAlchemy + SQLite
- 前端：原生 HTML/CSS/JavaScript + Chart.js
- OCR：rapidocr-onnxruntime + Pillow + NumPy

## 目录结构

```text
.
├─backend/
│  ├─requirements.txt
│  └─app/
│     ├─main.py
│     ├─schemas.py
│     ├─core/
│     │  └─constants.py
│     ├─db/
│     │  ├─database.py
│     │  ├─models.py
│     │  └─crud.py
│     └─services/
│        ├─ocr_service.py
│        ├─alipay_import_service.py
│        └─wechat_import_service.py
├─frontend/
│  ├─index.html
│  ├─styles.css
│  └─app.js
└─start_all.bat
```

## 环境要求

- 操作系统：Windows（已提供一键脚本）
- Python：建议 3.10+
- 包管理：推荐使用 uv（未安装也可使用 pip）

## 快速启动

### 方式一：手动启动

1. 在项目根目录创建并激活虚拟环境

```bash
uv venv
.venv\Scripts\activate
```

2. 安装后端依赖

```bash
uv pip install -r backend/requirements.txt
```

3. 启动后端

```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. 新开一个终端，启动前端静态服务

```bash
cd frontend
python -m http.server 5500
```

5. 访问地址

- 前端页面：http://localhost:5500
- 后端接口文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

### 方式二：一键启动（Windows）

在项目根目录执行：

```bash
start_all.bat
```

说明：

- 脚本会优先使用项目根目录虚拟环境 .venv
- 若 .venv 不存在会自动创建
- 会自动安装依赖并打开两个终端窗口（后端 + 前端）
- 关闭这两个终端窗口即可停止服务

## 核心功能

- 新增收支记录：类型、分类、金额、日期、备注
- 记录列表：查看、刷新、删除
- 图表统计：
  - 支出分类占比（环图）
  - 月度收支趋势（柱状图）
- OCR 导入：识别票据图片并生成候选记录，可编辑后批量导入
- 支付宝 CSV 导入：解析账务明细并按唯一键去重
- 微信 XLSX 导入：解析微信账单并按唯一键去重

## 导入功能说明

### OCR 图片导入

- 接口：POST /ocr/preview
- 仅支持图片文件（image/*）
- 流程：上传图片 -> 识别候选记录 -> 前端勾选与编辑 -> 批量导入
- 批量入库接口：POST /transactions/batch

### 支付宝 CSV 导入

- 预览接口：POST /imports/alipay/preview
- 导入接口：POST /imports/alipay
- 支持编码：GB2312 / GB18030 / GBK / UTF-8-SIG / UTF-8
- 必须表头：
  - 入账时间
  - 支付宝交易号
  - 支付宝流水号
  - 收入（+元）
  - 支出（-元）
- 可重复导入同一份文件，系统会自动跳过重复记录
- 官方导出入口（页面文案可能会变）：
  - https://b.alipay.com/page/mbillexprod/account/detail

### 微信 XLSX 导入

- 预览接口：POST /imports/wechat/preview
- 导入接口：POST /imports/wechat
- 仅支持 XLSX（不支持 CSV）
- 仅导入状态为“支付成功”或“已收款”的记录
- 固定表头：
  - 交易时间
  - 交易类型
  - 交易对方
  - 商品
  - 收/支
  - 金额(元)
  - 支付方式
  - 当前状态
  - 交易单号
  - 商户单号
  - 备注
- 手机微信导出参考路径：
  - 我 -> 服务 -> 钱包 -> 账单 -> 下载账单 -> 用于个人对账 -> 选择区间 -> 导出 XLSX

## 幂等与去重机制

- 数据库层建立唯一索引：(source, import_key)
- 支付宝来源 source：alipay_csv
- 微信来源 source：wechat_xlsx
- 重复导入时返回：inserted（新增条数）与 skipped（跳过条数）

## 数据库说明

- 默认数据库为 SQLite
- 实际文件位置：项目根目录 homefin.db
- 不是 backend/homefin.db

如果需要重置数据，停止后端后删除根目录 homefin.db，再重新启动服务即可自动建表。

## 主要接口一览

- GET /health
- GET /categories
- GET /transactions
- POST /transactions
- POST /transactions/batch
- DELETE /transactions/{txn_id}
- GET /stats/category/{txn_type}
- GET /stats/monthly
- POST /ocr/preview
- POST /imports/alipay/preview
- POST /imports/alipay
- POST /imports/wechat/preview
- POST /imports/wechat

完整请求/响应示例请查看 Swagger 文档：http://localhost:8000/docs

## 接口请求示例

以下示例默认后端地址为：http://localhost:8000

### 1. 健康检查

```bash
curl http://localhost:8000/health
```

### 2. 获取分类

```bash
curl http://localhost:8000/categories
```

### 3. 新增一条记录

```bash
curl -X POST http://localhost:8000/transactions \
	-H "Content-Type: application/json" \
	-d '{
		"type": "expense",
		"category": "餐饮",
		"amount": 35.8,
		"txn_date": "2026-03-19",
		"note": "午饭"
	}'
```

### 4. 批量新增（OCR 导入最终调用）

```bash
curl -X POST http://localhost:8000/transactions/batch \
	-H "Content-Type: application/json" \
	-d '{
		"items": [
			{
				"type": "expense",
				"category": "餐饮",
				"amount": 18.5,
				"txn_date": "2026-03-19",
				"note": "早餐"
			},
			{
				"type": "income",
				"category": "工资",
				"amount": 12000,
				"txn_date": "2026-03-10",
				"note": "3 月工资"
			}
		]
	}'
```

### 5. 查询记录

```bash
curl http://localhost:8000/transactions
```

### 6. 删除记录

```bash
curl -X DELETE http://localhost:8000/transactions/1
```

### 7. 获取支出分类统计

```bash
curl http://localhost:8000/stats/category/expense
```

### 8. 获取月度统计

```bash
curl http://localhost:8000/stats/monthly
```

### 9. OCR 预览（上传图片）

```bash
curl -X POST http://localhost:8000/ocr/preview \
	-F "file=@D:/data/receipt.jpg"
```

### 10. 支付宝 CSV 预览（上传 CSV）

```bash
curl -X POST http://localhost:8000/imports/alipay/preview \
	-F "file=@D:/data/alipay.csv"
```

### 11. 支付宝导入（幂等）

```bash
curl -X POST http://localhost:8000/imports/alipay \
	-H "Content-Type: application/json" \
	-d '{
		"items": [
			{
				"selected": true,
				"type": "expense",
				"category": "购物",
				"amount": 99.9,
				"txn_date": "2026-03-18",
				"note": "淘宝 | 日用品",
				"external_id": "202603180001",
				"source": "alipay_csv",
				"import_key": "f0f4c0c6e2b63133231786d6a5bf1537b9b89e7c4f80c2af7b20f45392b5c8f1"
			}
		]
	}'
```

### 12. 微信 XLSX 预览（上传 XLSX）

```bash
curl -X POST http://localhost:8000/imports/wechat/preview \
	-F "file=@D:/data/wechat.xlsx"
```

### 13. 微信导入（幂等）

```bash
curl -X POST http://localhost:8000/imports/wechat \
	-H "Content-Type: application/json" \
	-d '{
		"items": [
			{
				"selected": true,
				"type": "expense",
				"category": "交通",
				"amount": 12,
				"txn_date": "2026-03-18",
				"note": "地铁",
				"external_id": "1000000000001",
				"source": "wechat_xlsx",
				"import_key": "16e9a3a22f7b4769d0d6c0f2ca17f6e08f510a45b5aef8291f2e420a8408339c"
			}
		]
	}'
```

### 说明

- Windows PowerShell 中可直接使用以上 curl（系统通常会映射为 Invoke-WebRequest）。
- 为了更稳定地调试 JSON 接口，推荐安装 curl.exe 或使用 Postman / Apifox。
- 实际导入建议先调用 preview 接口拿到候选 items，再原样提交到 import 接口，避免字段不一致。

## 常见问题

### 1. 前端页面能打开，但数据加载失败

- 检查后端是否已启动：http://localhost:8000/health
- 检查前端 API 地址是否为 http://localhost:8000（frontend/app.js 中 API_BASE）

### 2. 导入文件后显示 0 条记录

- 支付宝：确认已包含必须表头，且金额列有正数
- 微信：确认是官方导出的 XLSX，且“当前状态”为“支付成功”或“已收款”

### 3. 重复导入时为什么有 skipped

- 这是预期行为，表示命中去重规则，系统已自动跳过重复数据

## 后续方向

- 支持多账户/多成员
- 增加预算与超支提醒
- 增加按周统计、同比环比
- 增加数据导出（CSV/Excel）

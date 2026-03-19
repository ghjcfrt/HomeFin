# 家庭财务小管家

前后端分离的小型项目：
- 后端（Python/FastAPI）：收支记录、分类统计、月度统计 API
- 前端（HTML/CSS/JS）：录入数据、列表展示、图表展示

## 目录结构

- `backend/` Python 后端
- `frontend/` 前端页面

## 1) 启动后端

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 2) 启动前端

新开一个终端：

```bash
cd frontend
python -m http.server 5500
```

浏览器访问：
- 前端页面：`http://localhost:5500`
- 后端文档：`http://localhost:8000/docs`

## 3) 一键启动（Windows）

项目根目录提供了 `start_all.bat`，双击即可启动前后端（会打开两个终端窗口）。

脚本固定使用项目根目录虚拟环境 `homefin/.venv`，不会使用 `backend/.venv`：

```bash
start_all.bat
```

停止服务：关闭两个新打开的终端窗口即可。

## 功能说明

- 新增收支记录（收入/支出、分类、金额、日期、备注）
- 记录列表与删除
- 分类统计（饼图）
- 月度收支趋势（柱状图）

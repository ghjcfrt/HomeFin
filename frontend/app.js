const API_BASE = "http://localhost:8000";
const CHART_JS_SRC = "https://cdn.jsdelivr.net/npm/chart.js";

const form = document.getElementById("txn-form");
const txnList = document.getElementById("txn-list");
const refreshBtn = document.getElementById("refresh-btn");
const categorySelect = form.elements.category;
const typeSelect = form.elements.type;
const submitBtn = document.getElementById("submit-btn");
const cancelEditBtn = document.getElementById("cancel-edit-btn");
const formModeTip = document.getElementById("form-mode-tip");

const filterDateFrom = document.getElementById("filter-date-from");
const filterDateTo = document.getElementById("filter-date-to");
const filterType = document.getElementById("filter-type");
const filterCategory = document.getElementById("filter-category");
const filterAmountMin = document.getElementById("filter-amount-min");
const filterAmountMax = document.getElementById("filter-amount-max");
const filterKeyword = document.getElementById("filter-keyword");
const sortBy = document.getElementById("sort-by");
const sortOrder = document.getElementById("sort-order");
const filterToggleBtn = document.getElementById("filter-toggle-btn");
const filterCloseBtn = document.getElementById("filter-close-btn");
const filterPopup = document.getElementById("filter-popup");
const filterApplyBtn = document.getElementById("filter-apply-btn");
const filterResetBtn = document.getElementById("filter-reset-btn");

const expenseChartHint = document.getElementById("expense-chart-hint");
const monthlyChartHint = document.getElementById("monthly-chart-hint");

const budgetMonthInput = document.getElementById("budget-month");
const budgetTotalInput = document.getElementById("budget-total");
const budgetCategorySelect = document.getElementById("budget-category");
const budgetCategoryAmountInput = document.getElementById("budget-category-amount");
const budgetSaveBtn = document.getElementById("budget-save-btn");
const budgetAddCategoryBtn = document.getElementById("budget-add-category-btn");
const budgetRefreshBtn = document.getElementById("budget-refresh-btn");
const budgetStatus = document.getElementById("budget-status");
const budgetOverview = document.getElementById("budget-overview");
const budgetList = document.getElementById("budget-list");

const backupExportBtn = document.getElementById("backup-export-btn");
const backupFileInput = document.getElementById("backup-file");
const backupRestoreBtn = document.getElementById("backup-restore-btn");
const backupStatus = document.getElementById("backup-status");

const ocrFileInput = document.getElementById("ocr-file");
const ocrBtn = document.getElementById("ocr-btn");
const ocrImportBtn = document.getElementById("ocr-import-btn");
const ocrStatus = document.getElementById("ocr-status");
const ocrList = document.getElementById("ocr-list");

const alipayFileInput = document.getElementById("alipay-file");
const alipayPreviewBtn = document.getElementById("alipay-preview-btn");
const alipayImportBtn = document.getElementById("alipay-import-btn");
const alipayStatus = document.getElementById("alipay-status");
const alipayList = document.getElementById("alipay-list");

const wechatFileInput = document.getElementById("wechat-file");
const wechatPreviewBtn = document.getElementById("wechat-preview-btn");
const wechatImportBtn = document.getElementById("wechat-import-btn");
const wechatStatus = document.getElementById("wechat-status");
const wechatList = document.getElementById("wechat-list");

let expenseChart;
let monthlyChart;
let categoryOptions = { income: [], expense: [] };
let ocrCandidates = [];
let alipayCandidates = [];
let wechatCandidates = [];
let editingTxnId = null;
let budgetDraftCategoryMap = {};
let chartLibraryLoading = null;

function loadChartLibrary() {
  if (typeof window.Chart === "function") {
    return Promise.resolve();
  }
  if (chartLibraryLoading) {
    return chartLibraryLoading;
  }

  chartLibraryLoading = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = CHART_JS_SRC;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("图表库加载失败"));
    document.head.appendChild(script);
  });

  return chartLibraryLoading;
}

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const isFormData = options.body instanceof FormData;
  if (!isFormData && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const resp = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!resp.ok) {
    let message = `请求失败 (${resp.status})`;
    try {
      const data = await resp.json();
      if (typeof data?.detail === "string") {
        message = data.detail;
      } else if (data?.detail?.message) {
        const code = data.detail.code ? `[${data.detail.code}] ` : "";
        message = `${code}${data.detail.message}`;
      }
    } catch {
      const text = await resp.text();
      if (text) message = text;
    }
    throw new Error(message);
  }

  if (resp.status === 204) return null;
  return resp.json();
}

function formatCurrency(value, type) {
  const symbol = type === "income" ? "+" : "-";
  return `${symbol}￥${Number(value).toFixed(2)}`;
}

function getCurrentDate() {
  return new Date().toISOString().slice(0, 10);
}

function getCurrentMonth() {
  return new Date().toISOString().slice(0, 7);
}

function buildQuery(params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    query.append(key, String(value));
  });
  const qs = query.toString();
  return qs ? `?${qs}` : "";
}

function getCategoryOptionsByType(txnType) {
  return txnType === "income" ? categoryOptions.income : categoryOptions.expense;
}

function fillCategorySelect(selectEl, txnType, selectedCategory) {
  const options = getCategoryOptionsByType(txnType);
  const fallback = txnType === "income" ? "其他收入" : "其他支出";
  const finalCategory = selectedCategory || options[0] || fallback;

  selectEl.innerHTML = "";
  options.forEach((category) => {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    selectEl.appendChild(option);
  });

  if (!options.includes(finalCategory)) {
    const customOption = document.createElement("option");
    customOption.value = finalCategory;
    customOption.textContent = `${finalCategory}（自定义）`;
    selectEl.appendChild(customOption);
  }

  selectEl.value = finalCategory;
}

function fillFilterCategorySelect() {
  const all = [...categoryOptions.expense, ...categoryOptions.income];
  const unique = [...new Set(all)];
  filterCategory.innerHTML = '<option value="">全部</option>';
  unique.forEach((category) => {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    filterCategory.appendChild(option);
  });
}

function fillBudgetCategorySelect() {
  budgetCategorySelect.innerHTML = "";
  categoryOptions.expense.forEach((category) => {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    budgetCategorySelect.appendChild(option);
  });
}

function enterEditMode(item) {
  editingTxnId = item.id;
  formModeTip.textContent = `当前为编辑模式：ID ${item.id}`;
  submitBtn.textContent = "保存修改";
  cancelEditBtn.style.display = "inline-block";

  typeSelect.value = item.type;
  fillCategorySelect(categorySelect, item.type, item.category);
  form.elements.amount.value = Number(item.amount).toFixed(2);
  form.elements.txn_date.value = item.txn_date;
  form.elements.note.value = item.note || "";
}

function exitEditMode() {
  editingTxnId = null;
  formModeTip.textContent = "当前为新增模式";
  submitBtn.textContent = "保存记录";
  cancelEditBtn.style.display = "none";

  const currentType = typeSelect.value || "expense";
  form.reset();
  typeSelect.value = currentType;
  fillCategorySelect(categorySelect, currentType, null);
  form.elements.txn_date.value = getCurrentDate();
}

function renderList(items) {
  txnList.innerHTML = "";

  if (!items.length) {
    txnList.innerHTML = "<p>暂无符合条件的记录。</p>";
    return;
  }

  for (const item of items) {
    const card = document.createElement("div");
    card.className = "txn-item";
    card.innerHTML = `
      <span class="badge ${item.type}">${item.type === "income" ? "收入" : "支出"}</span>
      <div>
        <strong>${item.category}</strong>
        <div>${item.note || "无备注"}</div>
        <small>${item.txn_date}</small>
      </div>
      <div class="amount">${formatCurrency(item.amount, item.type)}</div>
      <div class="actions">
        <button data-action="edit" data-id="${item.id}">编辑</button>
        <button data-action="delete" data-id="${item.id}">删除</button>
      </div>
    `;
    txnList.appendChild(card);
  }

  txnList.querySelectorAll("button[data-action]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = Number(btn.dataset.id);
      const action = btn.dataset.action;
      if (action === "edit") {
        const item = items.find((x) => x.id === id);
        if (item) enterEditMode(item);
        return;
      }

      if (!confirm("确认删除这条记录吗？")) return;
      await request(`/transactions/${id}`, { method: "DELETE" });
      await refreshAll();
    });
  });
}

function prepareCanvas(canvas, preferredHeight = 280) {
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(320, Math.floor(rect.width || canvas.parentElement?.clientWidth || 420));
  const height = preferredHeight;
  const dpr = window.devicePixelRatio || 1;

  canvas.width = Math.floor(width * dpr);
  canvas.height = Math.floor(height * dpr);

  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);
  return { ctx, width, height };
}

function drawFallbackDonut(canvas, data) {
  const { ctx, width, height } = prepareCanvas(canvas, 280);
  const values = data.map((x) => Number(x.total || 0)).filter((v) => v > 0);

  if (!values.length) {
    ctx.fillStyle = "#4f6670";
    ctx.font = "14px Space Grotesk, Segoe UI, sans-serif";
    ctx.fillText("暂无支出数据", 16, 28);
    return;
  }

  const labels = data.filter((x) => Number(x.total || 0) > 0).map((x) => x.category);
  const total = values.reduce((a, b) => a + b, 0);
  const colors = ["#ff8f3d", "#ffba52", "#ffd66b", "#4bc0a8", "#0e9f6e", "#2e7d95", "#8db1ff", "#9b8cff"];

  const cx = width * 0.34;
  const cy = height * 0.5;
  const r = Math.min(width, height) * 0.25;
  const inner = r * 0.58;

  let start = -Math.PI / 2;
  values.forEach((value, idx) => {
    const angle = (value / total) * Math.PI * 2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, r, start, start + angle);
    ctx.closePath();
    ctx.fillStyle = colors[idx % colors.length];
    ctx.fill();
    start += angle;
  });

  ctx.beginPath();
  ctx.arc(cx, cy, inner, 0, Math.PI * 2);
  ctx.fillStyle = "#ffffff";
  ctx.fill();

  ctx.fillStyle = "#113343";
  ctx.font = "700 14px Space Grotesk, Segoe UI, sans-serif";
  ctx.fillText("总支出", cx - 22, cy - 4);
  ctx.font = "700 16px Space Grotesk, Segoe UI, sans-serif";
  ctx.fillText(`￥${total.toFixed(0)}`, cx - 30, cy + 18);

  const legendX = width * 0.62;
  let legendY = 38;
  ctx.font = "13px Space Grotesk, Segoe UI, sans-serif";
  labels.forEach((label, idx) => {
    const value = values[idx];
    const ratio = ((value / total) * 100).toFixed(1);
    ctx.fillStyle = colors[idx % colors.length];
    ctx.fillRect(legendX, legendY - 10, 10, 10);
    ctx.fillStyle = "#113343";
    ctx.fillText(`${label} ${ratio}%`, legendX + 16, legendY);
    legendY += 22;
  });
}

function drawFallbackBars(canvas, data) {
  const { ctx, width, height } = prepareCanvas(canvas, 300);

  if (!data.length) {
    ctx.fillStyle = "#4f6670";
    ctx.font = "14px Space Grotesk, Segoe UI, sans-serif";
    ctx.fillText("暂无月度数据", 16, 28);
    return;
  }

  const months = data.map((x) => x.month);
  const incomes = data.map((x) => Number(x.income || 0));
  const expenses = data.map((x) => Number(x.expense || 0));
  const maxValue = Math.max(1, ...incomes, ...expenses);

  const padL = 42;
  const padR = 12;
  const padT = 20;
  const padB = 46;
  const chartW = width - padL - padR;
  const chartH = height - padT - padB;
  const groupW = chartW / months.length;
  const barW = Math.min(16, groupW * 0.28);

  ctx.strokeStyle = "rgba(17, 51, 67, 0.18)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(padL, padT);
  ctx.lineTo(padL, padT + chartH);
  ctx.lineTo(padL + chartW, padT + chartH);
  ctx.stroke();

  ctx.font = "12px Space Grotesk, Segoe UI, sans-serif";
  ctx.fillStyle = "#4f6670";
  [0, 0.5, 1].forEach((t) => {
    const v = maxValue * (1 - t);
    const y = padT + chartH * t;
    ctx.fillText(v.toFixed(0), 8, y + 4);
    ctx.strokeStyle = "rgba(17, 51, 67, 0.08)";
    ctx.beginPath();
    ctx.moveTo(padL, y);
    ctx.lineTo(padL + chartW, y);
    ctx.stroke();
  });

  months.forEach((month, i) => {
    const gx = padL + i * groupW + groupW / 2;
    const incomeH = (incomes[i] / maxValue) * chartH;
    const expenseH = (expenses[i] / maxValue) * chartH;

    ctx.fillStyle = "#0e9f6e";
    ctx.fillRect(gx - barW - 2, padT + chartH - incomeH, barW, incomeH);

    ctx.fillStyle = "#ff8f3d";
    ctx.fillRect(gx + 2, padT + chartH - expenseH, barW, expenseH);

    ctx.fillStyle = "#113343";
    ctx.fillText(month.slice(5), gx - 14, padT + chartH + 16);
  });

  ctx.fillStyle = "#0e9f6e";
  ctx.fillRect(width - 130, 8, 10, 10);
  ctx.fillStyle = "#113343";
  ctx.fillText("收入", width - 116, 17);
  ctx.fillStyle = "#ff8f3d";
  ctx.fillRect(width - 74, 8, 10, 10);
  ctx.fillStyle = "#113343";
  ctx.fillText("支出", width - 60, 17);
}

function renderExpenseChart(data) {
  const ctx = document.getElementById("expense-chart");
  if (typeof window.Chart !== "function") {
    expenseChartHint.textContent = "当前为离线绘图模式";
    drawFallbackDonut(ctx, data || []);
    return;
  }

  expenseChartHint.textContent = "";

  const labels = data.map((x) => x.category);
  const values = data.map((x) => x.total);

  try {
    expenseChart?.destroy();
    expenseChart = new window.Chart(ctx, {
      type: "doughnut",
      data: {
        labels,
        datasets: [
          {
            data: values,
            backgroundColor: ["#ff8f3d", "#ffba52", "#ffd66b", "#4bc0a8", "#0e9f6e", "#2e7d95"],
          },
        ],
      },
    });
  } catch (err) {
    expenseChartHint.textContent = `图表渲染失败，已切换离线模式：${err.message}`;
    drawFallbackDonut(ctx, data || []);
  }
}

function renderMonthlyChart(data) {
  const ctx = document.getElementById("monthly-chart");
  if (typeof window.Chart !== "function") {
    monthlyChartHint.textContent = "当前为离线绘图模式";
    drawFallbackBars(ctx, data || []);
    return;
  }

  monthlyChartHint.textContent = "";

  const labels = data.map((x) => x.month);

  try {
    monthlyChart?.destroy();
    monthlyChart = new window.Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          { label: "收入", data: data.map((x) => x.income), backgroundColor: "#0e9f6e" },
          { label: "支出", data: data.map((x) => x.expense), backgroundColor: "#ff8f3d" },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "bottom" },
        },
      },
    });
  } catch (err) {
    monthlyChartHint.textContent = `图表渲染失败，已切换离线模式：${err.message}`;
    drawFallbackBars(ctx, data || []);
  }
}

function formatIssueText(issues) {
  if (!issues?.length) return "";
  const errorCount = issues.filter((x) => x.severity === "error").length;
  const warnCount = issues.length - errorCount;
  return `，异常 ${issues.length} 条（错误 ${errorCount}，警告 ${warnCount}）`;
}

function bindCandidateTable(container, candidates) {
  container.querySelectorAll("[data-field]").forEach((el) => {
    el.addEventListener("change", (e) => {
      const field = e.target.dataset.field;
      const idx = Number(e.target.dataset.idx);
      const current = candidates[idx];
      if (!current) return;

      if (field === "selected") {
        current.selected = e.target.checked;
      } else if (field === "amount") {
        current.amount = Number(e.target.value);
      } else {
        current[field] = e.target.value;
      }

      if (field === "type") {
        const row = e.target.closest("tr");
        const categoryEl = row.querySelector('select[data-field="category"]');
        fillCategorySelect(categoryEl, current.type, null);
        current.category = categoryEl.value;
      }
    });
  });
}

function renderCandidateTable(container, candidates, idTitle) {
  container.innerHTML = "";
  if (!candidates.length) {
    container.innerHTML = "<p class='hint empty-hint'>暂无可导入记录。</p>";
    return;
  }

  const table = document.createElement("table");
  table.className = "ocr-table";
  table.innerHTML = `
    <thead>
      <tr>
        <th>导入</th>
        <th>${idTitle}</th>
        <th>类型</th>
        <th>分类</th>
        <th>金额</th>
        <th>日期</th>
        <th>备注</th>
      </tr>
    </thead>
    <tbody></tbody>
  `;

  const tbody = table.querySelector("tbody");
  candidates.forEach((item, idx) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><input type="checkbox" data-field="selected" data-idx="${idx}" ${item.selected ? "checked" : ""} /></td>
      <td title="${item.external_id || "-"}">${item.external_id || "-"}</td>
      <td>
        <select data-field="type" data-idx="${idx}">
          <option value="expense" ${item.type === "expense" ? "selected" : ""}>支出</option>
          <option value="income" ${item.type === "income" ? "selected" : ""}>收入</option>
        </select>
      </td>
      <td><select data-field="category" data-idx="${idx}"></select></td>
      <td><input data-field="amount" data-idx="${idx}" type="number" min="0.01" step="0.01" value="${Number(item.amount).toFixed(2)}" /></td>
      <td><input data-field="txn_date" data-idx="${idx}" type="date" value="${item.txn_date}" /></td>
      <td><textarea data-field="note" data-idx="${idx}" rows="2" placeholder="可填写备注">${item.note || ""}</textarea></td>
    `;
    tbody.appendChild(tr);

    const categoryEl = tr.querySelector('select[data-field="category"]');
    fillCategorySelect(categoryEl, item.type, item.category);
  });

  container.appendChild(table);
  bindCandidateTable(container, candidates);
}

function renderOCRList() {
  renderCandidateTable(ocrList, ocrCandidates, "来源");
}

function renderAlipayList() {
  renderCandidateTable(alipayList, alipayCandidates, "支付宝交易号");
}

function renderWechatList() {
  renderCandidateTable(wechatList, wechatCandidates, "微信交易单号");
}

async function runOCRPreview() {
  const file = ocrFileInput.files?.[0];
  if (!file) {
    ocrStatus.textContent = "请先选择图片文件";
    return;
  }

  ocrStatus.textContent = "识别中，请稍候...";
  const formData = new FormData();
  formData.append("file", file);

  try {
    const result = await request("/ocr/preview", { method: "POST", body: formData });
    if (result.categories) {
      categoryOptions = result.categories;
      fillCategorySelect(categorySelect, typeSelect.value, categorySelect.value);
      fillFilterCategorySelect();
      fillBudgetCategorySelect();
    }

    ocrCandidates = (result.items || []).map((item) => ({
      selected: Boolean(item.selected),
      type: item.type,
      category: item.category,
      amount: Number(item.amount),
      txn_date: item.txn_date,
      note: item.note || "",
      external_id: "OCR",
    }));

    ocrStatus.textContent = `识别完成：候选 ${ocrCandidates.length} 条${formatIssueText(result.issues)}`;
    renderOCRList();
  } catch (err) {
    ocrStatus.textContent = `识别失败：${err.message}`;
    ocrCandidates = [];
    renderOCRList();
  }
}

async function runAlipayPreview() {
  const file = alipayFileInput.files?.[0];
  if (!file) {
    alipayStatus.textContent = "请先选择支付宝 CSV 文件";
    return;
  }

  alipayStatus.textContent = "解析中，请稍候...";
  const formData = new FormData();
  formData.append("file", file);

  try {
    const result = await request("/imports/alipay/preview", { method: "POST", body: formData });
    alipayCandidates = (result.items || []).map((item) => ({
      selected: Boolean(item.selected),
      type: item.type,
      category: item.category,
      amount: Number(item.amount),
      txn_date: item.txn_date,
      note: item.note || "",
      external_id: item.external_id,
      source: item.source,
      import_key: item.import_key,
    }));

    const required = (result.required_headers || []).join("、");
    alipayStatus.textContent = `解析完成：候选 ${alipayCandidates.length} 条，必须表头：${required}${formatIssueText(result.issues)}`;
    renderAlipayList();
  } catch (err) {
    alipayStatus.textContent = `解析失败：${err.message}`;
    alipayCandidates = [];
    renderAlipayList();
  }
}

async function runWechatPreview() {
  const file = wechatFileInput.files?.[0];
  if (!file) {
    wechatStatus.textContent = "请先选择微信 XLSX 文件";
    return;
  }

  wechatStatus.textContent = "解析中，请稍候...";
  const formData = new FormData();
  formData.append("file", file);

  try {
    const result = await request("/imports/wechat/preview", { method: "POST", body: formData });
    wechatCandidates = (result.items || []).map((item) => ({
      selected: Boolean(item.selected),
      type: item.type,
      category: item.category,
      amount: Number(item.amount),
      txn_date: item.txn_date,
      note: item.note || "",
      external_id: item.external_id,
      source: item.source,
      import_key: item.import_key,
    }));

    const required = (result.required_headers || []).join("、");
    wechatStatus.textContent = `解析完成：候选 ${wechatCandidates.length} 条，固定表头：${required}${formatIssueText(result.issues)}`;
    renderWechatList();
  } catch (err) {
    wechatStatus.textContent = `解析失败：${err.message}`;
    wechatCandidates = [];
    renderWechatList();
  }
}

async function importSelectedOCRItems() {
  const selectedItems = ocrCandidates
    .filter((item) => item.selected)
    .map((item) => ({
      type: item.type,
      category: item.category,
      amount: Number(item.amount),
      txn_date: item.txn_date,
      note: item.note?.trim() || null,
    }))
    .filter((item) => item.category && item.amount > 0 && item.txn_date);

  if (!selectedItems.length) {
    ocrStatus.textContent = "请至少勾选一条有效记录";
    return;
  }

  await request("/transactions/batch", {
    method: "POST",
    body: JSON.stringify({ items: selectedItems }),
  });

  ocrStatus.textContent = `已导入 ${selectedItems.length} 条记录`;
  ocrCandidates = [];
  renderOCRList();
  await refreshAll();
}

async function importSelectedAlipayItems() {
  const selectedItems = alipayCandidates
    .filter((item) => item.selected)
    .map((item) => ({
      selected: true,
      type: item.type,
      category: item.category,
      amount: Number(item.amount),
      txn_date: item.txn_date,
      note: item.note?.trim() || null,
      external_id: item.external_id,
      source: item.source,
      import_key: item.import_key,
    }))
    .filter((item) => item.category && item.amount > 0 && item.txn_date && item.import_key);

  if (!selectedItems.length) {
    alipayStatus.textContent = "请至少勾选一条有效记录";
    return;
  }

  const result = await request("/imports/alipay", {
    method: "POST",
    body: JSON.stringify({ items: selectedItems }),
  });

  alipayStatus.textContent = `导入完成：新增 ${result.inserted} 条，跳过重复 ${result.skipped} 条`;
  alipayCandidates = [];
  renderAlipayList();
  await refreshAll();
}

async function importSelectedWechatItems() {
  const selectedItems = wechatCandidates
    .filter((item) => item.selected)
    .map((item) => ({
      selected: true,
      type: item.type,
      category: item.category,
      amount: Number(item.amount),
      txn_date: item.txn_date,
      note: item.note?.trim() || null,
      external_id: item.external_id,
      source: item.source,
      import_key: item.import_key,
    }))
    .filter((item) => item.category && item.amount > 0 && item.txn_date && item.import_key);

  if (!selectedItems.length) {
    wechatStatus.textContent = "请至少勾选一条有效记录";
    return;
  }

  const result = await request("/imports/wechat", {
    method: "POST",
    body: JSON.stringify({ items: selectedItems }),
  });

  wechatStatus.textContent = `导入完成：新增 ${result.inserted} 条，跳过重复 ${result.skipped} 条`;
  wechatCandidates = [];
  renderWechatList();
  await refreshAll();
}

function getFilters() {
  return {
    date_from: filterDateFrom.value || undefined,
    date_to: filterDateTo.value || undefined,
    txn_type: filterType.value || undefined,
    category: filterCategory.value || undefined,
    amount_min: filterAmountMin.value || undefined,
    amount_max: filterAmountMax.value || undefined,
    keyword: filterKeyword.value?.trim() || undefined,
    sort_by: sortBy.value,
    sort_order: sortOrder.value,
  };
}

function resetFilters() {
  filterDateFrom.value = "";
  filterDateTo.value = "";
  filterType.value = "";
  filterCategory.value = "";
  filterAmountMin.value = "";
  filterAmountMax.value = "";
  filterKeyword.value = "";
  sortBy.value = "txn_date";
  sortOrder.value = "desc";
}

function showFilterPopup() {
  filterPopup.hidden = !filterPopup.hidden;
}

function hideFilterPopup() {
  filterPopup.hidden = true;
}

function levelLabel(level) {
  if (level === "over") return "已超支";
  if (level === "warning") return "预警";
  return "正常";
}

function renderBudgetStatus(status) {
  budgetOverview.innerHTML = "";
  budgetList.innerHTML = "";

  if (status.total_budget) {
    const ratioText = `${(status.total_ratio * 100).toFixed(1)}%`;
    budgetOverview.innerHTML = `月总预算：￥${status.total_budget.toFixed(2)}，已支出：￥${status.total_spent.toFixed(2)}，占比 ${ratioText} <span class="level ${status.total_level}">${levelLabel(status.total_level)}</span>`;
  } else {
    budgetOverview.textContent = `本月已支出：￥${status.total_spent.toFixed(2)}（尚未设置月总预算）`;
  }

  if (!status.category_status.length) {
    budgetList.innerHTML = "<p class='hint'>暂无分类预算。</p>";
    return;
  }

  const table = document.createElement("table");
  table.className = "ocr-table";
  table.innerHTML = `
    <thead>
      <tr>
        <th>分类</th>
        <th>预算</th>
        <th>已支出</th>
        <th>占比</th>
        <th>状态</th>
      </tr>
    </thead>
    <tbody>
      ${status.category_status
        .map(
          (item) => `
        <tr>
          <td>${item.category}</td>
          <td>￥${item.budget.toFixed(2)}</td>
          <td>￥${item.spent.toFixed(2)}</td>
          <td>${(item.ratio * 100).toFixed(1)}%</td>
          <td><span class="level ${item.level}">${levelLabel(item.level)}</span></td>
        </tr>
      `
        )
        .join("")}
    </tbody>
  `;
  budgetList.appendChild(table);
}

async function loadBudgetStatus() {
  const month = budgetMonthInput.value || getCurrentMonth();
  budgetMonthInput.value = month;

  const status = await request(`/budgets/${month}`);
  budgetDraftCategoryMap = {};
  status.category_status.forEach((x) => {
    budgetDraftCategoryMap[x.category] = Number(x.budget);
  });

  budgetTotalInput.value = status.total_budget ? Number(status.total_budget).toFixed(2) : "";
  renderBudgetStatus(status);
  budgetStatus.textContent = `预算状态已更新：${month}`;
}

function upsertBudgetCategoryDraft() {
  const category = budgetCategorySelect.value;
  const amount = Number(budgetCategoryAmountInput.value);
  if (!category || !Number.isFinite(amount) || amount <= 0) {
    budgetStatus.textContent = "请填写有效的分类预算金额";
    return false;
  }
  budgetDraftCategoryMap[category] = amount;
  budgetCategoryAmountInput.value = "";
  budgetStatus.textContent = `已更新分类预算草稿：${category} ￥${amount.toFixed(2)}`;
  return true;
}

async function saveBudget() {
  const month = budgetMonthInput.value || getCurrentMonth();
  budgetMonthInput.value = month;

  const totalBudgetRaw = budgetTotalInput.value.trim();
  const payload = {
    total_budget: totalBudgetRaw ? Number(totalBudgetRaw) : null,
    category_budgets: Object.entries(budgetDraftCategoryMap).map(([category, amount]) => ({
      category,
      amount,
    })),
  };

  await request(`/budgets/${month}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  await loadBudgetStatus();
}

async function downloadBackup() {
  backupStatus.textContent = "正在导出备份...";
  const resp = await fetch(`${API_BASE}/backup/export`);
  if (!resp.ok) {
    throw new Error("导出备份失败");
  }

  const blob = await resp.blob();
  const disposition = resp.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename=\"?([^\"]+)\"?/i);
  const filename = match?.[1] || `homefin-backup-${Date.now()}.json`;

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  backupStatus.textContent = `备份导出成功：${filename}`;
}

async function restoreBackup() {
  const file = backupFileInput.files?.[0];
  if (!file) {
    backupStatus.textContent = "请先选择备份文件";
    return;
  }
  if (!confirm("恢复会覆盖当前全部数据，是否继续？")) return;

  const formData = new FormData();
  formData.append("file", file);
  const result = await request("/backup/restore", {
    method: "POST",
    body: formData,
  });
  backupStatus.textContent = `恢复成功：交易 ${result.restored_transactions} 条，预算 ${result.restored_budgets} 条`;
  await refreshAll();
  await loadBudgetStatus();
}

async function refreshAll() {
  const query = buildQuery(getFilters());
  const [txns, expenseStats, monthlyStats] = await Promise.all([
    request(`/transactions${query}`),
    request("/stats/category/expense"),
    request("/stats/monthly"),
  ]);

  renderList(txns);
  try {
    renderExpenseChart(expenseStats);
  } catch (err) {
    expenseChartHint.textContent = `图表渲染失败：${err.message}`;
  }
  try {
    renderMonthlyChart(monthlyStats);
  } catch (err) {
    monthlyChartHint.textContent = `图表渲染失败：${err.message}`;
  }
}

async function initCategoryOptions() {
  const categories = await request("/categories");
  categoryOptions = categories;
  fillCategorySelect(categorySelect, typeSelect.value, null);
  fillFilterCategorySelect();
  fillBudgetCategorySelect();
}

typeSelect.addEventListener("change", () => {
  fillCategorySelect(categorySelect, typeSelect.value, null);
});

cancelEditBtn.addEventListener("click", exitEditMode);

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const formData = new FormData(form);
  const payload = {
    type: formData.get("type"),
    category: formData.get("category"),
    amount: Number(formData.get("amount")),
    txn_date: formData.get("txn_date"),
    note: formData.get("note").trim() || null,
  };

  if (editingTxnId) {
    await request(`/transactions/${editingTxnId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  } else {
    await request("/transactions", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  exitEditMode();
  await refreshAll();
  await loadBudgetStatus();
});

refreshBtn.addEventListener("click", refreshAll);
filterToggleBtn.addEventListener("click", showFilterPopup);
filterCloseBtn.addEventListener("click", hideFilterPopup);
filterApplyBtn.addEventListener("click", async () => {
  await refreshAll();
  hideFilterPopup();
});
filterResetBtn.addEventListener("click", async () => {
  resetFilters();
  await refreshAll();
  hideFilterPopup();
});

budgetAddCategoryBtn.addEventListener("click", upsertBudgetCategoryDraft);
budgetSaveBtn.addEventListener("click", saveBudget);
budgetRefreshBtn.addEventListener("click", loadBudgetStatus);
budgetMonthInput.addEventListener("change", loadBudgetStatus);

backupExportBtn.addEventListener("click", async () => {
  try {
    await downloadBackup();
  } catch (err) {
    backupStatus.textContent = `导出失败：${err.message}`;
  }
});
backupRestoreBtn.addEventListener("click", async () => {
  try {
    await restoreBackup();
  } catch (err) {
    backupStatus.textContent = `恢复失败：${err.message}`;
  }
});

ocrBtn.addEventListener("click", runOCRPreview);
ocrImportBtn.addEventListener("click", importSelectedOCRItems);
alipayPreviewBtn.addEventListener("click", runAlipayPreview);
alipayImportBtn.addEventListener("click", importSelectedAlipayItems);
wechatPreviewBtn.addEventListener("click", runWechatPreview);
wechatImportBtn.addEventListener("click", importSelectedWechatItems);

async function bootstrap() {
  hideFilterPopup();
  form.elements.txn_date.value = getCurrentDate();
  budgetMonthInput.value = getCurrentMonth();
  await initCategoryOptions();
  renderOCRList();
  renderAlipayList();
  renderWechatList();
  await refreshAll();
  await loadBudgetStatus();

  // 首屏内容渲染完成后再加载图表库，避免阻塞 LCP。
  setTimeout(() => {
    loadChartLibrary()
      .then(() => refreshAll())
      .catch(() => {
        expenseChartHint.textContent = "图表库加载失败，当前使用离线绘图模式（需要梯子）";
        monthlyChartHint.textContent = "图表库加载失败，当前使用离线绘图模式（需要梯子）";
      });
  }, 0);
}

bootstrap().catch((err) => {
  txnList.innerHTML = `<p>记录加载失败：${err.message}</p>`;
});

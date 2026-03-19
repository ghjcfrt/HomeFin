const API_BASE = "http://localhost:8000";

const form = document.getElementById("txn-form");
const txnList = document.getElementById("txn-list");
const refreshBtn = document.getElementById("refresh-btn");
const categorySelect = form.elements.category;
const typeSelect = form.elements.type;

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

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const isFormData = options.body instanceof FormData;
  if (!isFormData) {
    headers["Content-Type"] = "application/json";
  }

  const resp = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || "请求失败");
  }

  if (resp.status === 204) return null;
  return resp.json();
}

function formatCurrency(value, type) {
  const symbol = type === "income" ? "+" : "-";
  return `${symbol}￥${Number(value).toFixed(2)}`;
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

function renderList(items) {
  txnList.innerHTML = "";

  if (!items.length) {
    txnList.innerHTML = "<p>暂无记录，先添加一笔吧。</p>";
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
      <div class="actions"><button data-id="${item.id}">删除</button></div>
    `;
    txnList.appendChild(card);
  }

  txnList.querySelectorAll("button[data-id]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("确认删除这条记录吗？")) return;
      await request(`/transactions/${btn.dataset.id}`, { method: "DELETE" });
      await refreshAll();
    });
  });
}

function renderExpenseChart(data) {
  const ctx = document.getElementById("expense-chart");
  const labels = data.map((x) => x.category);
  const values = data.map((x) => x.total);

  expenseChart?.destroy();
  expenseChart = new Chart(ctx, {
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
}

function renderMonthlyChart(data) {
  const ctx = document.getElementById("monthly-chart");
  const labels = data.map((x) => x.month);

  monthlyChart?.destroy();
  monthlyChart = new Chart(ctx, {
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

function renderOCRList() {
  ocrList.innerHTML = "";

  if (!ocrCandidates.length) {
    ocrList.innerHTML = "<p class='hint'>暂无可导入账单，请先点击“识别账单”。</p>";
    return;
  }

  const table = document.createElement("table");
  table.className = "ocr-table";
  table.innerHTML = `
    <thead>
      <tr>
        <th>导入</th>
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
  ocrCandidates.forEach((item, idx) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><input type="checkbox" data-field="selected" data-idx="${idx}" ${item.selected ? "checked" : ""} /></td>
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

  ocrList.appendChild(table);
  bindCandidateTable(ocrList, ocrCandidates);
}

function renderAlipayList() {
  alipayList.innerHTML = "";

  if (!alipayCandidates.length) {
    alipayList.innerHTML = "<p class='hint'>暂无可导入账单，请先点击“解析 CSV”。</p>";
    return;
  }

  const table = document.createElement("table");
  table.className = "ocr-table";
  table.innerHTML = `
    <thead>
      <tr>
        <th>导入</th>
        <th>支付宝交易号</th>
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
  alipayCandidates.forEach((item, idx) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><input type="checkbox" data-field="selected" data-idx="${idx}" ${item.selected ? "checked" : ""} /></td>
      <td title="${item.external_id}">${item.external_id}</td>
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

  alipayList.appendChild(table);
  bindCandidateTable(alipayList, alipayCandidates);
}

function renderWechatList() {
  wechatList.innerHTML = "";

  if (!wechatCandidates.length) {
    wechatList.innerHTML = "<p class='hint'>暂无可导入账单，请先点击“解析 XLSX”。</p>";
    return;
  }

  const table = document.createElement("table");
  table.className = "ocr-table";
  table.innerHTML = `
    <thead>
      <tr>
        <th>导入</th>
        <th>微信交易单号</th>
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
  wechatCandidates.forEach((item, idx) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><input type="checkbox" data-field="selected" data-idx="${idx}" ${item.selected ? "checked" : ""} /></td>
      <td title="${item.external_id}">${item.external_id}</td>
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

  wechatList.appendChild(table);
  bindCandidateTable(wechatList, wechatCandidates);
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
    const result = await request("/ocr/preview", {
      method: "POST",
      body: formData,
    });

    if (result.categories) {
      categoryOptions = result.categories;
      fillCategorySelect(categorySelect, typeSelect.value, categorySelect.value);
    }

    ocrCandidates = (result.items || []).map((item) => ({
      selected: Boolean(item.selected),
      type: item.type,
      category: item.category,
      amount: Number(item.amount),
      txn_date: item.txn_date,
      note: item.note || "",
    }));

    ocrStatus.textContent = `识别完成：共 ${ocrCandidates.length} 条候选记录`;
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
    const result = await request("/imports/alipay/preview", {
      method: "POST",
      body: formData,
    });

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
    alipayStatus.textContent = `解析完成：共 ${alipayCandidates.length} 条候选记录。必须表头：${required}`;
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
    const result = await request("/imports/wechat/preview", {
      method: "POST",
      body: formData,
    });

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
    wechatStatus.textContent = `解析完成：共 ${wechatCandidates.length} 条候选记录。固定表头：${required}`;
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

async function refreshAll() {
  const [txns, expenseStats, monthlyStats] = await Promise.all([
    request("/transactions"),
    request("/stats/category/expense"),
    request("/stats/monthly"),
  ]);

  renderList(txns);
  renderExpenseChart(expenseStats);
  renderMonthlyChart(monthlyStats);
}

async function initCategoryOptions() {
  const categories = await request("/categories");
  categoryOptions = categories;
  fillCategorySelect(categorySelect, typeSelect.value, null);
}

typeSelect.addEventListener("change", () => {
  fillCategorySelect(categorySelect, typeSelect.value, null);
});

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

  await request("/transactions", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  const currentType = typeSelect.value;
  form.reset();
  typeSelect.value = currentType;
  fillCategorySelect(categorySelect, typeSelect.value, null);
  form.elements.txn_date.value = new Date().toISOString().slice(0, 10);
  await refreshAll();
});

refreshBtn.addEventListener("click", refreshAll);
ocrBtn.addEventListener("click", runOCRPreview);
ocrImportBtn.addEventListener("click", importSelectedOCRItems);
alipayPreviewBtn.addEventListener("click", runAlipayPreview);
alipayImportBtn.addEventListener("click", importSelectedAlipayItems);
wechatPreviewBtn.addEventListener("click", runWechatPreview);
wechatImportBtn.addEventListener("click", importSelectedWechatItems);

async function bootstrap() {
  form.elements.txn_date.value = new Date().toISOString().slice(0, 10);
  await initCategoryOptions();
  renderOCRList();
  renderAlipayList();
  renderWechatList();
  await refreshAll();
}

bootstrap().catch((err) => {
  txnList.innerHTML = `<p>加载失败：${err.message}</p>`;
});

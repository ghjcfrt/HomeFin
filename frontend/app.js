const API_BASE = "http://localhost:8000";

const form = document.getElementById("txn-form");
const txnList = document.getElementById("txn-list");
const refreshBtn = document.getElementById("refresh-btn");

let expenseChart;
let monthlyChart;

async function request(path, options = {}) {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
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
      plugins: {
        legend: { position: "bottom" },
      },
    },
  });
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

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const formData = new FormData(form);
  const payload = {
    type: formData.get("type"),
    category: formData.get("category").trim(),
    amount: Number(formData.get("amount")),
    txn_date: formData.get("txn_date"),
    note: formData.get("note").trim() || null,
  };

  await request("/transactions", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  form.reset();
  form.elements.txn_date.value = new Date().toISOString().slice(0, 10);
  await refreshAll();
});

refreshBtn.addEventListener("click", refreshAll);

form.elements.txn_date.value = new Date().toISOString().slice(0, 10);
refreshAll().catch((err) => {
  txnList.innerHTML = `<p>加载失败：${err.message}</p>`;
});

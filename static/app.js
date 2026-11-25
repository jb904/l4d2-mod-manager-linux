let allMods = [];
let currentTab = "all";
let currentMode = "";

const $list    = document.getElementById("list");
const $count   = document.getElementById("count");
const $apply   = document.getElementById("apply");
const $modes   = document.getElementById("modes");
const $pickAll = document.getElementById("pickAll");
const $pickAllWrap = document.querySelector(".pick-all");

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}

async function loadMods() {
  const res = await fetch("/api/mods");
  allMods = await res.json();
  render();
}

function currentList() {
  if (currentTab === "enabled")  return allMods.filter(m => m.status === "enabled");
  if (currentTab === "disabled") return allMods.filter(m => m.status === "disabled");
  return allMods;
}

function render() {
  $list.innerHTML = "";
  const mods = currentList();

  if (!mods.length) {
    $list.innerHTML = '<div class="empty">这里没有模组</div>';
    updateCount();
    return;
  }

  const hasCtrl = currentTab !== "all" && currentMode !== "";
  const isAlias = hasCtrl && currentMode === "alias";

  for (const m of mods) {
    const title  = m.mod_alias || m.mod_name || "error";
    const origin = (m.mod_alias && m.mod_name) ? m.mod_name : "";

    const card = document.createElement("div");
    card.className = "mod" + (isAlias ? " alias-mode" : "");
    card.dataset.id = m.mod_id;

    card.innerHTML = `
      ${m.has_img ? `<div class="thumb"><img src="/img/${encodeURIComponent(m.mod_id)}.jpg" alt=""></div>` : ""}
      <div class="info">
        <div class="name">${esc(title)}</div>
        ${origin ? `<div class="alias">${esc(origin)}</div>` : ""}
        <div class="sub"><span class="dot ${m.status}"></span>${esc(m.mod_id)}</div>
      </div>
      <div class="ctrl"></div>
      ${isAlias ? `<div class="alias-row"><input type="text" class="alias-input" value="${esc(m.mod_alias)}" placeholder="勾选后输入新别名"></div>` : ""}
    `;

    if (hasCtrl) {
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.className = "pick";
      cb.addEventListener("change", () => {
        card.classList.toggle("picked", cb.checked);
        updateCount();
      });
      card.querySelector(".ctrl").appendChild(cb);
    }

    $list.appendChild(card);
  }

  updateCount();
}

function updateCount() {
  const n = document.querySelectorAll(".pick:checked").length;
  $count.textContent = `已选 ${n} 项`;
}

document.getElementById("tabs").addEventListener("click", e => {
  const btn = e.target.closest(".tab");
  if (!btn) return;

  document.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  currentTab = btn.dataset.tab;

  $modes.hidden = currentTab === "all";
  $pickAllWrap.hidden = currentTab === "all";

  if (currentTab === "all") {
    currentMode = "";
    document.querySelectorAll('input[name="mode"]').forEach(r => (r.checked = false));
  }

  $pickAll.checked = false;
  render();
});

document.querySelectorAll('input[name="mode"]').forEach(r => {
  r.addEventListener("change", () => {
    currentMode = r.value;
    $pickAll.checked = false;
    render();
  });
});

$pickAll.addEventListener("change", () => {
  document.querySelectorAll(".mod").forEach(card => {
    const cb = card.querySelector(".pick");
    if (!cb) return;
    cb.checked = $pickAll.checked;
    card.classList.toggle("picked", cb.checked);
  });
  updateCount();
});

$apply.addEventListener("click", async () => {
  if (currentTab === "all") return alert("全部模组页面只能浏览");
  if (!currentMode)         return alert("请先在左侧选择操作方式");

  if (currentMode === "alias") {
    const picked = [...document.querySelectorAll(".mod.picked")];
    if (!picked.length) return alert("请先勾选要改名的模组");

    const mods = picked.map(div => ({
      id: div.dataset.id,
      alias: div.querySelector(".alias-input")?.value ?? "",
    }));

    await fetch("/api/alias", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mods }),
    });
  } else {
    const ids = [...document.querySelectorAll(".mod.picked")].map(d => d.dataset.id);

    if (!ids.length) return alert("请先勾选模组");

    if (currentMode === "disable" || currentMode === "enable") {
      await fetch("/api/move", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids, enable: currentMode === "enable" }),
      });
    } else if (currentMode === "refetch") {
      $apply.disabled = true;
      $apply.textContent = "抓取中…";
      await fetch("/api/refetch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids }),
      });
      $apply.disabled = false;
      $apply.textContent = "执行";
    }
  }

  await loadMods();
});

loadMods();
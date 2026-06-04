// ===========================
// 設定
// ===========================
const PER_PAGE = 5;
const JSON_PATH = "archives.json";

// カテゴリの表示名とバッジクラス
const CAT_INFO = {
  game:   { label: "ゲーム実況", cls: "badge-game" },
  talk:   { label: "雑談",       cls: "badge-talk" },
  collab: { label: "コラボ",     cls: "badge-collab" },
  other:  { label: "その他",     cls: "badge-other" },
};

// ===========================
// 状態
// ===========================
let archives     = [];   // JSONから読み込んだ全データ
let selectedTags   = new Set(); // 複数タグ選択（空＝すべて表示）
let currentPage  = 1;
let currentQuery = "";

// ===========================
// JSONの読み込み（追加）
// ===========================
async function loadArchives() {
  try {
    const res = await fetch(JSON_PATH);
    if (!res.ok) throw new Error(`HTTP error: ${res.status}`);
    archives = await res.json();
  } catch (err) {
    console.error("アーカイブデータの読み込みに失敗しました:", err);
    document.getElementById("archiveList").innerHTML =
      '<li class="empty-state">データの読み込みに失敗しました。ページを再読み込みしてください。</li>';
  }
}

// ===========================
// フィルタリング
// ===========================
function getFiltered() {
  return archives.filter(a => {
     const tags = Array.isArray(a.tags) ? a.tags : (a.cat ? [a.cat] : []);

    // タグ絞り込み：selectedTags が空 = すべて表示、あればOR一致
    const matchTag = selectedTags.size === 0
      || tags.some(t => selectedTags.has(t));

    const matchQuery = a.title.includes(currentQuery);
    return matchTag && matchQuery;
  });
}

// ===========================
// カード描画
// ===========================
function renderCards(items) {
  const list = document.getElementById("archiveList");
  list.innerHTML = "";

  if (items.length === 0) {
    list.innerHTML = '<li class="empty-state">該当する配信が見つかりませんでした。</li>';
    return;
  }

  items.forEach((a, i) => {
    const tags = Array.isArray(a.tags) ? a.tags : (a.cat ? [a.cat] : ["other"]);
    const dateStr = a.date.replace(/-/g, "/");

    // タグバッジを複数生成
    const badgesHtml = tags.map(t => {
      const info = CAT_INFO[t] || { label: t, cls: "badge-other" };
      return `<span class="badge ${info.cls}">${info.label}</span>`;
    }).join("");

    const li = document.createElement("li");
    li.className = "archive-card";
    li.style.animationDelay = `${i * 40}ms`;
    li.innerHTML = `
      <div class="card-thumb">▷</div>
      <div class="card-body">
        <p class="card-title">${escapeHtml(a.title)}</p>
        <div class="card-meta">
          <span class="card-date">${dateStr}</span>
          ${badgesHtml}
        </div>
      </div>
      <a class="card-link" href="${escapeHtml(a.url)}" target="_blank" rel="noopener noreferrer">
        <span>視聴</span> ↗
      </a>
    `;
    list.appendChild(li);
  });
}

// ===========================
// ページネーション描画
// ===========================
function renderPagination(total) {
  const maxPage = Math.ceil(total / PER_PAGE);
  const pag = document.getElementById("pagination");
  pag.innerHTML = "";

  if (maxPage <= 1) return;

  // 前へ
  const prev = document.createElement("button");
  prev.className = "page-btn";
  prev.textContent = "←";
  prev.disabled = currentPage === 1;
  prev.addEventListener("click", () => goPage(currentPage - 1));
  pag.appendChild(prev);

  // ページ番号
  for (let p = 1; p <= maxPage; p++) {
    const btn = document.createElement("button");
    btn.className = "page-btn" + (p === currentPage ? " active" : "");
    btn.textContent = p;
    btn.addEventListener("click", () => goPage(p));
    pag.appendChild(btn);
  }

  // 次へ
  const next = document.createElement("button");
  next.className = "page-btn";
  next.textContent = "→";
  next.disabled = currentPage === maxPage;
  next.addEventListener("click", () => goPage(currentPage + 1));
  pag.appendChild(next);
}

// ===========================
// 件数表示
// ===========================
function renderCount(total) {
  const el = document.getElementById("resultCount");
  el.textContent = `全${archives.length}件中 ${total}件表示`;
}

// ===========================
// 全体描画
// ===========================
function render() {
  const filtered = getFiltered();
  const total    = filtered.length;
  const maxPage  = Math.max(1, Math.ceil(total / PER_PAGE));
  if (currentPage > maxPage) currentPage = maxPage;

  const start = (currentPage - 1) * PER_PAGE;
  const paged = filtered.slice(start, start + PER_PAGE);

  renderCount(total);
  renderCards(paged);
  renderPagination(total);
}

// ===========================
// ページ移動
// ===========================
function goPage(p) {
  currentPage = p;
  render();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ===========================
// イベント：フィルタータグ
// ===========================
document.getElementById("filterRow").addEventListener("click", e => {
  const btn = e.target.closest(".tag");
  if (!btn) return;
    document.querySelectorAll(".tag").forEach(t => t.classList.remove("active"));
    btn.classList.add("active");
  currentCat  = btn.dataset.cat;
  currentPage = 1;
  render();
});

// ===========================
// イベント：検索
// ===========================
let searchTimer;
document.getElementById("searchInput").addEventListener("input", e => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    currentQuery = e.target.value.trim();
    currentPage  = 1;
    render();
  }, 200);
});

// ===========================
// XSSを防ぐエスケープ
// ===========================
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ===========================
// 起動：JSON読み込み → 描画（変更）
// ===========================
loadArchives().then(() => render());

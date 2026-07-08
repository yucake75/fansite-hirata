// ===========================
// 設定
// ===========================
const PER_PAGE = 15;
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
let currentGame = ""; // ゲームタブ用の選択中ゲーム名
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

  // ページ番号（省略付き）
  const pages = getPaginationRange(currentPage, maxPage, 2);
  pages.forEach((p) => {
    if (p === "...") {
      const dots = document.createElement("span");
      dots.className = "page-dots";
      dots.textContent = "…";
      pag.appendChild(dots);
    } else {
      const btn = document.createElement("button");
      btn.className = "page-btn" + (p === currentPage ? " active" : "");
      btn.textContent = p;
      btn.addEventListener("click", () => goPage(p));
      pag.appendChild(btn);
    }
  });

  // 次へ
  const next = document.createElement("button");
  next.className = "page-btn";
  next.textContent = "→";
  next.disabled = currentPage === maxPage;
  next.addEventListener("click", () => goPage(currentPage + 1));
  pag.appendChild(next);
}

// ===========================
// ページ番号配列を生成（省略付き）
// ===========================
function getPaginationRange(current, total, delta = 2) {
  const range = [];
  const rangeWithDots = [];
  let last;

  for (let i = 1; i <= total; i++) {
    if (i === 1 || i === total || (i >= current - delta && i <= current + delta)) {
      range.push(i);
    }
  }

  for (const i of range) {
    if (last) {
      if (i - last === 2) {
        // 1つだけ飛ぶ場合は省略せず数字を出す
        rangeWithDots.push(last + 1);
      } else if (i - last !== 1) {
        rangeWithDots.push("...");
      }
    }
    rangeWithDots.push(i);
    last = i;
  }

  return rangeWithDots;
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

  const cat = btn.dataset.cat;

  // アクティブを全解除してから選択したものだけアクティブに
  document.querySelectorAll(".tag").forEach(t => t.classList.remove("active"));
  btn.classList.add("active");

  if (cat === "all") {
    selectedTags.clear();
  } else {
    selectedTags.clear();
    selectedTags.add(cat);
  }

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
loadArchives().then(() => {
  renderUpdatedAt();
  render();
});


function renderUpdatedAt() {
  const updatedAt = new Date().toLocaleString("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
  const el = document.getElementById("updatedAt");
  if (el) {
    el.textContent = updatedAt;
  }
}


// ===========================
// ゲームタブ描画
// ===========================
let currentGameQuery = "";
let gameListCache = []; // ゲーム名一覧のキャッシュ（毎回全archivesを走査しないように）
 
function renderGameTab() {
  const container = document.getElementById("gameTab");
  container.innerHTML = "";
 
  // ゲーム名を昇順で収集（初回のみ計算、以降はキャッシュを再利用）
  if (gameListCache.length === 0) {
    gameListCache = [...new Set(archives.map(a => a.game).filter(Boolean))].sort();
  }
 
  const query = currentGameQuery.trim().toLowerCase();
  const gameList = query
    ? gameListCache.filter(g => g.toLowerCase().includes(query))
    : gameListCache;
 
  const ul = document.createElement("ul");
  ul.className = "game-list";
 
  if (gameList.length === 0) {
    ul.innerHTML = '<li class="empty-state">該当するゲームが見つかりませんでした。</li>';
    container.appendChild(ul);
    return;
  }
 
  gameList.forEach(g => {
    const count = archives.filter(a => a.game === g).length;
    const li = document.createElement("li");
    li.className = "game-item";
    li.innerHTML = `<span class="game-name">${escapeHtml(g)}</span><span class="game-count">${count}件</span>`;
    li.addEventListener("click", () => openGameModal(g)); // ← モーダルを開く
    ul.appendChild(li);
  });
 
  container.appendChild(ul);
}
 
// ===========================
// イベント：ゲーム検索
// ===========================
let gameSearchTimer;
const gameSearchInput = document.getElementById("gameSearchInput");
if (gameSearchInput) {
  gameSearchInput.addEventListener("input", e => {
    clearTimeout(gameSearchTimer);
    gameSearchTimer = setTimeout(() => {
      currentGameQuery = e.target.value.trim();
      renderGameTab();
    }, 200);
  });
}
 
 
function renderGameButtons(gameList) {
  const wrap = document.getElementById("gameButtonWrap");
  wrap.innerHTML = "";
 
  const query = currentGame.toLowerCase();
  const filtered = gameList.filter(g => g.toLowerCase().includes(query));
 
  filtered.forEach(g => {
    const btn = document.createElement("button");
    btn.className = "tag" + (currentGame === g ? " active" : "");
    btn.textContent = g;
    btn.addEventListener("click", () => {
      currentGame = currentGame === g ? "" : g;
      document.getElementById("gameSearchInput").value = currentGame;
      renderGameButtons(gameList);
      renderGameResults();
    });
    wrap.appendChild(btn);
  });
}
 
function renderGameResults() {
  const wrap = document.getElementById("gameResults");
  wrap.innerHTML = "";
 
  if (!currentGame) return;
 
  const matched = archives.filter(a =>
    a.game && a.game.toLowerCase().includes(currentGame.toLowerCase())
  );
 
  if (matched.length === 0) {
    wrap.innerHTML = '<p class="empty-state">該当する配信が見つかりませんでした。</p>';
    return;
  }
 
  const ul = document.createElement("ul");
  ul.id = "archiveList";
  matched.forEach((a, i) => {
    const tags = Array.isArray(a.tags) ? a.tags : (a.cat ? [a.cat] : []);
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
          <span class="card-date">${a.date.replace(/-/g, "/")}</span>
          ${badgesHtml}
          <span class="card-game">🎮 ${escapeHtml(a.game)}</span>
        </div>
      </div>
      <a class="card-link" href="${escapeHtml(a.url)}" target="_blank" rel="noopener noreferrer">
        <span>視聴</span> ↗
      </a>
    `;
    ul.appendChild(li);
  });
  wrap.appendChild(ul);
}
 
document.getElementById("tabRow").addEventListener("click", e => {
  const btn = e.target.closest("[data-tab]");
  if (!btn) return;
 
  document.querySelectorAll("[data-tab]").forEach(t => t.classList.remove("active"));
  btn.classList.add("active");
 
  const tab = btn.dataset.tab;
  document.getElementById("archiveSection").style.display = tab === "archive" ? "" : "none";
  document.getElementById("gameSection").style.display   = tab === "game"    ? "" : "none";
 
  if (tab === "game") renderGameTab();
});
 
 
// ===========================
// ゲームモーダル
// ===========================
function openGameModal(game) {
  const matched = archives.filter(a => a.game === game);
 
  document.getElementById("modalTitle").textContent = `🎮 ${game}（${matched.length}件）`;
 
  const list = document.getElementById("modalArchiveList");
  list.innerHTML = "";
 
  matched.forEach((a, i) => {
    const tags = Array.isArray(a.tags) ? a.tags : (a.cat ? [a.cat] : []);
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
          <span class="card-date">${a.date.replace(/-/g, "/")}</span>
          ${badgesHtml}
        </div>
      </div>
      <a class="card-link" href="${escapeHtml(a.url)}" target="_blank" rel="noopener noreferrer">
        <span>視聴</span> ↗
      </a>
    `;
    list.appendChild(li);
  });
 
  document.getElementById("gameModal").style.display = "flex";
}
 
// モーダルを閉じる
document.getElementById("modalClose").addEventListener("click", () => {
  document.getElementById("gameModal").style.display = "none";
});
 
// オーバーレイクリックでも閉じる
document.getElementById("gameModal").addEventListener("click", e => {
  if (e.target === e.currentTarget) {
    e.currentTarget.style.display = "none";
  }
});
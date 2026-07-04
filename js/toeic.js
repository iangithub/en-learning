/* TOEIC 高頻單字 — category grid + flashcard study view (hash routing: #slug) */
(async function () {
  const app = document.getElementById("app");
  const store = progressStore("learned:toeic");
  const hideZh = boolSetting("opt:hideZh", false);
  const autoplay = boolSetting("opt:autoplay", true);

  let INDEX;
  try {
    INDEX = await (await fetch("data/toeic-index.json")).json();
  } catch {
    app.innerHTML = '<div class="empty-note">資料載入失敗，請重新整理再試。</div>';
    return;
  }
  const catCache = new Map();

  async function loadCat(slug) {
    if (!catCache.has(slug)) {
      const res = await fetch(`data/toeic/${slug}.json`);
      catCache.set(slug, await res.json());
    }
    return catCache.get(slug);
  }

  async function route() {
    Player.stop();
    document.onkeydown = null;
    const slug = location.hash.slice(1);
    const meta = INDEX.categories.find((c) => c.slug === slug);
    if (meta) {
      app.innerHTML = '<div class="loading">載入單字中⋯</div>';
      renderStudy(await loadCat(slug));
    } else {
      renderGrid();
    }
    window.scrollTo(0, 0);
  }

  /* ---------- category grid ---------- */
  function renderGrid() {
    app.replaceChildren(
      el("div", { class: "page-head" },
        el("h1", {}, "TOEIC 高頻單字"),
        el("p", {}, `收錄 ${INDEX.total.toLocaleString()} 個字彙，依商務情境分類、★1–★5 頻率分層（★5 最高頻）。字卡翻面看詞性變化、例句與考點。`)),
      el("div", { class: "card-grid" },
        ...INDEX.categories.map((c) =>
          el("button", { class: "grid-card", onclick: () => (location.hash = `#${c.slug}`), "aria-label": c.category },
            el("div", { class: "cover" },
              el("img", { src: `images/cat-${c.slug}.webp`, alt: "", loading: "lazy" })),
            el("div", { class: "body" },
              el("div", { class: "tag" }, `${c.count} 字`),
              el("h3", {}, c.category),
              progressEl(c))))));
  }

  function progressEl(c) {
    const key = `learnedCount:${c.slug}`;
    const n = parseInt(localStorage.getItem(key) || "0", 10);
    const pct = Math.min(100, Math.round((n / c.count) * 100));
    return el("div", { class: "progress-row", style: "flex:1" },
      el("div", { class: "progress-track" }, el("div", { class: "progress-fill", style: `width:${pct}%` })),
      el("span", {}, `${n}/${c.count}`));
  }

  /* ---------- study view ---------- */
  function renderStudy(cat) {
    const words = cat.words;
    let order = words.map((_, i) => i);
    let shuffled = false;
    let onlyNew = false;
    let query = "";
    let idx = 0;
    let flipped = false;
    let starSel;
    try { starSel = new Set(JSON.parse(localStorage.getItem("opt:stars") || "[5,4,3,2,1]")); }
    catch { starSel = new Set([5, 4, 3, 2, 1]); }

    const view = el("section", { class: "study" });

    function visible() {
      let v = shuffled ? order : words.map((_, i) => i);
      v = v.filter((i) => starSel.has(words[i].star));
      if (onlyNew) v = v.filter((i) => !store.has(words[i].id));
      if (query) {
        const q = query.toLowerCase();
        v = v.filter((i) => words[i].word.toLowerCase().includes(q) || words[i].zh.includes(query));
      }
      return v;
    }

    function current() {
      const v = visible();
      if (!v.length) return null;
      if (idx >= v.length) idx = v.length - 1;
      return words[v[idx]];
    }

    function saveCatProgress() {
      const n = store.count(words.map((w) => w.id));
      localStorage.setItem(`learnedCount:${cat.slug}`, String(n));
    }

    function paint() {
      const v = visible();
      const w = current();
      view.replaceChildren(
        el("div", { class: "study-top" },
          el("button", { class: "back-btn", onclick: () => (location.hash = "") }, "← 全部分類"),
          el("span", { class: "study-title" }, cat.category),
          el("span", { class: "study-meta" }, `${words.length} 字`)),
        el("div", { class: "study-controls" },
          el("input", { class: "search-box", type: "search", placeholder: "搜尋單字或中文⋯", value: query,
            oninput: (e) => { query = e.target.value.trim(); idx = 0; flipped = false; paintSoft(); } }),
          toggle("🔀 隨機", shuffled, () => { shuffled = !shuffled; if (shuffled) order = shuffleArr(order); idx = 0; flipped = false; paint(); }),
          toggle("🆕 只看未學會", onlyNew, () => { onlyNew = !onlyNew; idx = 0; flipped = false; paint(); }),
          toggle("🙈 遮中文", hideZh.get(), () => { hideZh.set(!hideZh.get()); paint(); }),
          toggle("🔊 自動發音", autoplay.get(), () => { autoplay.set(!autoplay.get()); paint(); })),
        el("div", { class: "study-controls star-row", role: "group", "aria-label": "星級篩選" },
          el("span", { class: "star-label" }, "星級"),
          ...[5, 4, 3, 2, 1].map((n) => {
            const cnt = words.reduce((a, w) => a + (w.star === n ? 1 : 0), 0);
            return el("button", {
              class: "toggle-btn star-chip", "aria-pressed": String(starSel.has(n)),
              title: `${cnt} 字`,
              onclick: () => {
                starSel.has(n) ? starSel.delete(n) : starSel.add(n);
                localStorage.setItem("opt:stars", JSON.stringify([...starSel]));
                idx = 0; flipped = false; paint();
              } }, `★${n}`, el("small", {}, ` ${cnt}`));
          })),
        el("div", { id: "cardZone" },
          w ? cardEl(w) : el("div", { class: "empty-note" },
            query ? "找不到符合的單字" : (starSel.size === 0 ? "請至少選擇一個星級" : (onlyNew ? "這個範圍都學會了 🎉" : "沒有符合篩選的單字"))),
          w ? navEl(v, w) : null),
        w ? el("div", { class: "kbd-hint" },
          el("kbd", {}, "←"), " ", el("kbd", {}, "→"), " 換卡　",
          el("kbd", {}, "Space"), " 翻面　",
          el("kbd", {}, "P"), " 發音　",
          el("kbd", {}, "L"), " 學會") : null);
    }

    /* repaint only the card zone so the search input keeps focus */
    function paintSoft() {
      const zone = view.querySelector("#cardZone");
      if (!zone) return paint();
      const v = visible();
      const w = current();
      zone.replaceChildren(
        w ? cardEl(w) : el("div", { class: "empty-note" },
          query ? "找不到符合的單字" : (starSel.size === 0 ? "請至少選擇一個星級" : (onlyNew ? "這個範圍都學會了 🎉" : "沒有符合篩選的單字"))),
        w ? navEl(v, w) : null);
    }

    function toggle(label, on, fn) {
      return el("button", { class: "toggle-btn", "aria-pressed": String(on), onclick: fn }, label);
    }

    const POS_ZH = { noun: "名詞", verb: "動詞", adjective: "形容詞", adverb: "副詞", preposition: "介系詞", conjunction: "連接詞", pronoun: "代名詞", interjection: "感嘆詞", phrase: "片語" };

    function cardEl(w) {
      const learned = store.has(w.id);
      const card = el("div", { class: `flashcard${flipped ? " flipped" : ""}`, role: "button", tabindex: "0",
        "aria-label": "字卡，點擊翻面",
        onclick: (e) => { if (e.target.closest(".play-btn,.mini-play,.zh")) return; flipped = !flipped; card.classList.toggle("flipped", flipped); } });

      const zh = el("div", { class: `zh${hideZh.get() ? " hidden-zh" : ""}`,
        onclick: (e) => { if (hideZh.get()) { e.stopPropagation(); e.target.classList.toggle("hidden-zh"); } } }, w.zh);

      const front = el("div", { class: "face face-front" },
        el("div", { class: "badges" },
          el("span", { class: "badge" }, `${"★".repeat(w.star)} · ${w.score}`),
          learned ? el("span", { class: "badge learned" }, "✓ 已學會") : el("span", {})),
        el("div", { class: "en", lang: "en" }, w.word),
        el("div", { class: "pill-row", style: "justify-content:center" },
          ...w.pos.map((p) => el("span", { class: "pill" }, POS_ZH[p] || p))),
        zh,
        el("button", { class: "play-btn", "aria-label": "播放發音", onclick: (e) => { e.stopPropagation(); Player.play(`audio/toeic/${w.id}.mp3`, e.currentTarget); } }, "▶"),
        el("div", { class: "flip-hint" }, "點卡片翻面看變化、例句與考點"));

      const backKids = [
        el("div", { class: "back-head" }, el("span", { class: "en", lang: "en" }, w.word), el("span", { class: "zh" }, w.zh)),
      ];

      if (w.forms?.length) {
        backKids.push(el("div", { class: "back-sec" }, el("h4", {}, "詞性與變化"),
          ...w.forms.map((f) => el("div", { style: "margin:6px 0" },
            el("span", { class: "pill", style: "margin-right:8px" }, POS_ZH[f.part_of_speech] || f.part_of_speech),
            el("span", { lang: "en" }, f.forms.join("、"))))));
      }
      if (w.examples?.length) {
        backKids.push(el("div", { class: "back-sec" }, el("h4", {}, "例句"),
          ...w.examples.map((x, i) => el("div", { class: "ex-item" },
            i === 0 ? el("button", { class: "mini-play", "aria-label": "播放例句發音",
              onclick: (e) => { e.stopPropagation(); Player.play(`audio/toeic/${w.id}_ex.mp3`, e.currentTarget); } }, "▶") : null,
            el("div", {}, el("span", { lang: "en" }, x.english), el("span", { class: "zh-sub" }, x.chinese))))));
      }
      if (w.tips?.length) {
        backKids.push(el("div", { class: "back-sec" }, el("h4", {}, "考點提示"),
          el("ul", {}, ...w.tips.map((t) => el("li", {}, t)))));
      }

      const back = el("div", { class: "face face-back" }, el("div", { class: "back-scroll" }, ...backKids));
      card.append(front, back);
      return el("div", { class: "flash-wrap" }, card);
    }

    function navEl(v, w) {
      const learned = store.has(w.id);
      return el("div", { class: "study-nav" },
        el("button", { class: "nav-btn", disabled: idx === 0 ? "" : null, "aria-label": "上一張", onclick: () => move(-1) }, "←"),
        el("span", { class: "counter" }, `${idx + 1} / ${v.length}`),
        el("button", { class: `learn-btn${learned ? " is-learned" : ""}`, onclick: () => { store.toggle(w.id); saveCatProgress(); paintSoft(); } },
          learned ? "✓ 已學會" : "標記學會"),
        el("button", { class: "nav-btn", disabled: idx >= v.length - 1 ? "" : null, "aria-label": "下一張", onclick: () => move(1) }, "→"));
    }

    function move(d) {
      const v = visible();
      const next = idx + d;
      if (next < 0 || next >= v.length) return;
      idx = next;
      flipped = false;
      Player.stop();
      paintSoft();
      if (autoplay.get()) {
        const w = current();
        if (w) Player.play(`audio/toeic/${w.id}.mp3`, view.querySelector(".play-btn"));
      }
    }

    function onKey(e) {
      if (e.target.matches("input,textarea")) return;
      if (e.key === "ArrowLeft") { e.preventDefault(); move(-1); }
      else if (e.key === "ArrowRight") { e.preventDefault(); move(1); }
      else if (e.key === " ") { e.preventDefault(); const c = view.querySelector(".flashcard"); if (c) { flipped = !flipped; c.classList.toggle("flipped", flipped); } }
      else if (e.key.toLowerCase() === "p") { const w = current(); if (w) Player.play(`audio/toeic/${w.id}.mp3`, view.querySelector(".play-btn")); }
      else if (e.key.toLowerCase() === "l") { const w = current(); if (w) { store.toggle(w.id); saveCatProgress(); paintSoft(); } }
    }
    document.onkeydown = onKey;

    paint();
    app.replaceChildren(view);
  }

  window.addEventListener("hashchange", route);
  route();
})();

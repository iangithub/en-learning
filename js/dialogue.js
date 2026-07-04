/* 情境對話 — category grid → dialogue list → chat view (hash: #uNN / #dNNKK) */
(async function () {
  const app = document.getElementById("app");
  const store = progressStore("done:dialog");
  const hideZh = boolSetting("opt:hideZh", false);

  let INDEX;
  try {
    INDEX = await (await fetch("data/dialogues-index.json")).json();
  } catch {
    app.innerHTML = '<div class="empty-note">資料載入失敗，請重新整理再試。</div>';
    return;
  }
  const catCache = new Map();
  const seq = new Audio(); // sequential play-all player (separate from Player)
  let seqStop = null;

  async function loadCat(unit) {
    const key = String(unit).padStart(2, "0");
    if (!catCache.has(key)) {
      const res = await fetch(`data/dialogues/${key}.json`);
      catCache.set(key, await res.json());
    }
    return catCache.get(key);
  }

  function stopAll() {
    Player.stop();
    if (seqStop) seqStop();
  }

  async function route() {
    stopAll();
    let m;
    if ((m = location.hash.match(/^#d(\d{2})(\d{2})$/))) {
      const cat = await loadCat(parseInt(m[1], 10)).catch(() => null);
      const dlg = cat && cat.dialogues.find((d) => d.id === `d${m[1]}${m[2]}`);
      if (dlg) { renderChat(cat, dlg); window.scrollTo(0, 0); return; }
    }
    if ((m = location.hash.match(/^#u(\d+)/))) {
      const cat = await loadCat(parseInt(m[1], 10)).catch(() => null);
      if (cat) { renderList(cat); window.scrollTo(0, 0); return; }
    }
    renderGrid();
    window.scrollTo(0, 0);
  }

  /* ---------- category grid ---------- */
  function renderGrid() {
    app.replaceChildren(
      el("div", { class: "page-head" },
        el("h1", {}, "情境對話"),
        el("p", {}, `${INDEX.total} 篇美式日常雙人對話，${INDEX.totalLines.toLocaleString()} 句逐句發音。選一個主題，跟著男女聲把對話演一遍。`)),
      el("div", { class: "card-grid" },
        ...INDEX.categories.map((c) => {
          const done = countDone(c.unit);
          const pct = Math.round((done / c.count) * 100);
          return el("button", { class: "grid-card", onclick: () => (location.hash = `#u${c.unit}`), "aria-label": c.title },
            el("div", { class: "cover" },
              el("img", { src: `images/unit${String(c.unit).padStart(2, "0")}.webp`, alt: "", loading: "lazy" })),
            el("div", { class: "body" },
              el("div", { class: "tag" }, `${c.count} 篇對話`),
              el("h3", {}, c.title),
              el("div", { class: "progress-row" },
                el("div", { class: "progress-track" }, el("div", { class: "progress-fill", style: `width:${pct}%` })),
                el("span", {}, `${done}/${c.count}`))));
        })));
  }

  function countDone(unit) {
    let n = 0;
    for (let i = 1; i <= 10; i++) if (store.has(`d${String(unit).padStart(2, "0")}${String(i).padStart(2, "0")}`)) n++;
    return n;
  }

  /* ---------- dialogue list ---------- */
  function renderList(cat) {
    app.replaceChildren(
      el("section", { class: "study" },
        el("div", { class: "study-top" },
          el("button", { class: "back-btn", onclick: () => (location.hash = "") }, "← 全部主題"),
          el("span", { class: "study-title" }, cat.title),
          el("span", { class: "study-meta" }, `${cat.dialogues.length} 篇`)),
        el("div", { class: "dlg-list" },
          ...cat.dialogues.map((d) => {
            const done = store.has(d.id);
            return el("button", { class: "dlg-item", onclick: () => (location.hash = `#${d.id}`) },
              el("div", { class: "dlg-item-main" },
                el("h3", {}, d.title, done ? el("span", { class: "badge learned", style: "margin-left:8px" }, "✓ 完成") : null),
                el("div", { class: "dlg-item-en" }, d.titleEn),
                el("p", { class: "sub" }, d.scene)),
              el("div", { class: "dlg-item-meta" },
                el("span", { class: "pill" }, `♂ ${d.m}`),
                el("span", { class: "pill" }, `♀ ${d.f}`),
                el("span", { class: "pill" }, `${d.lines.length} 句`)));
          }))));
  }

  /* ---------- chat view ---------- */
  function renderChat(cat, dlg) {
    const idx = cat.dialogues.indexOf(dlg);
    let playing = false;

    const view = el("section", { class: "study dlg-chat" });

    function audioSrc(l) { return `audio/dialog/${dlg.id}_${String(l.n).padStart(2, "0")}.mp3`; }

    function bubbleEl(l) {
      const male = l.s === "M";
      return el("div", { class: `bubble-row ${male ? "male" : "female"}`, id: `line-${l.n}` },
        el("div", { class: "bubble" },
          el("div", { class: "bubble-name" }, `${male ? "♂" : "♀"} ${male ? dlg.m : dlg.f}`),
          el("div", { class: "bubble-en", lang: "en" }, l.en),
          el("div", { class: `bubble-zh${hideZh.get() ? " hidden-zh zh" : ""}`,
            onclick: (e) => { if (hideZh.get()) e.currentTarget.classList.toggle("hidden-zh"); } }, l.zh),
          el("button", { class: "mini-play bubble-play", "aria-label": "播放這句",
            onclick: (e) => { if (seqStop) seqStop(); Player.play(audioSrc(l), e.currentTarget); } }, "▶")));
    }

    function playAll(btn) {
      if (playing) { seqStop(); return; }
      playing = true;
      btn.textContent = "⏹ 停止播放";
      btn.setAttribute("aria-pressed", "true");
      Player.stop();
      let i = 0;
      const lines = dlg.lines;
      const clear = () => {
        playing = false;
        seq.pause();
        seq.onended = null;
        seqStop = null;
        view.querySelectorAll(".bubble-row.playing").forEach((x) => x.classList.remove("playing"));
        btn.textContent = "▶ 播放整段對話";
        btn.setAttribute("aria-pressed", "false");
      };
      seqStop = clear;
      const step = () => {
        if (!playing || i >= lines.length) return clear();
        const l = lines[i];
        view.querySelectorAll(".bubble-row.playing").forEach((x) => x.classList.remove("playing"));
        const row = view.querySelector(`#line-${l.n}`);
        if (row) {
          row.classList.add("playing");
          row.scrollIntoView({ block: "center", behavior: "smooth" });
        }
        seq.src = audioSrc(l);
        seq.onended = () => { i++; setTimeout(step, 350); };
        seq.play().catch(clear);
      };
      step();
    }

    function paint() {
      const done = store.has(dlg.id);
      view.replaceChildren(
        el("div", { class: "study-top" },
          el("button", { class: "back-btn", onclick: () => (location.hash = `#u${cat.unit}`) }, `← ${cat.title}`),
          el("span", { class: "study-title" }, dlg.title),
          el("span", { class: "study-meta" }, dlg.titleEn)),
        el("p", { class: "dlg-scene" }, dlg.scene),
        el("div", { class: "study-controls" },
          el("button", { class: "toggle-btn", "aria-pressed": "false", onclick: (e) => playAll(e.currentTarget) }, "▶ 播放整段對話"),
          el("button", { class: "toggle-btn", "aria-pressed": String(hideZh.get()),
            onclick: () => { hideZh.set(!hideZh.get()); stopAll(); paint(); } }, "🙈 遮中文"),
          el("button", { class: `toggle-btn`, "aria-pressed": String(done),
            onclick: () => { store.toggle(dlg.id); paint(); } }, done ? "✓ 已完成" : "標記完成")),
        el("div", { class: "chat-area" }, ...dlg.lines.map(bubbleEl)),
        el("div", { class: "back-sec", style: "max-width:760px;margin:26px auto 0" },
          el("h4", {}, "道地用法"),
          ...dlg.phrases.map((p) => el("div", { class: "ex-item" },
            el("div", {},
              el("span", { lang: "en", style: "font-weight:700" }, p.p),
              el("span", { class: "zh-sub" }, `${p.zh}${p.note ? "｜" + p.note : ""}`))))),
        el("div", { class: "study-nav" },
          el("button", { class: "nav-btn", disabled: idx === 0 ? "" : null, "aria-label": "上一篇",
            onclick: () => (location.hash = `#${cat.dialogues[idx - 1].id}`) }, "←"),
          el("span", { class: "counter" }, `${idx + 1} / ${cat.dialogues.length}`),
          el("button", { class: "nav-btn", disabled: idx >= cat.dialogues.length - 1 ? "" : null, "aria-label": "下一篇",
            onclick: () => (location.hash = `#${cat.dialogues[idx + 1].id}`) }, "→")));
    }

    paint();
    app.replaceChildren(view);
  }

  window.addEventListener("hashchange", route);
  route();
})();

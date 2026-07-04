/* 英文聽力高頻句 — unit grid + flashcard study view (hash routing: #uNN) */
(async function () {
  const app = document.getElementById("app");
  const store = progressStore("learned:listening");
  const hideZh = boolSetting("opt:hideZh", false);
  const autoplay = boolSetting("opt:autoplay", true);

  let DATA;
  try {
    DATA = await (await fetch("data/listening.json")).json();
  } catch {
    app.innerHTML = '<div class="empty-note">資料載入失敗，請重新整理再試。</div>';
    return;
  }

  const units = DATA.units;
  const byUnit = new Map(units.map((u) => [u.unit, u]));

  function route() {
    Player.stop();
    document.onkeydown = null;
    const m = location.hash.match(/^#u(\d+)/);
    const u = m && byUnit.get(parseInt(m[1], 10));
    u ? renderStudy(u) : renderGrid();
    window.scrollTo(0, 0);
  }

  /* ---------- unit grid ---------- */
  function renderGrid() {
    app.replaceChildren(
      el("div", { class: "page-head" },
        el("h1", {}, "英文聽力高頻句"),
        el("p", {}, "美國人日常溝通的自然說法——挑一個情境開始，點卡片翻面看重點解說。")),
      el("div", { class: "card-grid" },
        ...units.map((u) => {
          const ids = u.sentences.map((s) => s.id);
          const doneN = store.count(ids);
          const pct = Math.round((doneN / ids.length) * 100);
          return el("button", { class: "grid-card", onclick: () => (location.hash = `#u${u.unit}`), "aria-label": `Unit ${u.unit} ${u.title}` },
            el("div", { class: "cover" },
              el("img", { src: `images/unit${String(u.unit).padStart(2, "0")}.webp`, alt: "", loading: "lazy" })),
            el("div", { class: "body" },
              el("div", { class: "tag" }, `UNIT ${u.unit}`),
              el("h3", {}, u.title),
              el("p", { class: "sub" }, u.scenario),
              el("div", { class: "progress-row" },
                el("div", { class: "progress-track" }, el("div", { class: "progress-fill", style: `width:${pct}%` })),
                el("span", {}, `${doneN}/${ids.length}`))));
        })));
  }

  /* ---------- study view ---------- */
  function renderStudy(unit) {
    let order = unit.sentences.map((_, i) => i);
    let shuffled = false;
    let onlyNew = false;
    let idx = 0;
    let flipped = false;

    const view = el("section", { class: "study" });

    function visible() {
      const base = shuffled ? order : unit.sentences.map((_, i) => i);
      return onlyNew ? base.filter((i) => !store.has(unit.sentences[i].id)) : base;
    }

    function current() {
      const v = visible();
      if (!v.length) return null;
      if (idx >= v.length) idx = v.length - 1;
      return unit.sentences[v[idx]];
    }

    function audioSrc(s) { return `audio/listening/${s.id}.mp3`; }

    function paint() {
      const v = visible();
      const s = current();
      view.replaceChildren(
        el("div", { class: "study-top" },
          el("button", { class: "back-btn", onclick: () => (location.hash = "") }, "← 全部單元"),
          el("span", { class: "study-title" }, `Unit ${unit.unit}｜${unit.title}`),
          el("span", { class: "study-meta" }, unit.scenario)),
        el("div", { class: "study-controls" },
          toggle("🔀 隨機", shuffled, () => { shuffled = !shuffled; if (shuffled) order = shuffleArr(order); idx = 0; flipped = false; paint(); }),
          toggle("🆕 只看未學會", onlyNew, () => { onlyNew = !onlyNew; idx = 0; flipped = false; paint(); }),
          toggle("🙈 遮中文", hideZh.get(), () => { hideZh.set(!hideZh.get()); paint(); }),
          toggle("🔊 自動發音", autoplay.get(), () => { autoplay.set(!autoplay.get()); paint(); })),
        s ? cardEl(s) : el("div", { class: "empty-note" }, "這個單元的句子都學會了 🎉（關閉「只看未學會」可全部複習）"),
        s ? navEl(v, s) : null,
        s ? el("div", { class: "kbd-hint" },
          el("kbd", {}, "←"), " ", el("kbd", {}, "→"), " 換卡　",
          el("kbd", {}, "Space"), " 翻面　",
          el("kbd", {}, "P"), " 發音　",
          el("kbd", {}, "L"), " 學會") : null);
    }

    function toggle(label, on, fn) {
      return el("button", { class: "toggle-btn", "aria-pressed": String(on), onclick: fn }, label);
    }

    function cardEl(s) {
      const learned = store.has(s.id);
      const b = s.back || {};
      const card = el("div", { class: `flashcard${flipped ? " flipped" : ""}`, role: "button", tabindex: "0",
        "aria-label": "字卡，點擊翻面",
        onclick: (e) => { if (e.target.closest(".play-btn,.mini-play,.zh")) return; flipped = !flipped; card.classList.toggle("flipped", flipped); } });

      const zh = el("div", { class: `zh${hideZh.get() ? " hidden-zh" : ""}`, title: hideZh.get() ? "點一下顯示中文" : "",
        onclick: (e) => { if (hideZh.get()) { e.stopPropagation(); e.target.classList.toggle("hidden-zh"); } } }, s.zh);

      const front = el("div", { class: "face face-front" },
        el("div", { class: "badges" },
          el("span", { class: "badge" }, `${s.n} / ${unit.sentences.length}`),
          learned ? el("span", { class: "badge learned" }, "✓ 已學會") : el("span", {})),
        el("div", { class: "en", lang: "en" }, s.en),
        zh,
        el("button", { class: "play-btn", "aria-label": "播放發音", onclick: (e) => { e.stopPropagation(); Player.play(audioSrc(s), e.currentTarget); } }, "▶"),
        el("div", { class: "flip-hint" }, "點卡片翻面看解說"));

      const backKids = [
        el("div", { class: "back-head" }, el("span", { class: "en", lang: "en" }, s.en), el("span", { class: "zh" }, s.zh)),
      ];
      if (b.grammar) backKids.push(el("div", { class: "back-sec" }, el("h4", {}, "時態與文法重點"), el("div", { class: "grammar-note" }, b.grammar)));
      if (b.variations?.length) backKids.push(el("div", { class: "back-sec" }, el("h4", {}, "美國人也會這樣說"),
        el("ul", {}, ...b.variations.map((v) => el("li", { lang: "en" }, v)))));
      if (b.keyPhrases?.length) backKids.push(el("div", { class: "back-sec" }, el("h4", {}, "關鍵片語"),
        el("div", { class: "pill-row" }, ...b.keyPhrases.map((k) => el("span", { class: "pill" }, `${k.phrase}｜${k.zh}`)))));
      if (b.extraExamples?.length) backKids.push(el("div", { class: "back-sec" }, el("h4", {}, "延伸例句"),
        ...b.extraExamples.map((x) => el("div", { class: "ex-item" },
          el("div", {}, el("span", { lang: "en" }, x.en), el("span", { class: "zh-sub" }, x.zh))))));

      const back = el("div", { class: "face face-back" }, el("div", { class: "back-scroll" }, ...backKids));

      card.append(front, back);
      return el("div", { class: "flash-wrap" }, card);
    }

    function navEl(v, s) {
      const learned = store.has(s.id);
      return el("div", { class: "study-nav" },
        el("button", { class: "nav-btn", disabled: idx === 0 ? "" : null, "aria-label": "上一張", onclick: () => move(-1) }, "←"),
        el("span", { class: "counter" }, `${idx + 1} / ${v.length}`),
        el("button", { class: `learn-btn${learned ? " is-learned" : ""}`, onclick: () => { store.toggle(s.id); paint(); } },
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
      paint();
      if (autoplay.get()) {
        const s = current();
        if (s) Player.play(`audio/listening/${s.id}.mp3`, view.querySelector(".play-btn"));
      }
    }

    view.addEventListener("keydown", onKey);
    function onKey(e) {
      if (e.target.matches("input,textarea")) return;
      if (e.key === "ArrowLeft") { e.preventDefault(); move(-1); }
      else if (e.key === "ArrowRight") { e.preventDefault(); move(1); }
      else if (e.key === " ") { e.preventDefault(); const c = view.querySelector(".flashcard"); if (c) { flipped = !flipped; c.classList.toggle("flipped", flipped); } }
      else if (e.key.toLowerCase() === "p") { const s = current(); if (s) Player.play(`audio/listening/${s.id}.mp3`, view.querySelector(".play-btn")); }
      else if (e.key.toLowerCase() === "l") { const s = current(); if (s) { store.toggle(s.id); paint(); } }
    }
    document.onkeydown = onKey;

    paint();
    app.replaceChildren(view);
  }

  window.addEventListener("hashchange", route);
  route();
})();

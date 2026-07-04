/* Shared: theme toggle, audio player, progress store */
(function () {
  const saved = localStorage.getItem("theme");
  const dark = saved ? saved === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
  document.documentElement.dataset.theme = dark ? "dark" : "light";
})();

const Theme = {
  toggle() {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    localStorage.setItem("theme", next);
    Theme.paint();
  },
  paint() {
    const btn = document.getElementById("themeBtn");
    if (btn) btn.textContent = document.documentElement.dataset.theme === "dark" ? "☀️" : "🌙";
  },
  init() {
    const btn = document.getElementById("themeBtn");
    if (btn) btn.addEventListener("click", Theme.toggle);
    Theme.paint();
  },
};

/* Single shared audio element; resolves button states */
const Player = {
  audio: new Audio(),
  current: null,
  play(src, btn) {
    if (Player.current) Player.current.classList.remove("playing");
    if (!Player.audio.paused && Player.audio.src.endsWith(src)) {
      Player.audio.pause();
      Player.current = null;
      return;
    }
    Player.audio.src = src;
    Player.current = btn || null;
    if (btn) btn.classList.add("playing");
    Player.audio.play().catch(() => {
      if (btn) btn.classList.remove("playing");
    });
  },
  stop() {
    Player.audio.pause();
    if (Player.current) Player.current.classList.remove("playing");
    Player.current = null;
  },
};
Player.audio.addEventListener("ended", () => {
  if (Player.current) Player.current.classList.remove("playing");
  Player.current = null;
});

/* learned-card store, key per feature */
function progressStore(key) {
  let set;
  try { set = new Set(JSON.parse(localStorage.getItem(key) || "[]")); }
  catch { set = new Set(); }
  return {
    has: (id) => set.has(id),
    toggle(id) {
      set.has(id) ? set.delete(id) : set.add(id);
      localStorage.setItem(key, JSON.stringify([...set]));
      return set.has(id);
    },
    count: (ids) => ids.reduce((n, id) => n + (set.has(id) ? 1 : 0), 0),
  };
}

/* boolean setting helper */
function boolSetting(key, dflt) {
  return {
    get: () => {
      const v = localStorage.getItem(key);
      return v === null ? dflt : v === "1";
    },
    set: (v) => localStorage.setItem(key, v ? "1" : "0"),
  };
}

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null) continue;
    if (k === "class") node.className = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else if (k === "html") node.innerHTML = v;
    else node.setAttribute(k, v);
  }
  for (const c of children) {
    if (c == null) continue;
    node.append(c.nodeType ? c : document.createTextNode(c));
  }
  return node;
}

function shuffleArr(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

document.addEventListener("DOMContentLoaded", Theme.init);

const STORIES_JSON = "../annotations/stories.json";
const WIKISOURCE_JSON = "../annotations/wikisource_urls.json";

const $ = (sel) => document.querySelector(sel);

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function titleizeKey(s) {
  return String(s)
    .replace(/^theme_/, "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (m) => m.toUpperCase());
}

function stableSort(arr, compare) {
  return arr
    .map((v, i) => ({ v, i }))
    .sort((a, b) => {
      const c = compare(a.v, b.v);
      return c !== 0 ? c : a.i - b.i;
    })
    .map((x) => x.v);
}

function compareValues(a, b) {
  if (a == null && b == null) return 0;
  if (a == null) return -1;
  if (b == null) return 1;
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: "base" });
}

function uniqSorted(values) {
  return [...new Set(values.filter((v) => v != null))].sort((a, b) => compareValues(a, b));
}

async function fetchJson(url) {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load ${url}: ${res.status} ${res.statusText}`);
  return res.json();
}

function buildColumns() {
  return [
    { key: "index", label: "#", sortable: true },
    { key: "title", label: "Title", sortable: true },
    { key: "rating_story", label: "Rating", sortable: true },
    { key: "tone", label: "Tone", sortable: true },
    { key: "setting", label: "Setting", sortable: true },
    { key: "ending_type", label: "Ending", sortable: true },
    { key: "darkness_level", label: "Dark", sortable: true },
    { key: "body_count", label: "Bodies", sortable: true },
    { key: "central_mechanism", label: "Mechanism", sortable: true },
    { key: "protagonist_type", label: "Protagonist", sortable: true },
    { key: "agency_driver", label: "Agency", sortable: true },
    { key: "wikisource", label: "Wikisource", sortable: false },
    { key: "local", label: "Local XHTML", sortable: false },
  ];
}

function buildSortOptions(columns) {
  const opt = [];
  for (const c of columns) {
    if (!c.sortable) continue;
    opt.push({ key: c.key, label: c.label });
  }
  return opt;
}

function buildThemeKeys(stories) {
  const keys = Object.keys(stories[0] ?? {}).filter((k) => k.startsWith("theme_"));
  keys.sort((a, b) => a.localeCompare(b));
  return keys;
}

function getBadgeClassForRating(r) {
  if (r >= 4) return "badge badge--good";
  if (r <= 2) return "badge badge--bad";
  return "badge";
}

function renderCell(story, key) {
  switch (key) {
    case "title": {
      const t = escapeHtml(story.title);
      const tooltip = story.notes ? escapeHtml(story.notes) : "";
      return `<span title="${tooltip}">${t}</span>`;
    }
    case "rating_story": {
      const r = story.rating_story ?? "";
      return `<span class="${getBadgeClassForRating(Number(r))}">${escapeHtml(r)}</span>`;
    }
    case "darkness_level": {
      return `<span class="badge">${escapeHtml(story.darkness_level)}</span>`;
    }
    case "body_count": {
      return story.body_count ? `<span class="badge badge--bad">${escapeHtml(story.body_count)}</span>` : `<span class="badge">0</span>`;
    }
    case "wikisource": {
      if (!story.wikisource_url) return `<span class="cell-muted">—</span>`;
      return `<a href="${escapeHtml(story.wikisource_url)}" target="_blank" rel="noreferrer">link</a>`;
    }
    case "local": {
      const href = `../src/epub/${story.href}`;
      return `<a href="${escapeHtml(href)}" target="_blank" rel="noreferrer">open</a>`;
    }
    default: {
      const v = story[key];
      if (Array.isArray(v)) {
        if (v.length === 0) return `<span class="cell-muted">—</span>`;
        return v.map((x) => `<span class="badge">${escapeHtml(x)}</span>`).join(" ");
      }
      if (v === "" || v == null) return `<span class="cell-muted">—</span>`;
      return `<span class="badge">${escapeHtml(v)}</span>`;
    }
  }
}

function buildFilterGroup(title, options) {
  const wrap = document.createElement("section");
  wrap.className = "filterGroup";
  const h = document.createElement("h3");
  h.className = "filterGroup__title";
  h.textContent = title;
  const body = document.createElement("div");
  body.className = "filterGroup__body";
  for (const opt of options) body.appendChild(opt);
  wrap.appendChild(h);
  wrap.appendChild(body);
  return wrap;
}

function checkboxOption({ id, label, value, count, onChange }) {
  const row = document.createElement("div");
  row.className = "opt";

  const lab = document.createElement("label");
  const input = document.createElement("input");
  input.type = "checkbox";
  input.id = id;
  input.value = value;
  input.addEventListener("change", () => onChange(input.checked, value));
  const txt = document.createElement("span");
  txt.textContent = label;
  lab.appendChild(input);
  lab.appendChild(txt);

  const c = document.createElement("code");
  c.textContent = String(count);

  row.appendChild(lab);
  row.appendChild(c);
  return row;
}

function buildFiltersUI({ stories, themeKeys, state, onStateChange }) {
  const container = $("#filters");
  container.innerHTML = "";

  const fields = [
    { key: "tone", label: "Tone" },
    { key: "setting", label: "Setting" },
    { key: "ending_type", label: "Ending type" },
    { key: "central_mechanism", label: "Central mechanism" },
    { key: "protagonist_type", label: "Protagonist type" },
    { key: "agency_driver", label: "Agency driver" },
  ];

  for (const f of fields) {
    const vals = uniqSorted(stories.map((s) => s[f.key]));
    const options = vals.map((v) =>
      checkboxOption({
        id: `f_${f.key}_${v}`,
        label: v,
        value: v,
        count: stories.filter((s) => s[f.key] === v).length,
        onChange: (checked, value) => {
          if (checked) state[f.key].add(value);
          else state[f.key].delete(value);
          onStateChange();
        },
      }),
    );
    container.appendChild(buildFilterGroup(f.label, options));
  }

  const socialTargets = uniqSorted(stories.flatMap((s) => s.social_target ?? []));
  container.appendChild(
    buildFilterGroup(
      "Social target",
      socialTargets.map((v) =>
        checkboxOption({
          id: `f_social_${v}`,
          label: v,
          value: v,
          count: stories.filter((s) => (s.social_target ?? []).includes(v)).length,
          onChange: (checked, value) => {
            if (checked) state.social_target.add(value);
            else state.social_target.delete(value);
            onStateChange();
          },
        }),
      ),
    ),
  );

  const constraints = uniqSorted(stories.flatMap((s) => s.constraint_pressure ?? []));
  container.appendChild(
    buildFilterGroup(
      "Constraint pressure",
      constraints.map((v) =>
        checkboxOption({
          id: `f_constraint_${v}`,
          label: v,
          value: v,
          count: stories.filter((s) => (s.constraint_pressure ?? []).includes(v)).length,
          onChange: (checked, value) => {
            if (checked) state.constraint_pressure.add(value);
            else state.constraint_pressure.delete(value);
            onStateChange();
          },
        }),
      ),
    ),
  );

  // Themes: “must be true”
  container.appendChild(
    buildFilterGroup(
      "Themes (must be true)",
      themeKeys.map((k) =>
        checkboxOption({
          id: `f_theme_${k}`,
          label: titleizeKey(k),
          value: k,
          count: stories.filter((s) => s[k] === true).length,
          onChange: (checked, value) => {
            if (checked) state.themesRequired.add(value);
            else state.themesRequired.delete(value);
            onStateChange();
          },
        }),
      ),
    ),
  );

  // Wikisource availability
  const wsOptions = [
    { v: "any", label: "Any" },
    { v: "yes", label: "Has Wikisource link" },
    { v: "no", label: "Missing Wikisource link" },
  ];
  container.appendChild(
    buildFilterGroup(
      "Wikisource",
      wsOptions.map(({ v, label }) => {
        const row = document.createElement("div");
        row.className = "opt";
        const lab = document.createElement("label");
        const input = document.createElement("input");
        input.type = "radio";
        input.name = "wikisource";
        input.value = v;
        input.checked = state.wikisource === v;
        input.addEventListener("change", () => {
          state.wikisource = v;
          onStateChange();
        });
        const txt = document.createElement("span");
        txt.textContent = label;
        lab.appendChild(input);
        lab.appendChild(txt);
        const c = document.createElement("code");
        if (v === "any") c.textContent = String(stories.length);
        else if (v === "yes") c.textContent = String(stories.filter((s) => Boolean(s.wikisource_url)).length);
        else c.textContent = String(stories.filter((s) => !s.wikisource_url).length);
        row.appendChild(lab);
        row.appendChild(c);
        return row;
      }),
    ),
  );
}

function storyMatchesSetFilter(story, field, set) {
  if (set.size === 0) return true;
  return set.has(story[field]);
}

function storyMatchesArrayFilter(story, field, set) {
  if (set.size === 0) return true;
  const arr = story[field] ?? [];
  return [...set].some((v) => arr.includes(v));
}

function applyFilters(stories, state) {
  const q = state.search.trim().toLowerCase();
  return stories.filter((s) => {
    if (s.rating_story < state.minRating) return false;
    if (s.darkness_level > state.maxDarkness) return false;

    if (q) {
      const hay = `${s.title}\n${s.notes ?? ""}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }

    if (!storyMatchesSetFilter(s, "tone", state.tone)) return false;
    if (!storyMatchesSetFilter(s, "setting", state.setting)) return false;
    if (!storyMatchesSetFilter(s, "ending_type", state.ending_type)) return false;
    if (!storyMatchesSetFilter(s, "central_mechanism", state.central_mechanism)) return false;
    if (!storyMatchesSetFilter(s, "protagonist_type", state.protagonist_type)) return false;
    if (!storyMatchesSetFilter(s, "agency_driver", state.agency_driver)) return false;

    if (!storyMatchesArrayFilter(s, "social_target", state.social_target)) return false;
    if (!storyMatchesArrayFilter(s, "constraint_pressure", state.constraint_pressure)) return false;

    for (const k of state.themesRequired) {
      if (s[k] !== true) return false;
    }

    if (state.wikisource === "yes" && !s.wikisource_url) return false;
    if (state.wikisource === "no" && s.wikisource_url) return false;

    return true;
  });
}

function applySort(stories, state) {
  const dir = state.sortDir === "desc" ? -1 : 1;
  const key = state.sortKey;
  return stableSort(stories, (a, b) => {
    let av = a[key];
    let bv = b[key];
    if (Array.isArray(av)) av = av.join(", ");
    if (Array.isArray(bv)) bv = bv.join(", ");
    const c = compareValues(av, bv) * dir;
    return c !== 0 ? c : compareValues(a.index, b.index);
  });
}

function renderTable({ stories, columns, state }) {
  const thead = $("#tableHead");
  const tbody = $("#tableBody");

  // header
  const trh = document.createElement("tr");
  for (const col of columns) {
    const th = document.createElement("th");
    if (col.sortable) {
      const btn = document.createElement("button");
      btn.type = "button";
      const arrow = state.sortKey === col.key ? (state.sortDir === "desc" ? " ↓" : " ↑") : "";
      btn.textContent = `${col.label}${arrow}`;
      btn.addEventListener("click", () => {
        if (state.sortKey === col.key) state.sortDir = state.sortDir === "desc" ? "asc" : "desc";
        else {
          state.sortKey = col.key;
          state.sortDir = col.key === "rating_story" ? "desc" : "asc";
        }
        syncSortControls(state);
        renderAll();
      });
      th.appendChild(btn);
    } else {
      th.textContent = col.label;
    }
    trh.appendChild(th);
  }
  thead.innerHTML = "";
  thead.appendChild(trh);

  // body
  tbody.innerHTML = stories
    .map((s) => {
      const tds = columns.map((c) => `<td>${renderCell(s, c.key)}</td>`).join("");
      return `<tr>${tds}</tr>`;
    })
    .join("");
}

function syncSortControls(state) {
  const sortKey = $("#sortKey");
  sortKey.value = state.sortKey;
  $("#sortDir").textContent = state.sortDir === "desc" ? "↓" : "↑";
}

let ALL_STORIES = [];
let COLUMNS = [];
let THEME_KEYS = [];

const state = {
  search: "",
  minRating: 1,
  maxDarkness: 5,
  sortKey: "rating_story",
  sortDir: "desc",
  tone: new Set(),
  setting: new Set(),
  ending_type: new Set(),
  central_mechanism: new Set(),
  protagonist_type: new Set(),
  agency_driver: new Set(),
  social_target: new Set(),
  constraint_pressure: new Set(),
  themesRequired: new Set(),
  wikisource: "any",
};

function resetState() {
  state.search = "";
  state.minRating = 1;
  state.maxDarkness = 5;
  state.sortKey = "rating_story";
  state.sortDir = "desc";
  for (const k of [
    "tone",
    "setting",
    "ending_type",
    "central_mechanism",
    "protagonist_type",
    "agency_driver",
    "social_target",
    "constraint_pressure",
    "themesRequired",
  ]) {
    state[k].clear();
  }
  state.wikisource = "any";
}

function renderAll() {
  const filtered = applyFilters(ALL_STORIES, state);
  const sorted = applySort(filtered, state);
  $("#status").textContent = `${sorted.length} / ${ALL_STORIES.length} stories`;
  renderTable({ stories: sorted, columns: COLUMNS, state });
}

async function main() {
  const [stories, wikisource] = await Promise.allSettled([fetchJson(STORIES_JSON), fetchJson(WIKISOURCE_JSON)]);

  if (stories.status !== "fulfilled") {
    $("#status").textContent = `Error: ${stories.reason?.message ?? stories.reason}`;
    return;
  }

  const wsByIndex = new Map();
  if (wikisource.status === "fulfilled") {
    for (const row of wikisource.value) wsByIndex.set(row.index, row);
  }

  ALL_STORIES = stories.value.map((s) => {
    const ws = wsByIndex.get(s.index);
    return {
      ...s,
      wikisource_url: ws?.wikisource_url ?? null,
      wikisource_title: ws?.wikisource_title ?? null,
    };
  });

  COLUMNS = buildColumns();
  THEME_KEYS = buildThemeKeys(ALL_STORIES);

  // sort dropdown
  const sortKey = $("#sortKey");
  sortKey.innerHTML = "";
  for (const opt of buildSortOptions(COLUMNS)) {
    const o = document.createElement("option");
    o.value = opt.key;
    o.textContent = opt.label;
    sortKey.appendChild(o);
  }
  sortKey.value = state.sortKey;

  // wire top controls
  $("#search").addEventListener("input", (e) => {
    state.search = e.target.value ?? "";
    renderAll();
  });
  $("#minRating").addEventListener("change", (e) => {
    state.minRating = Number(e.target.value ?? 1);
    renderAll();
  });
  $("#maxDarkness").addEventListener("change", (e) => {
    state.maxDarkness = Number(e.target.value ?? 5);
    renderAll();
  });
  $("#sortKey").addEventListener("change", (e) => {
    state.sortKey = e.target.value;
    renderAll();
  });
  $("#sortDir").addEventListener("click", () => {
    state.sortDir = state.sortDir === "desc" ? "asc" : "desc";
    syncSortControls(state);
    renderAll();
  });
  $("#reset").addEventListener("click", () => {
    resetState();
    $("#search").value = "";
    $("#minRating").value = String(state.minRating);
    $("#maxDarkness").value = String(state.maxDarkness);
    syncSortControls(state);
    buildFiltersUI({
      stories: ALL_STORIES,
      themeKeys: THEME_KEYS,
      state,
      onStateChange: renderAll,
    });
    renderAll();
  });

  syncSortControls(state);

  buildFiltersUI({
    stories: ALL_STORIES,
    themeKeys: THEME_KEYS,
    state,
    onStateChange: renderAll,
  });

  renderAll();
}

main().catch((err) => {
  $("#status").textContent = `Error: ${err?.message ?? String(err)}`;
});


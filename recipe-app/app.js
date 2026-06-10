// ============================================================
// Peebs Weekly Menu — app logic
// Views: week planner, recipe detail, shopping list, all recipes.
// Persisted in localStorage on this device:
//   - the weekly plan and week preferences (style/calories/time)
//   - shopping-list checkmarks
//   - favorite recipes
//   - reviews (taste + quick/easy ratings, notes)
//   - allergy exclusions (recipes containing excluded allergens are
//     hidden from shuffle, the swap picker, and All Recipes)
// ============================================================

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const STORAGE_KEY = "weekly-menu-plan-v1";
const CHECKS_KEY = "weekly-menu-checks-v1";
const FAVS_KEY = "weekly-menu-favs-v1";
const REVIEWS_KEY = "weekly-menu-reviews-v1";
const ALLERGY_KEY = "weekly-menu-allergies-v1";
const SORT_KEY = "weekly-menu-sort-v1";
const PREFS_KEY = "weekly-menu-prefs-v1";

const app = document.getElementById("app");

// ---------- Icons ----------
const ICON_DICE = `<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="2.5" y="2.5" width="19" height="19" rx="4.5" fill="none" stroke="currentColor" stroke-width="1.8"/><circle cx="8" cy="8" r="1.6" fill="currentColor"/><circle cx="16" cy="8" r="1.6" fill="currentColor"/><circle cx="12" cy="12" r="1.6" fill="currentColor"/><circle cx="8" cy="16" r="1.6" fill="currentColor"/><circle cx="16" cy="16" r="1.6" fill="currentColor"/></svg>`;
const ICON_HEART = `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.18L12 21z"/></svg>`;
const ICON_EXT = `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 17L17 7M9 7h8v8" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

// ---------- Publix link helper ----------
function publixUrl(term) {
  return "https://www.publix.com/search?searchTerm=" + encodeURIComponent(term);
}
function publixLink(term, label) {
  return `<a class="publix-link" href="${publixUrl(term)}" target="_blank" rel="noopener">${label}${ICON_EXT}</a>`;
}

// ---------- Persistence helpers ----------
function loadJSON(key, fallback) {
  try {
    const v = JSON.parse(localStorage.getItem(key));
    return v === null || v === undefined ? fallback : v;
  } catch (e) {
    return fallback;
  }
}
const saveJSON = (key, v) => localStorage.setItem(key, JSON.stringify(v));

// ---------- State ----------
let favorites = loadJSON(FAVS_KEY, {});            // { recipeId: true }
let reviews = loadJSON(REVIEWS_KEY, {});           // { recipeId: { taste, ease, note } }
// Allergens we're avoiding. Defaults to the house allergies —
// shellfish and nuts — change anytime with the chips on All Recipes.
let excludedAllergens = loadJSON(ALLERGY_KEY, ["shellfish", "nuts"]);
let sortMode = loadJSON(SORT_KEY, "quickest");
let checks = loadJSON(CHECKS_KEY, {});
// Week preferences: style = any|healthy|balanced|indulgent,
// maxCal / maxTime = 0 means no limit.
let prefs = loadJSON(PREFS_KEY, { style: "any", maxCal: 0, maxTime: 0 });

const recipeById = (id) => RECIPES.find((r) => r.id === id);
const isSafe = (r) => !r.allergens.some((a) => excludedAllergens.includes(a));
const safeRecipes = () => RECIPES.filter(isSafe);
const getReview = (id) => reviews[id] || null;

// Recipes matching both allergies and week preferences.
function eligibleRecipes() {
  return safeRecipes().filter((r) =>
    (prefs.style === "any" || r.health === prefs.style) &&
    (!prefs.maxCal || r.calories <= prefs.maxCal) &&
    (!prefs.maxTime || r.time <= prefs.maxTime)
  );
}

function loadPlan() {
  const saved = loadJSON(STORAGE_KEY, null);
  if (Array.isArray(saved) && saved.length === 7 &&
      saved.every((id) => id === null || RECIPES.some((r) => r.id === id))) {
    return saved;
  }
  return shuffledPlan();
}

function shuffledPlan() {
  const ids = eligibleRecipes().map((r) => r.id);
  for (let i = ids.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [ids[i], ids[j]] = [ids[j], ids[i]];
  }
  const week = ids.slice(0, 7);
  while (week.length < 7) week.push(null);
  return week;
}

let plan = loadPlan();
const savePlan = () => saveJSON(STORAGE_KEY, plan);
savePlan();

// getDay(): Sunday=0 ... Saturday=6 → our Monday-first index
function todayIndex() {
  return (new Date().getDay() + 6) % 7;
}

// ---------- Small render helpers ----------
function starsDisplay(n) {
  return "★".repeat(n) + "☆".repeat(5 - n);
}

function ratingSummary(id) {
  const rev = getReview(id);
  if (!rev) return "";
  const parts = [];
  if (rev.taste) parts.push(`<span class="rating-chip" title="How much we liked it">Taste <b>${starsDisplay(rev.taste)}</b></span>`);
  if (rev.ease) parts.push(`<span class="rating-chip" title="Quick and easy to make">Ease <b>${starsDisplay(rev.ease)}</b></span>`);
  return parts.join("");
}

function healthPill(r) {
  return `<span class="health-pill ${r.health}">${HEALTH_LEVELS[r.health].label}</span>`;
}

function mealMeta(r) {
  return `${r.time} min · ${r.calories} cal`;
}

function favHeart(id, extraClass = "") {
  const fav = !!favorites[id];
  return `<button class="fav-btn ${fav ? "faved" : ""} ${extraClass}" data-fav="${id}"
    title="${fav ? "Remove from favorites" : "Save to favorites"}"
    aria-label="${fav ? "Remove from favorites" : "Save to favorites"}">${ICON_HEART}</button>`;
}

function wireFavButtons(rerender) {
  app.querySelectorAll("[data-fav]").forEach((b) => {
    b.addEventListener("click", (e) => {
      e.stopPropagation();
      const id = b.dataset.fav;
      if (favorites[id]) delete favorites[id];
      else favorites[id] = true;
      saveJSON(FAVS_KEY, favorites);
      rerender();
    });
  });
}

// ---------- Routing ----------
let currentView = { name: "week" };

function navigate(view) {
  currentView = view;
  document.querySelectorAll(".nav-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.view === view.name);
  });
  render();
  window.scrollTo({ top: 0 });
}

document.querySelectorAll(".nav-btn").forEach((b) => {
  b.addEventListener("click", () => navigate({ name: b.dataset.view }));
});
document.getElementById("logo-home").addEventListener("click", () => navigate({ name: "week" }));

function render() {
  switch (currentView.name) {
    case "week":   renderWeek(); break;
    case "recipe": renderRecipe(currentView.id, currentView.from); break;
    case "list":   renderShoppingList(); break;
    case "all":    renderAllRecipes(); break;
  }
}

// ---------- Week view ----------
const STYLE_OPTIONS = [
  { value: "any", label: "Anything goes" },
  { value: "healthy", label: "Healthy" },
  { value: "balanced", label: "Balanced" },
  { value: "indulgent", label: "Gnommy" },
];
const CAL_OPTIONS = [
  { value: 0, label: "No limit" },
  { value: 500, label: "Under 500 cal" },
  { value: 650, label: "Under 650 cal" },
  { value: 800, label: "Under 800 cal" },
];
const TIME_OPTIONS = [
  { value: 0, label: "No limit" },
  { value: 25, label: "25 min or less" },
  { value: 35, label: "35 min or less" },
];

function renderWeek() {
  const today = todayIndex();
  const matchCount = eligibleRecipes().length;
  app.innerHTML = `
    <div class="view-header">
      <h2>This Week</h2>
      <button class="btn dice-btn" id="shuffle-week" title="Shuffle the week">${ICON_DICE}Shuffle Week</button>
    </div>
    <p class="view-sub">Set your preferences and the whole week adjusts. Tap a meal for the recipe and Publix links, or swap any single night.</p>

    <div class="prefs-bar">
      <div class="pref-field">
        <span class="pref-label">Style</span>
        <select class="pref-select" id="pref-style">
          ${STYLE_OPTIONS.map((o) => `<option value="${o.value}" ${prefs.style === o.value ? "selected" : ""}>${o.label}</option>`).join("")}
        </select>
      </div>
      <div class="pref-field">
        <span class="pref-label">Calories</span>
        <select class="pref-select" id="pref-cal">
          ${CAL_OPTIONS.map((o) => `<option value="${o.value}" ${prefs.maxCal === o.value ? "selected" : ""}>${o.label}</option>`).join("")}
        </select>
      </div>
      <div class="pref-field">
        <span class="pref-label">Cook time</span>
        <select class="pref-select" id="pref-time">
          ${TIME_OPTIONS.map((o) => `<option value="${o.value}" ${prefs.maxTime === o.value ? "selected" : ""}>${o.label}</option>`).join("")}
        </select>
      </div>
      <span class="prefs-meta">${matchCount} of ${RECIPES.length} recipes match</span>
    </div>

    <div class="week-grid">
      ${DAYS.map((day, i) => {
        const r = recipeById(plan[i]);
        const unsafe = r && !isSafe(r);
        return `
        <div class="day-card">
          <div class="day-label ${i === today ? "today" : ""}">
            <span>${day}</span>
            ${i === today ? '<span class="today-pill">Tonight</span>' : ""}
          </div>
          <div class="day-body">
            ${r ? `
              <button class="meal-link" data-recipe="${r.id}">
                ${healthPill(r)}
                <span class="meal-name">${r.name}</span>
                <span class="meal-meta">${mealMeta(r)}</span>
              </button>
              ${ratingSummary(r.id) ? `<div class="rating-row">${ratingSummary(r.id)}</div>` : ""}
              ${unsafe ? `<p class="allergy-warning">Contains ${r.allergens.filter((a) => excludedAllergens.includes(a)).map((a) => ALLERGENS[a].toLowerCase()).join(", ")} — swap this one</p>` : ""}` : `
              <p class="meal-meta">Nothing planned — date night out?</p>`}
            <div class="day-actions">
              <button class="btn small secondary" data-swap="${i}">Swap</button>
              ${r ? `<button class="btn small secondary" data-clear="${i}">Clear</button>` : ""}
            </div>
          </div>
        </div>`;
      }).join("")}
    </div>`;

  const diceBtn = document.getElementById("shuffle-week");
  diceBtn.addEventListener("click", () => {
    if (diceBtn.classList.contains("shaking")) return;
    diceBtn.classList.add("shaking");
    setTimeout(() => {
      plan = shuffledPlan();
      savePlan();
      renderWeek();
    }, 550);
  });

  // Changing any preference regenerates the week immediately.
  const onPrefChange = () => {
    prefs = {
      style: document.getElementById("pref-style").value,
      maxCal: Number(document.getElementById("pref-cal").value),
      maxTime: Number(document.getElementById("pref-time").value),
    };
    saveJSON(PREFS_KEY, prefs);
    plan = shuffledPlan();
    savePlan();
    renderWeek();
  };
  ["pref-style", "pref-cal", "pref-time"].forEach((id) => {
    document.getElementById(id).addEventListener("change", onPrefChange);
  });

  wireRecipeLinks("week");
  app.querySelectorAll("[data-swap]").forEach((b) => {
    b.addEventListener("click", () => openSwapPicker(Number(b.dataset.swap)));
  });
  app.querySelectorAll("[data-clear]").forEach((b) => {
    b.addEventListener("click", () => {
      plan[Number(b.dataset.clear)] = null;
      savePlan();
      renderWeek();
    });
  });
}

function wireRecipeLinks(from) {
  app.querySelectorAll("[data-recipe]").forEach((el) => {
    el.addEventListener("click", () => navigate({ name: "recipe", id: el.dataset.recipe, from }));
  });
}

// ---------- Swap picker ----------
function openSwapPicker(dayIndex) {
  // Favorites first, then top-rated taste, then quickest.
  const choices = eligibleRecipes().sort((a, b) => {
    const favDiff = (favorites[b.id] ? 1 : 0) - (favorites[a.id] ? 1 : 0);
    if (favDiff) return favDiff;
    const tasteDiff = ((getReview(b.id) || {}).taste || 0) - ((getReview(a.id) || {}).taste || 0);
    if (tasteDiff) return tasteDiff;
    return a.time - b.time;
  });
  const backdrop = document.createElement("div");
  backdrop.className = "modal-backdrop";
  backdrop.innerHTML = `
    <div class="modal">
      <h3>Pick a meal for ${DAYS[dayIndex]}</h3>
      <p class="view-sub">Favorites and top-rated meals first. Allergy and preference filters apply.</p>
      <ul class="picker-list">
        ${choices.map((r) => `
          <li><button class="picker-item" data-pick="${r.id}">
            <span class="tag-row">${healthPill(r)}${favorites[r.id] ? '<span class="rating-chip">Favorite</span>' : ""}</span>
            <strong>${r.name}</strong>
            <span class="meal-meta">${mealMeta(r)} · ${r.tags.join(" · ")}</span>
            ${ratingSummary(r.id) ? `<span class="rating-row">${ratingSummary(r.id)}</span>` : ""}
          </button></li>`).join("")}
      </ul>
    </div>`;
  backdrop.addEventListener("click", (e) => {
    if (e.target === backdrop) backdrop.remove();
  });
  backdrop.querySelectorAll("[data-pick]").forEach((b) => {
    b.addEventListener("click", () => {
      plan[dayIndex] = b.dataset.pick;
      savePlan();
      backdrop.remove();
      renderWeek();
    });
  });
  document.body.appendChild(backdrop);
}

// ---------- Recipe detail ----------
function renderRecipe(id, from = "week") {
  const r = recipeById(id);
  if (!r) { navigate({ name: "week" }); return; }
  const backLabel = from === "all" ? "← All Recipes" : "← This Week";
  const rev = getReview(id) || { taste: 0, ease: 0, note: "" };
  const containsHtml = r.allergens.length
    ? `Contains: ${r.allergens.map((a) => excludedAllergens.includes(a)
        ? `<span class="danger">${ALLERGENS[a]}</span>` : ALLERGENS[a]).join(", ")}`
    : "No common allergens";

  app.innerHTML = `
    <button class="back-link" id="back">${backLabel}</button>
    <div class="detail-card">
      <div class="detail-head">
        <div class="detail-title">
          <div class="tag-row">${healthPill(r)}${r.tags.map((t) => `<span class="tag">${t}</span>`).join("")}</div>
          <h2>${r.name}</h2>
        </div>
        ${favHeart(id, "big")}
      </div>
      <p class="detail-meta">${r.time} minutes · Serves 2 · ${r.calories} calories per serving</p>
      <p class="contains-note">${containsHtml}</p>
      <div class="detail-cols">
        <div>
          <h3>Ingredients</h3>
          <ul class="ing-list">
            ${r.ingredients.map((ing) => `
              <li class="ing-row">
                <span class="ing-info">
                  <span class="ing-name">${ing.item}</span>
                  <span class="ing-amount">${ing.amount}</span>
                  <span class="ing-dept">${ing.dept}</span>
                </span>
                ${publixLink(ing.search || ing.item, "Find at Publix")}
              </li>`).join("")}
          </ul>
        </div>
        <div>
          <h3>Steps</h3>
          <ol class="steps-list">
            ${r.steps.map((s) => `<li>${s}</li>`).join("")}
          </ol>
        </div>
      </div>

      <div class="review-box" id="review-box">
        <h3>Our Review</h3>
        <div class="review-row">
          <span class="review-label">How much we liked it</span>
          <span class="star-input" data-field="taste">
            ${[1, 2, 3, 4, 5].map((n) => `<button class="star ${rev.taste >= n ? "filled" : ""}" data-val="${n}">★</button>`).join("")}
          </span>
        </div>
        <div class="review-row">
          <span class="review-label">Quick &amp; easy to make</span>
          <span class="star-input" data-field="ease">
            ${[1, 2, 3, 4, 5].map((n) => `<button class="star ${rev.ease >= n ? "filled" : ""}" data-val="${n}">★</button>`).join("")}
          </span>
        </div>
        <textarea class="review-note" id="review-note" rows="2"
          placeholder="Notes for next time (e.g., 'double the garlic', 'took closer to 45 min')...">${rev.note || ""}</textarea>
        <div class="review-actions">
          <button class="btn" id="save-review">Save Review</button>
          <span class="save-confirm" id="save-confirm" hidden>Saved</span>
        </div>
      </div>
    </div>`;

  document.getElementById("back").addEventListener("click", () => navigate({ name: from === "all" ? "all" : "week" }));
  wireFavButtons(() => renderRecipe(id, from));

  // Star inputs update a draft; Save persists it.
  const draft = { taste: rev.taste, ease: rev.ease };
  app.querySelectorAll(".star-input").forEach((group) => {
    const field = group.dataset.field;
    group.querySelectorAll(".star").forEach((star) => {
      star.addEventListener("click", () => {
        draft[field] = Number(star.dataset.val);
        group.querySelectorAll(".star").forEach((s) => {
          s.classList.toggle("filled", Number(s.dataset.val) <= draft[field]);
        });
      });
    });
  });
  document.getElementById("save-review").addEventListener("click", () => {
    reviews[id] = { ...draft, note: document.getElementById("review-note").value.trim() };
    saveJSON(REVIEWS_KEY, reviews);
    const confirm = document.getElementById("save-confirm");
    confirm.hidden = false;
    setTimeout(() => { confirm.hidden = true; }, 2000);
  });
}

// ---------- Shopping list ----------
function buildShoppingList() {
  // Merge duplicate ingredients across the week's recipes,
  // keyed by item name, collecting each recipe's amount.
  const merged = new Map();
  plan.forEach((id) => {
    const r = recipeById(id);
    if (!r) return;
    r.ingredients.forEach((ing) => {
      const key = ing.item.toLowerCase();
      if (!merged.has(key)) {
        merged.set(key, { ...ing, amounts: [], recipes: [] });
      }
      const entry = merged.get(key);
      entry.amounts.push(ing.amount);
      entry.recipes.push(r.name);
    });
  });

  // Group by department, ordered by walk-order.
  const byDept = new Map();
  [...merged.values()].forEach((entry) => {
    if (!byDept.has(entry.dept)) byDept.set(entry.dept, []);
    byDept.get(entry.dept).push(entry);
  });
  return [...byDept.entries()].sort(
    (a, b) => DEPARTMENTS[a[0]].order - DEPARTMENTS[b[0]].order
  );
}

function renderShoppingList() {
  const groups = buildShoppingList();
  const plannedCount = plan.filter(Boolean).length;

  if (plannedCount === 0) {
    app.innerHTML = `
      <div class="view-header"><h2>Shopping List</h2></div>
      <div class="empty-note">No meals planned yet — head to <strong>This Week</strong> and add some dinners first.</div>`;
    return;
  }

  app.innerHTML = `
    <div class="view-header">
      <h2>Shopping List</h2>
      <button class="btn secondary" id="reset-checks">Uncheck All</button>
    </div>
    <p class="view-sub">Everything for ${plannedCount} dinner${plannedCount === 1 ? "" : "s"}, grouped in the order you'd walk Publix.</p>
    ${groups.map(([dept, items]) => `
      <section class="dept-section">
        <div class="dept-header">${dept}</div>
        <ul class="dept-items">
          ${items.map((ing) => {
            const key = ing.item.toLowerCase();
            const isChecked = !!checks[key];
            return `
            <li class="shop-row ${isChecked ? "checked" : ""}">
              <input type="checkbox" data-check="${key}" ${isChecked ? "checked" : ""}>
              <span class="shop-info">
                <span class="shop-name">${ing.item}</span>
                <span class="shop-detail">${ing.amounts.join(" + ")} — for ${[...new Set(ing.recipes)].join(", ")}</span>
              </span>
              ${publixLink(ing.search || ing.item, "Publix")}
            </li>`;
          }).join("")}
        </ul>
      </section>`).join("")}`;

  app.querySelectorAll("[data-check]").forEach((cb) => {
    cb.addEventListener("change", () => {
      checks[cb.dataset.check] = cb.checked;
      saveJSON(CHECKS_KEY, checks);
      cb.closest(".shop-row").classList.toggle("checked", cb.checked);
    });
  });
  document.getElementById("reset-checks").addEventListener("click", () => {
    checks = {};
    saveJSON(CHECKS_KEY, checks);
    renderShoppingList();
  });
}

// ---------- All recipes ----------
const SORT_MODES = {
  quickest:  { label: "Quickest first" },
  calories:  { label: "Lowest calories" },
  toprated:  { label: "Top rated" },
  easiest:   { label: "Easiest to make" },
  favorites: { label: "Favorites first" },
  az:        { label: "A to Z" },
};

let favoritesOnly = false;
let styleFilter = "all"; // local filter on All Recipes, separate from week prefs

// Build filter chips from whatever actually appears in the data.
const allergensInData = [...new Set(RECIPES.flatMap((r) => r.allergens))]
  .sort((a, b) => Object.keys(ALLERGENS).indexOf(a) - Object.keys(ALLERGENS).indexOf(b));
const stylesInData = [...new Set(RECIPES.map((r) => r.health))]
  .sort((a, b) => Object.keys(HEALTH_LEVELS).indexOf(a) - Object.keys(HEALTH_LEVELS).indexOf(b));

function sortedRecipes() {
  const taste = (r) => (getReview(r.id) || {}).taste || 0;
  const ease = (r) => (getReview(r.id) || {}).ease || 0;
  let list = safeRecipes();
  if (styleFilter !== "all") list = list.filter((r) => r.health === styleFilter);
  if (favoritesOnly) list = list.filter((r) => favorites[r.id]);
  return list.slice().sort((a, b) => {
    switch (sortMode) {
      case "calories":  return a.calories - b.calories;
      case "toprated":  return taste(b) - taste(a) || a.time - b.time;
      case "easiest":   return ease(b) - ease(a) || a.time - b.time;
      case "favorites": return (favorites[b.id] ? 1 : 0) - (favorites[a.id] ? 1 : 0) || a.name.localeCompare(b.name);
      case "az":        return a.name.localeCompare(b.name);
      case "quickest":
      default:          return a.time - b.time || taste(b) - taste(a);
    }
  });
}

function renderAllRecipes() {
  const visible = sortedRecipes();
  const hiddenCount = RECIPES.length - safeRecipes().length;

  app.innerHTML = `
    <div class="view-header"><h2>All Recipes</h2></div>
    <p class="view-sub">Rate meals after you cook them, save favorites with the heart, and sort by whatever fits tonight.</p>

    <div class="toolbar">
      <div class="toolbar-group">
        <span class="toolbar-label">Sort</span>
        <select id="sort-select" class="pref-select">
          ${Object.entries(SORT_MODES).map(([k, v]) => `<option value="${k}" ${k === sortMode ? "selected" : ""}>${v.label}</option>`).join("")}
        </select>
        <button class="chip ${favoritesOnly ? "on" : ""}" id="favs-only">Favorites only</button>
      </div>
      <div class="toolbar-group">
        <span class="toolbar-label">Style</span>
        <button class="chip ${styleFilter === "all" ? "on" : ""}" data-style="all">All</button>
        ${stylesInData.map((h) => `
          <button class="chip ${styleFilter === h ? "on" : ""}" data-style="${h}">${HEALTH_LEVELS[h].label}</button>`).join("")}
      </div>
      <div class="toolbar-group">
        <span class="toolbar-label">Avoid</span>
        ${allergensInData.map((a) => `
          <button class="chip allergy ${excludedAllergens.includes(a) ? "on" : ""}" data-allergen="${a}">${ALLERGENS[a]}</button>`).join("")}
      </div>
    </div>
    ${hiddenCount ? `<p class="filter-note">${hiddenCount} recipe${hiddenCount === 1 ? "" : "s"} hidden by your allergy filters (also skipped in shuffle and swap).</p>` : ""}

    ${visible.length ? `
    <div class="recipe-grid">
      ${visible.map((r) => `
        <div class="recipe-card" data-recipe="${r.id}">
          <div class="card-top">
            ${healthPill(r)}
            ${favHeart(r.id)}
          </div>
          <h3>${r.name}</h3>
          <span class="time-chip">${mealMeta(r)} · Serves 2</span>
          ${ratingSummary(r.id) ? `<div class="rating-row">${ratingSummary(r.id)}</div>` : `<div class="rating-row unrated">Not rated yet</div>`}
          <div class="tag-row">${r.tags.map((t) => `<span class="tag">${t}</span>`).join("")}</div>
        </div>`).join("")}
    </div>` : `
    <div class="empty-note">No recipes match these filters${favoritesOnly ? " — try turning off Favorites only" : ""}.</div>`}`;

  wireRecipeLinks("all");
  wireFavButtons(renderAllRecipes);

  document.getElementById("sort-select").addEventListener("change", (e) => {
    sortMode = e.target.value;
    saveJSON(SORT_KEY, sortMode);
    renderAllRecipes();
  });
  document.getElementById("favs-only").addEventListener("click", () => {
    favoritesOnly = !favoritesOnly;
    renderAllRecipes();
  });
  app.querySelectorAll("[data-style]").forEach((b) => {
    b.addEventListener("click", () => {
      styleFilter = b.dataset.style;
      renderAllRecipes();
    });
  });
  app.querySelectorAll("[data-allergen]").forEach((b) => {
    b.addEventListener("click", () => {
      const a = b.dataset.allergen;
      excludedAllergens = excludedAllergens.includes(a)
        ? excludedAllergens.filter((x) => x !== a)
        : [...excludedAllergens, a];
      saveJSON(ALLERGY_KEY, excludedAllergens);
      renderAllRecipes();
    });
  });
}

// ---------- Go ----------
render();

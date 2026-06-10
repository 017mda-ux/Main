// ============================================================
// Our Weekly Menu — app logic
// Views: week planner, recipe detail, shopping list, all recipes.
// The weekly plan and shopping-list checkmarks persist in
// localStorage so the plan survives refreshes on the same device.
// ============================================================

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const STORAGE_KEY = "weekly-menu-plan-v1";
const CHECKS_KEY = "weekly-menu-checks-v1";

const app = document.getElementById("app");

// ---------- Publix link helper ----------
function publixUrl(term) {
  return "https://www.publix.com/search?searchTerm=" + encodeURIComponent(term);
}

// ---------- Plan state ----------
function loadPlan() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (Array.isArray(saved) && saved.length === 7 &&
        saved.every((id) => id === null || RECIPES.some((r) => r.id === id))) {
      return saved;
    }
  } catch (e) { /* fall through to a fresh plan */ }
  return shuffledPlan();
}

function shuffledPlan() {
  const ids = RECIPES.map((r) => r.id);
  for (let i = ids.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [ids[i], ids[j]] = [ids[j], ids[i]];
  }
  return ids.slice(0, 7);
}

function savePlan() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(plan));
}

function loadChecks() {
  try { return JSON.parse(localStorage.getItem(CHECKS_KEY)) || {}; }
  catch (e) { return {}; }
}

function saveChecks() {
  localStorage.setItem(CHECKS_KEY, JSON.stringify(checks));
}

let plan = loadPlan();
let checks = loadChecks();
savePlan();

const recipeById = (id) => RECIPES.find((r) => r.id === id);

// getDay(): Sunday=0 ... Saturday=6 → our Monday-first index
function todayIndex() {
  return (new Date().getDay() + 6) % 7;
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
function renderWeek() {
  const today = todayIndex();
  app.innerHTML = `
    <div class="view-header">
      <h2>This Week's Dinners</h2>
      <button class="btn secondary" id="shuffle-week">🎲 Shuffle the Week</button>
    </div>
    <p class="view-sub">Tap a meal for the recipe and Publix links. Swap any night you're not feeling.</p>
    <div class="week-grid">
      ${DAYS.map((day, i) => {
        const r = recipeById(plan[i]);
        return `
        <div class="day-card">
          <div class="day-label ${i === today ? "today" : ""}">
            <span>${day}</span>
            ${i === today ? '<span class="today-pill">Tonight!</span>' : ""}
          </div>
          <div class="day-body">
            ${r ? `
              <button class="meal-link" data-recipe="${r.id}">
                <span class="meal-emoji">${r.emoji}</span>
                <span>
                  <span class="meal-name">${r.name}</span><br>
                  <span class="meal-meta">⏱️ ${r.time} min · ${r.tags[0]}</span>
                </span>
              </button>` : `
              <p class="meal-meta">Nothing planned — date night out? 😉</p>`}
            <div class="day-actions">
              <button class="btn small secondary" data-swap="${i}">↔️ Swap</button>
              ${r ? `<button class="btn small secondary" data-clear="${i}">✕ Clear</button>` : ""}
            </div>
          </div>
        </div>`;
      }).join("")}
    </div>`;

  document.getElementById("shuffle-week").addEventListener("click", () => {
    plan = shuffledPlan();
    savePlan();
    renderWeek();
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
  const backdrop = document.createElement("div");
  backdrop.className = "modal-backdrop";
  backdrop.innerHTML = `
    <div class="modal">
      <h3>Pick a meal for ${DAYS[dayIndex]}</h3>
      <ul class="picker-list">
        ${RECIPES.map((r) => `
          <li><button class="picker-item" data-pick="${r.id}">
            <span class="emoji">${r.emoji}</span>
            <span><strong>${r.name}</strong><br>
            <span class="meal-meta">⏱️ ${r.time} min · ${r.tags.join(" · ")}</span></span>
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
  const backLabel = from === "all" ? "← All Recipes" : "← Back to This Week";

  app.innerHTML = `
    <button class="back-link" id="back">${backLabel}</button>
    <div class="detail-card">
      <div class="detail-head">
        <span class="emoji">${r.emoji}</span>
        <div>
          <h2>${r.name}</h2>
          <div class="tag-row">${r.tags.map((t) => `<span class="tag">${t}</span>`).join("")}</div>
        </div>
      </div>
      <p class="detail-meta">⏱️ ${r.time} minutes · 👫 Serves 2</p>
      <div class="detail-cols">
        <div>
          <h3>🛒 Ingredients</h3>
          <ul class="ing-list">
            ${r.ingredients.map((ing) => `
              <li class="ing-row">
                <span class="ing-info">
                  <span class="ing-name">${ing.item}</span>
                  <span class="ing-amount">${ing.amount}</span>
                  <span class="ing-dept">${DEPARTMENTS[ing.dept].emoji} ${ing.dept}</span>
                </span>
                <a class="publix-link" href="${publixUrl(ing.search || ing.item)}" target="_blank" rel="noopener">
                  Find at Publix ↗
                </a>
              </li>`).join("")}
          </ul>
        </div>
        <div>
          <h3>👩‍🍳 Steps</h3>
          <ol class="steps-list">
            ${r.steps.map((s) => `<li>${s}</li>`).join("")}
          </ol>
        </div>
      </div>
    </div>`;

  document.getElementById("back").addEventListener("click", () => navigate({ name: from === "all" ? "all" : "week" }));
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
      <div class="empty-note">No meals planned yet — head to <strong>This Week</strong> and add some dinners first!</div>`;
    return;
  }

  app.innerHTML = `
    <div class="view-header">
      <h2>Shopping List</h2>
      <button class="btn secondary" id="reset-checks">↺ Uncheck All</button>
    </div>
    <p class="view-sub">Everything for ${plannedCount} dinner${plannedCount === 1 ? "" : "s"}, grouped in the order you'd walk Publix. Tap an item's link to find it on Publix.com.</p>
    ${groups.map(([dept, items]) => `
      <section class="dept-section">
        <div class="dept-header">${DEPARTMENTS[dept].emoji} ${dept}</div>
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
              <a class="publix-link" href="${publixUrl(ing.search || ing.item)}" target="_blank" rel="noopener">
                Publix ↗
              </a>
            </li>`;
          }).join("")}
        </ul>
      </section>`).join("")}`;

  app.querySelectorAll("[data-check]").forEach((cb) => {
    cb.addEventListener("change", () => {
      checks[cb.dataset.check] = cb.checked;
      saveChecks();
      cb.closest(".shop-row").classList.toggle("checked", cb.checked);
    });
  });
  document.getElementById("reset-checks").addEventListener("click", () => {
    checks = {};
    saveChecks();
    renderShoppingList();
  });
}

// ---------- All recipes ----------
function renderAllRecipes() {
  app.innerHTML = `
    <div class="view-header"><h2>All Recipes</h2></div>
    <p class="view-sub">The full collection — ${RECIPES.length} dinners and counting. Add more in <code>recipes.js</code>.</p>
    <div class="recipe-grid">
      ${RECIPES.map((r) => `
        <div class="recipe-card" data-recipe="${r.id}">
          <span class="emoji">${r.emoji}</span>
          <h3>${r.name}</h3>
          <span class="time-chip">⏱️ ${r.time} min · Serves 2</span>
          <div class="tag-row">${r.tags.map((t) => `<span class="tag">${t}</span>`).join("")}</div>
        </div>`).join("")}
    </div>`;
  wireRecipeLinks("all");
}

// ---------- Go ----------
render();

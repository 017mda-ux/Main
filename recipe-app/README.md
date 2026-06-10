# Peebs Weekly Menu

A simple weekly dinner planner for two, with one-tap Publix ingredient links.

## Features

- **This Week** — A Monday–Sunday board of dinners with a preferences bar:
  pick a style (Healthy / Balanced / Gnommy), a calorie cap, and a cook-time
  cap, and the whole week regenerates to match. The dice button reshuffles
  (with a shake). Swap or clear any single night. Saved automatically in
  the browser (localStorage).
- **Recipe view** — Ingredients (portioned for two) with **Find at Publix**
  links, numbered steps, calories per serving, allergen notes, a favorite
  heart, and a review box (taste + quick/easy star ratings with notes).
- **Shopping List** — Combines all ingredients across the week's dinners,
  de-duplicates them, and groups them by Publix department in roughly the
  order you'd walk the store. Checkboxes persist while you shop.
- **All Recipes** — Sort by quickest, lowest calories, top rated, easiest,
  or favorites. Filter chips for style and allergens are generated
  dynamically from the recipe data. Allergy exclusions (shellfish and nuts
  by default) also apply to shuffle and swap.

## Running it

No build step, no server required — just open the file:

```
open recipe-app/index.html
```

Or serve it locally:

```
cd recipe-app && python3 -m http.server 8000
```

It also works as-is on GitHub Pages (Settings → Pages → deploy from branch).

## Adding your own recipes

Edit `recipes.js` — each recipe is a plain object:

```js
{
  id: "my-new-dish",          // unique string
  name: "My New Dish",
  calories: 600,               // estimated, per serving
  health: "balanced",          // "healthy" | "balanced" | "indulgent" (Gnommy)
  time: 30,                    // minutes
  tags: ["Comfort"],
  allergens: ["gluten"],       // keys from ALLERGENS, or []
  ingredients: [
    { item: "Egg noodles", amount: "8 oz", dept: "Pantry",
      search: "wide egg noodles" },  // optional: better Publix search term
  ],
  steps: ["Do the thing.", "Eat."],
}
```

`dept` must be one of the keys in `DEPARTMENTS` (top of `recipes.js`);
it controls how the shopping list is grouped and ordered.

## A note on aisle links

Publix doesn't expose exact aisle numbers on the web — they vary by store.
The links open a Publix.com product search for the ingredient; once an item
is in your cart on the Publix **app** with your home store selected, the
in-store item locator shows the exact aisle.

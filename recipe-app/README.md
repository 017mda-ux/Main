# Peebs Weekly Menu

A weekly dinner planner for two with one-tap Publix ingredient links and
1,300+ dinner ideas: 26 curated house recipes (including 10 Blackstone
griddle classics like smash burgers, hibachi fried rice, and Philly
cheesesteaks) plus a meal generator
(`generator.js`) that composes coherent dinners from proteins, flavor
preps, and serving formats, with incompatible combinations pruned.

## Features

- **This Week** — A Monday–Sunday board of dinners with a preferences bar:
  pick a style (Healthy / Balanced / Gnommy), a calorie range (under
  500/650/800, or over 850/1500 for feast nights), a cook-time cap, and
  what you're cooking on (anything, or Blackstone griddle only), and the
  whole week regenerates to match. The dice button reshuffles with
  a shake and never repeats the current week. Swap or clear any single
  night. Saved automatically in the browser (localStorage).
- **Recipe view** — Ingredients (portioned for two) with **Find at Publix**
  links, numbered steps, calories per serving, allergen notes, a favorite
  heart, and a review box (taste + quick/easy star ratings with notes).
- **Shopping List** — Combines all ingredients across the week's dinners,
  de-duplicates them, and groups them by Publix department in roughly the
  order you'd walk the store. Checkboxes persist while you shop.
- **All Recipes** — Search the full library; sort by quickest, lowest
  calories, top rated, easiest, or favorites. Filter chips for style and
  allergens are generated dynamically from the recipe data. Allergy
  exclusions (shellfish and nuts by default) also apply to shuffle and
  swap. Results paginate 48 at a time.

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
  griddle: true,               // optional: cooks on the Blackstone flat-top
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

# 🍽️ Our Weekly Menu

A simple weekly dinner planner for two, with one-tap Publix ingredient links.

## Features

- **📅 This Week** — A Monday–Sunday board of dinners. Today's card is
  highlighted ("Tonight!"). Shuffle the whole week, swap any single night,
  or clear a night for date night out. Your plan is saved automatically in
  the browser (localStorage).
- **🍳 Recipe view** — Click any meal to see ingredients (portioned for two)
  and numbered steps. Every ingredient has a **Find at Publix** button that
  opens a Publix.com product search, plus its typical department
  (Produce, Dairy, Meat, …).
- **🛒 Shopping List** — Combines all ingredients across the week's dinners,
  de-duplicates them, and groups them by Publix department in roughly the
  order you'd walk the store. Checkboxes persist while you shop.
- **📖 All Recipes** — Browse the full collection and jump into any recipe.

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
  emoji: "🍜",
  time: 30,                    // minutes
  tags: ["Comfort"],
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

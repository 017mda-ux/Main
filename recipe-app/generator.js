// ============================================================
// MEAL GENERATOR
// Composes dinner ideas from building blocks: a protein, a flavor
// prep, and a serving format. Incompatible combinations are pruned
// with profile matching (e.g. teriyaki never lands on pasta) and
// per-component block lists, leaving 1,000+ coherent dinners.
//
// Generated recipe ids are stable ("gen-<protein>-<prep>-<format>")
// so favorites, reviews, and the weekly plan survive updates.
//
// Combos where both the protein and the format are flat-top friendly
// are flagged griddle: true for the Blackstone filter.
//
// ALL_RECIPES = curated house recipes (recipes.js) + generated ideas.
// ============================================================

// Flavor profiles connect preps to the formats they make sense in.
// fresh = bright/lemony, am = american, so = southern, mx = mexican,
// as = asian, it = italian, md = mediterranean.

const GEN_PROTEINS = [
  { id: "chicken-breast", griddle: true, label: "Chicken", short: "chicken", cal: 280, time: 20, allergens: [],
    items: [{ item: "Chicken breasts", amount: "1 lb", dept: "Meat", search: "boneless chicken breast" }],
    cook: "Cook the chicken in a hot, oiled skillet, 5–6 minutes per side, until it reaches 165°F; rest and slice." },
  { id: "chicken-thighs", griddle: true, label: "Chicken Thighs", short: "chicken", cal: 340, time: 25, allergens: [],
    items: [{ item: "Chicken thighs", amount: "1 lb, boneless", dept: "Meat", search: "boneless chicken thighs" }],
    cook: "Sear the chicken thighs 6–7 minutes per side until deeply golden and cooked through; rest and slice." },
  { id: "crispy-chicken", label: "Crispy Chicken", short: "chicken", cal: 600, time: 35, allergens: ["gluten", "dairy"],
    items: [
      { item: "Chicken breasts", amount: "2, halved flat", dept: "Meat", search: "boneless chicken breast" },
      { item: "Buttermilk", amount: "1 cup", dept: "Dairy" },
      { item: "All-purpose flour", amount: "1 cup", dept: "Pantry" },
      { item: "Vegetable oil", amount: "for frying", dept: "Pantry", search: "vegetable oil" },
    ],
    cook: "Soak the chicken in buttermilk, dredge in seasoned flour, and shallow-fry 4–5 minutes per side to 165°F." },
  { id: "ground-beef", griddle: true, label: "Beef", short: "beef", cal: 380, time: 15, allergens: [],
    items: [{ item: "Ground beef", amount: "1 lb", dept: "Meat", search: "ground beef 80/20" }],
    cook: "Brown the beef in a hot skillet, breaking it up, 6–8 minutes; drain excess fat." },
  { id: "ground-turkey", griddle: true, label: "Turkey", short: "turkey", cal: 300, time: 15, allergens: [],
    items: [{ item: "Ground turkey", amount: "1 lb", dept: "Meat", search: "93% lean ground turkey" }],
    cook: "Brown the turkey in a hot, oiled skillet, breaking it up, 6–8 minutes." },
  { id: "italian-sausage", griddle: true, label: "Sausage", short: "sausage", cal: 420, time: 20, allergens: [],
    items: [{ item: "Italian sausage", amount: "1 lb", dept: "Meat", search: "italian sausage" }],
    cook: "Brown the sausage over medium-high heat until cooked through, about 8–10 minutes." },
  { id: "smoked-sausage", griddle: true, label: "Smoked Sausage", short: "sausage", cal: 400, time: 15, allergens: [],
    items: [{ item: "Smoked sausage", amount: "14 oz, sliced", dept: "Meat", search: "smoked sausage" }],
    cook: "Sear the sausage slices until browned at the edges, 5–6 minutes." },
  { id: "pork-chops", griddle: true, label: "Pork Chops", short: "pork", cal: 360, time: 25, allergens: [],
    items: [{ item: "Pork chops", amount: "2 bone-in", dept: "Meat", search: "bone-in pork chops" }],
    cook: "Sear the pork chops 4–5 minutes per side to 145°F; rest 5 minutes." },
  { id: "pork-tenderloin", griddle: true, label: "Pork Tenderloin", short: "pork", cal: 300, time: 30, allergens: [],
    items: [{ item: "Pork tenderloin", amount: "1 lb", dept: "Meat", search: "pork tenderloin" }],
    cook: "Sear the tenderloin on all sides, then roast at 400°F for 15–18 minutes to 145°F; rest and slice." },
  { id: "sirloin-steak", griddle: true, label: "Steak", short: "steak", cal: 400, time: 20, allergens: [],
    items: [{ item: "Sirloin steak", amount: "1 lb", dept: "Meat", search: "sirloin steak" }],
    cook: "Sear the steak in a screaming-hot pan, 3–4 minutes per side for medium; rest, then slice against the grain." },
  { id: "salmon", griddle: true, label: "Salmon", short: "salmon", cal: 350, time: 20, allergens: ["fish"],
    items: [{ item: "Salmon fillets", amount: "2 (6 oz each)", dept: "Seafood", search: "fresh salmon fillet" }],
    cook: "Cook the salmon skin-side down 4 minutes, flip, and cook 2–3 more until it flakes easily." },
  { id: "white-fish", griddle: true, label: "White Fish", short: "fish", cal: 220, time: 15, allergens: ["fish"],
    items: [{ item: "Mahi or tilapia fillets", amount: "2 (6 oz each)", dept: "Seafood", search: "mahi mahi fillet" }],
    cook: "Cook the fish 3–4 minutes per side until opaque and flaky." },
  { id: "shrimp", griddle: true, label: "Shrimp", short: "shrimp", cal: 240, time: 10, allergens: ["shellfish"],
    items: [{ item: "Large shrimp", amount: "1 lb, peeled", dept: "Seafood", search: "raw shrimp peeled" }],
    cook: "Sear the shrimp 1–2 minutes per side until pink and just cooked through." },
  { id: "meatballs", label: "Meatballs", short: "meatballs", cal: 450, time: 25, allergens: ["gluten", "eggs"],
    items: [
      { item: "Ground beef", amount: "1 lb", dept: "Meat", search: "ground beef 80/20" },
      { item: "Breadcrumbs", amount: "1/2 cup", dept: "Pantry", search: "italian breadcrumbs" },
      { item: "Egg", amount: "1", dept: "Dairy", search: "large eggs" },
    ],
    cook: "Mix the beef with breadcrumbs, egg, salt, and pepper; roll into meatballs and brown on all sides, 10–12 minutes." },
  { id: "tofu", griddle: true, label: "Crispy Tofu", short: "tofu", cal: 220, time: 20, allergens: ["soy"],
    items: [
      { item: "Extra-firm tofu", amount: "14 oz, pressed", dept: "Produce", search: "extra firm tofu" },
      { item: "Cornstarch", amount: "2 tbsp", dept: "Pantry" },
    ],
    cook: "Cube the tofu, toss with cornstarch, and pan-fry until golden and crisp on all sides, 8–10 minutes." },
  { id: "chickpeas", label: "Chickpea", short: "chickpeas", cal: 210, time: 20, allergens: [],
    items: [{ item: "Chickpeas", amount: "2 cans (15 oz), drained", dept: "Pantry", search: "canned chickpeas" }],
    cook: "Roast the chickpeas with olive oil at 425°F for 18–20 minutes until crisp." },
];

const GEN_PREPS = [
  { id: "lemon-garlic", name: "Lemon-Garlic", profile: "fresh", cal: 80, time: 0, allergens: ["dairy"],
    items: [
      { item: "Lemon", amount: "1", dept: "Produce" },
      { item: "Garlic", amount: "4 cloves", dept: "Produce" },
      { item: "Butter", amount: "2 tbsp", dept: "Dairy", search: "unsalted butter" },
    ],
    step: "Make a lemon-garlic butter: melt the butter with minced garlic, lemon zest, and a big squeeze of juice; spoon it over the {protein} as it finishes." },
  { id: "garlic-butter", name: "Garlic Butter", profile: "am", cal: 120, time: 0, allergens: ["dairy"],
    items: [
      { item: "Butter", amount: "3 tbsp", dept: "Dairy", search: "unsalted butter" },
      { item: "Garlic", amount: "4 cloves", dept: "Produce" },
      { item: "Fresh parsley", amount: "2 tbsp, chopped", dept: "Produce" },
    ],
    step: "Baste the {protein} with garlic butter in the final minutes and finish with chopped parsley." },
  { id: "cajun", name: "Cajun Blackened", profile: "so", cal: 30, time: 0, allergens: [],
    items: [{ item: "Cajun seasoning", amount: "2 tbsp", dept: "Spices", search: "cajun seasoning" }],
    step: "Coat the {protein} generously with cajun seasoning before cooking; let the spices char slightly for that blackened crust." },
  { id: "bbq", name: "BBQ-Glazed", profile: "am", cal: 120, time: 0, allergens: [],
    items: [{ item: "BBQ sauce", amount: "1/2 cup", dept: "Pantry", search: "sweet baby rays bbq sauce" }],
    step: "Brush the {protein} with BBQ sauce in the last few minutes of cooking so it caramelizes into a sticky glaze." },
  { id: "honey-garlic", name: "Honey-Garlic", profile: "as", cal: 110, time: 0, allergens: ["soy"],
    items: [
      { item: "Honey", amount: "1/4 cup", dept: "Pantry" },
      { item: "Soy sauce", amount: "3 tbsp", dept: "International", search: "soy sauce" },
      { item: "Garlic", amount: "4 cloves", dept: "Produce" },
    ],
    step: "Whisk honey, soy sauce, and minced garlic; pour over the cooked {protein} and simmer 1–2 minutes until glossy." },
  { id: "teriyaki", name: "Teriyaki", profile: "as", cal: 130, time: 0, allergens: ["soy", "gluten"],
    items: [
      { item: "Teriyaki sauce", amount: "1/2 cup", dept: "International", search: "teriyaki sauce" },
      { item: "Sesame seeds", amount: "1 tbsp", dept: "Spices", search: "sesame seeds" },
    ],
    step: "Glaze the cooked {protein} with teriyaki sauce and a sprinkle of sesame seeds." },
  { id: "taco-spiced", name: "Taco-Spiced", profile: "mx", cal: 40, time: 0, allergens: [],
    items: [
      { item: "Taco seasoning", amount: "2 tbsp", dept: "Spices", search: "taco seasoning" },
      { item: "Lime", amount: "1", dept: "Produce" },
    ],
    step: "Season the {protein} with taco seasoning before cooking and finish with a big squeeze of lime." },
  { id: "italian-herb", name: "Italian Herb", profile: "it", cal: 60, time: 0, allergens: [],
    items: [
      { item: "Italian seasoning", amount: "1 tbsp", dept: "Spices" },
      { item: "Olive oil", amount: "2 tbsp", dept: "Pantry" },
      { item: "Garlic", amount: "3 cloves", dept: "Produce" },
    ],
    step: "Rub the {protein} with olive oil, Italian seasoning, minced garlic, salt, and pepper before cooking." },
  { id: "parmesan-crusted", name: "Parmesan-Crusted", profile: "it", cal: 180, time: 5, allergens: ["dairy", "gluten"],
    items: [
      { item: "Parmesan cheese", amount: "1/2 cup, grated", dept: "Dairy", search: "grated parmesan cheese" },
      { item: "Panko breadcrumbs", amount: "1/2 cup", dept: "Pantry", search: "panko breadcrumbs" },
    ],
    step: "Press a mix of parmesan and panko onto the {protein} before cooking; it should turn deep golden and crunchy." },
  { id: "greek", name: "Greek Lemon-Oregano", profile: "md", cal: 70, time: 0, allergens: [],
    items: [
      { item: "Lemon", amount: "1", dept: "Produce" },
      { item: "Dried oregano", amount: "1 tbsp", dept: "Spices" },
      { item: "Olive oil", amount: "2 tbsp", dept: "Pantry" },
    ],
    step: "Marinate the {protein} in olive oil, lemon juice, oregano, salt, and pepper for at least 10 minutes before cooking." },
  { id: "buffalo", name: "Buffalo", profile: "am", cal: 100, time: 0, allergens: ["dairy"],
    items: [
      { item: "Buffalo sauce", amount: "1/2 cup", dept: "Pantry", search: "franks redhot buffalo sauce" },
      { item: "Blue cheese dressing", amount: "1/4 cup", dept: "Pantry", search: "blue cheese dressing" },
    ],
    step: "Toss the hot cooked {protein} in buffalo sauce; serve with blue cheese dressing for dipping or drizzling.",
    blockedProteins: ["salmon", "white-fish", "pork-chops", "pork-tenderloin", "sirloin-steak", "smoked-sausage", "italian-sausage"] },
  { id: "maple-dijon", name: "Maple-Dijon", profile: "am", cal: 100, time: 0, allergens: [],
    items: [
      { item: "Maple syrup", amount: "3 tbsp", dept: "Pantry", search: "pure maple syrup" },
      { item: "Dijon mustard", amount: "2 tbsp", dept: "Pantry", search: "dijon mustard" },
    ],
    step: "Whisk maple syrup and dijon; brush onto the {protein} in the last minutes of cooking until lacquered.",
    blockedProteins: ["shrimp", "tofu", "meatballs", "crispy-chicken"] },
  { id: "pesto", name: "Pesto", profile: "it", cal: 160, time: 0, allergens: ["dairy", "nuts"],
    items: [{ item: "Basil pesto", amount: "1/2 cup", dept: "Pantry", search: "basil pesto" }],
    step: "Spoon pesto over the hot cooked {protein} so it melts into a glossy herb coating.",
    blockedProteins: ["crispy-chicken", "smoked-sausage", "ground-beef", "ground-turkey"] },
  { id: "sesame-ginger", name: "Sesame-Ginger", profile: "as", cal: 110, time: 0, allergens: ["soy"],
    items: [
      { item: "Sesame oil", amount: "1 tbsp", dept: "International", search: "toasted sesame oil" },
      { item: "Fresh ginger", amount: "1 tbsp, grated", dept: "Produce", search: "fresh ginger root" },
      { item: "Soy sauce", amount: "3 tbsp", dept: "International", search: "soy sauce" },
    ],
    step: "Whisk sesame oil, grated ginger, and soy sauce; toss with the cooked {protein}." },
  { id: "chipotle-lime", name: "Chipotle-Lime", profile: "mx", cal: 60, time: 0, allergens: [],
    items: [
      { item: "Chipotle peppers in adobo", amount: "2, minced", dept: "International", search: "chipotle peppers adobo" },
      { item: "Lime", amount: "2", dept: "Produce" },
    ],
    step: "Rub the {protein} with minced chipotle, lime zest, and salt before cooking; finish with lime juice." },
  { id: "bacon-ranch", name: "Bacon-Ranch", profile: "am", cal: 250, time: 10, allergens: ["dairy"],
    items: [
      { item: "Bacon", amount: "6 slices", dept: "Meat", search: "thick cut bacon" },
      { item: "Ranch dressing", amount: "1/3 cup", dept: "Pantry", search: "ranch dressing" },
    ],
    step: "Crisp and crumble the bacon; shower it over the cooked {protein} and drizzle everything with ranch.",
    blockedProteins: ["salmon", "white-fish", "shrimp", "tofu", "chickpeas", "meatballs"] },
  { id: "gochujang", name: "Korean Gochujang", profile: "as", cal: 120, time: 0, allergens: ["soy"],
    items: [
      { item: "Gochujang", amount: "3 tbsp", dept: "International", search: "gochujang" },
      { item: "Honey", amount: "1 tbsp", dept: "Pantry" },
      { item: "Sesame seeds", amount: "1 tbsp", dept: "Spices", search: "sesame seeds" },
    ],
    step: "Stir gochujang with honey and a splash of water; toss with the cooked {protein} and top with sesame seeds." },
];

const GEN_FORMATS = [
  { id: "rice-bowl", griddle: true, suffix: "Rice Bowl", profiles: ["as", "fresh", "mx", "md", "so", "am"], cal: 320, time: 20, allergens: [], lean: true,
    items: [
      { item: "Jasmine rice", amount: "1 cup, uncooked", dept: "International", search: "jasmine rice" },
      { item: "Broccoli", amount: "2 cups florets", dept: "Produce", search: "broccoli crowns" },
      { item: "Green onions", amount: "2, sliced", dept: "Produce" },
    ],
    steps: ["Start the rice per package directions.", "Steam the broccoli until crisp-tender, 4–5 minutes.", "Build bowls: rice, broccoli, and the {protein}; top with sliced green onions."] },
  { id: "power-bowl", griddle: true, suffix: "Power Bowl", profiles: ["fresh", "md", "mx", "am"], cal: 280, time: 20, allergens: [], lean: true,
    items: [
      { item: "Quinoa", amount: "1 cup, uncooked", dept: "Pantry", search: "quinoa" },
      { item: "Baby spinach", amount: "3 cups", dept: "Produce" },
      { item: "Cherry tomatoes", amount: "1 pint", dept: "Produce" },
      { item: "Cucumber", amount: "1, diced", dept: "Produce" },
    ],
    steps: ["Cook the quinoa per package directions.", "Build bowls: quinoa, spinach, tomatoes, and cucumber.", "Top with the {protein} and any pan juices."] },
  { id: "pasta", suffix: "Pasta", profiles: ["it", "fresh", "so", "am"], cal: 450, time: 20, allergens: ["gluten", "dairy"],
    items: [
      { item: "Penne pasta", amount: "8 oz", dept: "Pantry", search: "penne pasta" },
      { item: "Parmesan cheese", amount: "1/2 cup, grated", dept: "Dairy", search: "grated parmesan cheese" },
      { item: "Heavy cream", amount: "3/4 cup", dept: "Dairy" },
    ],
    steps: ["Boil the pasta to al dente; reserve 1/2 cup pasta water.", "Warm the cream in the empty pot, stir in parmesan, and toss with the pasta, loosening with pasta water.", "Fold in the {protein} and serve with extra parmesan."] },
  { id: "tacos", griddle: true, suffix: "Tacos", profiles: ["mx", "so", "as", "am"], cal: 350, time: 10, allergens: [],
    items: [
      { item: "Corn tortillas", amount: "8 small", dept: "International", search: "corn tortillas" },
      { item: "Coleslaw mix", amount: "1 bag", dept: "Produce", search: "coleslaw mix" },
      { item: "Avocado", amount: "1", dept: "Produce" },
      { item: "Cilantro", amount: "1/2 bunch", dept: "Produce", search: "fresh cilantro" },
    ],
    steps: ["Toss the slaw mix with a squeeze of lime and a pinch of salt.", "Warm the tortillas in a dry skillet.", "Build tacos: slaw, the {protein}, avocado slices, and cilantro."] },
  { id: "sandwiches", griddle: true, suffix: "Sandwiches", profiles: ["am", "so"], cal: 420, time: 10, allergens: ["gluten"],
    items: [
      { item: "Brioche buns", amount: "2", dept: "Bakery", search: "brioche hamburger buns" },
      { item: "Romaine lettuce", amount: "2 leaves", dept: "Produce", search: "romaine lettuce" },
      { item: "Tomato", amount: "1, sliced", dept: "Produce", search: "tomatoes on the vine" },
      { item: "Dill pickle chips", amount: "1/2 cup", dept: "Pantry", search: "dill pickle chips" },
    ],
    steps: ["Toast the buns cut-side down until golden.", "Build sandwiches: lettuce, tomato, the {protein}, and pickles."] },
  { id: "sheet-pan", suffix: "Sheet Pan Dinner", profiles: ["fresh", "md", "am", "it", "so", "as"], cal: 300, time: 30, allergens: [], lean: true,
    items: [
      { item: "Baby potatoes", amount: "1 lb, halved", dept: "Produce", search: "baby gold potatoes" },
      { item: "Broccoli", amount: "1 head, in florets", dept: "Produce", search: "broccoli crowns" },
      { item: "Red onion", amount: "1, in wedges", dept: "Produce" },
      { item: "Olive oil", amount: "3 tbsp", dept: "Pantry" },
    ],
    steps: ["Preheat the oven to 425°F. Toss the potatoes with oil, salt, and pepper; roast 15 minutes.", "Add the broccoli, onion, and the {protein} to the pan.", "Roast 15–18 more minutes until the vegetables are browned and everything is cooked through."] },
  { id: "chopped-salad", griddle: true, suffix: "Chopped Salad", profiles: ["fresh", "md", "mx", "am", "as", "so"], cal: 220, time: 10, allergens: [], lean: true,
    items: [
      { item: "Romaine hearts", amount: "2, chopped", dept: "Produce", search: "romaine hearts" },
      { item: "Cherry tomatoes", amount: "1 cup", dept: "Produce" },
      { item: "Cucumber", amount: "1, diced", dept: "Produce" },
      { item: "Vinaigrette", amount: "1/4 cup", dept: "Pantry", search: "balsamic vinaigrette" },
    ],
    steps: ["Chop and toss the romaine, tomatoes, and cucumber with the vinaigrette.", "Top the salad with the warm {protein}."] },
  { id: "noodle-stir-fry", griddle: true, suffix: "Noodle Stir-Fry", profiles: ["as"], cal: 420, time: 15, allergens: ["gluten"],
    items: [
      { item: "Lo mein noodles", amount: "8 oz", dept: "International", search: "lo mein noodles" },
      { item: "Snow peas", amount: "2 cups", dept: "Produce" },
      { item: "Carrots", amount: "2, julienned", dept: "Produce" },
    ],
    steps: ["Boil the noodles per package directions; drain.", "Stir-fry the snow peas and carrots over high heat, 2–3 minutes.", "Add the noodles and the {protein}; toss everything together until coated and hot."] },
  { id: "mashed-potatoes", suffix: "with Mashed Potatoes", profiles: ["am", "fresh", "so"], cal: 380, time: 15, allergens: ["dairy"],
    items: [
      { item: "Refrigerated mashed potatoes", amount: "1 package", dept: "Dairy", search: "refrigerated mashed potatoes" },
      { item: "Fresh green beans", amount: "12 oz", dept: "Produce", search: "fresh green beans" },
    ],
    steps: ["Heat the mashed potatoes per the package.", "Steam the green beans 4–5 minutes until crisp-tender.", "Plate the {protein} over the potatoes with the green beans alongside, spooning over any pan sauce."] },
  { id: "wraps", griddle: true, suffix: "Wraps", profiles: ["mx", "am", "md", "so"], cal: 380, time: 10, allergens: ["gluten"],
    items: [
      { item: "Flour tortillas", amount: "4 large", dept: "International", search: "flour tortillas burrito size" },
      { item: "Shredded lettuce", amount: "2 cups", dept: "Produce", search: "shredded lettuce" },
      { item: "Tomato", amount: "1, diced", dept: "Produce", search: "tomatoes on the vine" },
    ],
    steps: ["Warm the tortillas so they roll without cracking.", "Layer lettuce, tomato, and the {protein} down the center of each.", "Roll tightly, slice in half, and serve."] },
  { id: "loaded-fries", suffix: "Loaded Fries", profiles: ["am", "so", "mx", "as"], cal: 850, time: 30, allergens: ["dairy"], heavy: true,
    items: [
      { item: "Frozen crinkle-cut fries", amount: "1 bag", dept: "Frozen", search: "frozen crinkle cut fries" },
      { item: "Shredded cheddar", amount: "1 1/2 cups", dept: "Dairy", search: "shredded cheddar cheese" },
      { item: "Sour cream", amount: "1/2 cup", dept: "Dairy" },
      { item: "Green onions", amount: "2, sliced", dept: "Produce" },
    ],
    steps: ["Bake the fries per the bag until extra crispy.", "Pile the fries on a sheet pan, top with cheddar, and broil 1–2 minutes until melted.", "Top with the {protein}, sour cream, and green onions. Eat immediately."] },
  { id: "mac-cheese", suffix: "Mac & Cheese", profiles: ["am", "so"], cal: 800, time: 30, allergens: ["dairy", "gluten"], heavy: true,
    items: [
      { item: "Cavatappi pasta", amount: "12 oz", dept: "Pantry", search: "cavatappi pasta" },
      { item: "Sharp cheddar", amount: "2 cups, shredded", dept: "Dairy", search: "sharp cheddar block" },
      { item: "Whole milk", amount: "2 cups", dept: "Dairy" },
      { item: "Butter", amount: "3 tbsp", dept: "Dairy", search: "unsalted butter" },
      { item: "All-purpose flour", amount: "3 tbsp", dept: "Pantry" },
    ],
    steps: ["Boil the pasta 2 minutes shy of al dente.", "Melt the butter, whisk in the flour for 1 minute, then slowly whisk in the milk until thickened; stir in the cheddar off heat.", "Fold in the pasta and the {protein}; broil 2 minutes for a browned top if you like."] },
  { id: "flatbread", suffix: "Flatbread", profiles: ["it", "md", "am", "fresh"], cal: 480, time: 15, allergens: ["gluten", "dairy"],
    items: [
      { item: "Naan or flatbreads", amount: "2", dept: "Bakery", search: "naan bread" },
      { item: "Shredded mozzarella", amount: "1 1/2 cups", dept: "Dairy", search: "shredded mozzarella" },
      { item: "Marinara sauce", amount: "1/2 cup", dept: "Pantry", search: "pizza sauce" },
    ],
    steps: ["Preheat the oven to 450°F.", "Top the flatbreads with sauce, mozzarella, and the {protein}.", "Bake 8–10 minutes until the cheese bubbles and the edges crisp."] },
];

// Formats each protein should never appear in.
const GEN_PROTEIN_BLOCKS = {
  "chicken-breast": [],
  "chicken-thighs": ["sandwiches"],
  "crispy-chicken": ["sheet-pan", "power-bowl", "noodle-stir-fry"],
  "ground-beef": ["sheet-pan", "mashed-potatoes"],
  "ground-turkey": ["sheet-pan", "mashed-potatoes"],
  "italian-sausage": ["tacos", "wraps", "chopped-salad", "noodle-stir-fry", "rice-bowl", "loaded-fries"],
  "smoked-sausage": ["tacos", "sandwiches", "wraps", "chopped-salad", "noodle-stir-fry", "flatbread"],
  "pork-chops": ["tacos", "wraps", "sandwiches", "mac-cheese", "loaded-fries", "noodle-stir-fry", "chopped-salad", "flatbread", "pasta", "power-bowl"],
  "pork-tenderloin": ["mac-cheese", "loaded-fries", "flatbread", "sandwiches"],
  "sirloin-steak": ["mac-cheese", "flatbread"],
  "salmon": ["sandwiches", "mac-cheese", "loaded-fries", "flatbread", "wraps"],
  "white-fish": ["mac-cheese", "loaded-fries", "flatbread", "mashed-potatoes"],
  "shrimp": ["sandwiches", "mashed-potatoes", "loaded-fries"],
  "meatballs": ["tacos", "chopped-salad", "wraps", "loaded-fries", "sheet-pan", "power-bowl"],
  "tofu": ["sandwiches", "mac-cheese", "loaded-fries", "mashed-potatoes", "flatbread"],
  "chickpeas": ["sandwiches", "mac-cheese", "loaded-fries", "mashed-potatoes", "noodle-stir-fry"],
};

function generateRecipes() {
  const out = [];
  for (const protein of GEN_PROTEINS) {
    const blockedFormats = GEN_PROTEIN_BLOCKS[protein.id] || [];
    for (const prep of GEN_PREPS) {
      if (prep.blockedProteins && prep.blockedProteins.includes(protein.id)) continue;
      for (const format of GEN_FORMATS) {
        if (!format.profiles.includes(prep.profile)) continue;
        if (blockedFormats.includes(format.id)) continue;

        const calories = Math.round((protein.cal + prep.cal + format.cal) / 10) * 10;
        const time = Math.max(protein.time, format.time) + prep.time + 5;
        const allergens = [...new Set([...protein.allergens, ...prep.allergens, ...format.allergens])];
        const health = (calories >= 800 || format.heavy) ? "indulgent"
          : (calories <= 620 && format.lean) ? "healthy"
          : "balanced";
        const fill = (s) => s.replaceAll("{protein}", protein.short);

        out.push({
          id: `gen-${protein.id}-${prep.id}-${format.id}`,
          generated: true,
          griddle: !!(protein.griddle && format.griddle),
          name: `${prep.name} ${protein.label} ${format.suffix}`,
          calories,
          health,
          time,
          allergens,
          tags: [prep.name, format.suffix],
          ingredients: [...protein.items, ...prep.items, ...format.items],
          steps: [fill(prep.step), protein.cook, ...format.steps.map(fill)],
        });
      }
    }
  }
  return out;
}

const GENERATED_RECIPES = generateRecipes();
const ALL_RECIPES = [...RECIPES, ...GENERATED_RECIPES];

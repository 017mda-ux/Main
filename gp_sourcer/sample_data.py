"""Sample GP profiles for demo / first-run seeding."""

from .models import GP

SAMPLE_GPS: list[GP] = [
    GP(
        id="marc-andreessen",
        name="Marc Andreessen",
        firm="Andreessen Horowitz (a16z)",
        role="Co-Founder & General Partner",
        focus_areas=["Enterprise Software", "Consumer Internet", "Crypto/Web3", "Bio", "Fintech"],
        stage=["Seed", "Series A", "Series B", "Growth"],
        geography=["US", "Global"],
        fund_size_m=9000,
        aum_m=35000,
        portfolio_highlights=["GitHub", "Lyft", "Coinbase", "Airbnb", "Facebook"],
        notable_exits=["GitHub (acq. $7.5B)", "Lyft (IPO)", "Coinbase (IPO)", "Okta (IPO)"],
        bio=(
            "Co-founder of a16z, one of Silicon Valley's most influential VC firms. "
            "Previously co-founded Netscape and co-created Mosaic, the first web browser. "
            "Thesis: software is eating the world. Strong views on technology, crypto, and progress."
        ),
        status="prospect",
        tags=["top-tier", "crypto", "enterprise", "high-profile"],
        twitter="@pmarca",
        website="https://a16z.com",
        fit_score=8,
        added_date="2026-01-10",
    ),
    GP(
        id="roelof-botha",
        name="Roelof Botha",
        firm="Sequoia Capital",
        role="Managing Partner",
        focus_areas=["Consumer Internet", "Enterprise SaaS", "Fintech", "Healthcare"],
        stage=["Series A", "Series B", "Growth"],
        geography=["US"],
        fund_size_m=2850,
        aum_m=85000,
        portfolio_highlights=["YouTube", "Instagram", "Unity", "Square", "MongoDB"],
        notable_exits=["YouTube (acq. $1.65B)", "Instagram (acq. $1B)", "Square (IPO)", "MongoDB (IPO)"],
        bio=(
            "South African-born investor, formerly CFO of PayPal. "
            "Known for backing category-defining consumer and enterprise businesses. "
            "Led Sequoia's investments in YouTube and Instagram before their landmark acquisitions."
        ),
        status="contacted",
        tags=["top-tier", "consumer", "enterprise", "proven-track-record"],
        website="https://sequoiacap.com",
        fit_score=9,
        added_date="2026-01-15",
        last_contacted="2026-03-01",
    ),
    GP(
        id="bill-gurley",
        name="Bill Gurley",
        firm="Benchmark",
        role="General Partner (Retired)",
        focus_areas=["Marketplace", "Consumer Internet", "SaaS"],
        stage=["Series A", "Series B"],
        geography=["US"],
        fund_size_m=425,
        aum_m=3000,
        portfolio_highlights=["Uber", "OpenTable", "Zillow", "Stitch Fix", "GrubHub"],
        notable_exits=["Uber (IPO, $82B)", "OpenTable (acq. $2.6B)", "Zillow (IPO)", "GrubHub (IPO)"],
        bio=(
            "Former Wall Street analyst turned VC legend at Benchmark. "
            "Wrote seminal posts on marketplace unit economics. "
            "Famous for marketplace investment thesis and early Uber conviction."
        ),
        status="meeting",
        tags=["marketplace", "unit-economics", "legendary"],
        twitter="@bgurley",
        fit_score=7,
        added_date="2026-02-01",
        last_contacted="2026-05-15",
    ),
    GP(
        id="sonali-de-rycker",
        name="Sonali De Rycker",
        firm="Accel",
        role="Partner",
        focus_areas=["Enterprise SaaS", "Fintech", "Consumer"],
        stage=["Seed", "Series A", "Series B"],
        geography=["Europe", "India"],
        fund_size_m=650,
        aum_m=9000,
        portfolio_highlights=["Spotify", "Monzo", "Brainly", "Kry", "Catawiki"],
        notable_exits=["Spotify (IPO)", "BlaBlaCar", "Funding Circle (IPO)"],
        bio=(
            "London-based partner at Accel, one of Europe's most prominent tech investors. "
            "Led investments in Spotify, Monzo, and other European category leaders. "
            "Strong conviction on European tech ecosystem and emerging market fintech."
        ),
        status="meeting",
        tags=["europe", "fintech", "consumer", "diverse-gp"],
        fit_score=9,
        added_date="2026-02-10",
        last_contacted="2026-05-20",
    ),
    GP(
        id="sarah-tavel",
        name="Sarah Tavel",
        firm="Benchmark",
        role="General Partner",
        focus_areas=["Consumer", "Marketplace", "Social"],
        stage=["Seed", "Series A"],
        geography=["US"],
        fund_size_m=425,
        aum_m=3000,
        portfolio_highlights=["Pinterest", "Chainalysis", "Hippo", "Rec Room"],
        notable_exits=["Pinterest (IPO)"],
        bio=(
            "First product manager at Pinterest before moving to VC. "
            "GP at Benchmark with focus on consumer and marketplace businesses. "
            "Known for 'Hierarchy of Engagement' framework for evaluating consumer products."
        ),
        status="prospect",
        tags=["consumer", "marketplace", "social", "operator-turned-investor"],
        twitter="@sarahtavel",
        fit_score=7,
        added_date="2026-03-01",
    ),
    GP(
        id="aileen-lee",
        name="Aileen Lee",
        firm="Cowboy Ventures",
        role="Founder & Managing Partner",
        focus_areas=["Consumer", "Enterprise SaaS", "Future of Work"],
        stage=["Seed", "Series A"],
        geography=["US"],
        fund_size_m=225,
        aum_m=600,
        portfolio_highlights=["Dollar Shave Club", "ClassDojo", "Rent the Runway", "Ipsy"],
        notable_exits=["Dollar Shave Club (acq. $1B)", "Rent the Runway (IPO)"],
        bio=(
            "Founder of Cowboy Ventures and coiner of the term 'unicorn' for $1B+ startups. "
            "Former partner at Kleiner Perkins. Known for data-driven approach to early-stage "
            "investing and strong portfolio support for underrepresented founders."
        ),
        status="diligence",
        tags=["seed", "consumer", "diverse-gp", "early-stage-specialist"],
        twitter="@aileenlee",
        website="https://cowboy.vc",
        fit_score=8,
        added_date="2026-01-20",
        last_contacted="2026-06-01",
        notes=["Met at SeedSF conference — strong alignment on future-of-work thesis"],
    ),
    GP(
        id="hans-tung",
        name="Hans Tung",
        firm="GGV Capital",
        role="Managing Partner",
        focus_areas=["Consumer Tech", "Enterprise SaaS", "Mobile"],
        stage=["Series A", "Series B", "Growth"],
        geography=["US", "China", "Southeast Asia"],
        fund_size_m=2520,
        aum_m=9200,
        portfolio_highlights=["Airbnb", "Slack", "Wish", "ByteDance", "Grab"],
        notable_exits=["Airbnb (IPO)", "Slack (acq. $27.7B)"],
        bio=(
            "Taiwan-born investor with deep expertise in US-China cross-border tech investing. "
            "Has backed companies in both markets at every stage. "
            "Strong network in Southeast Asia and Greater China tech ecosystems."
        ),
        status="prospect",
        tags=["asia", "cross-border", "consumer", "enterprise"],
        fit_score=6,
        added_date="2026-03-15",
    ),
    GP(
        id="peter-fenton",
        name="Peter Fenton",
        firm="Benchmark",
        role="General Partner",
        focus_areas=["Developer Tools", "Open Source", "Infrastructure", "Enterprise"],
        stage=["Series A", "Series B"],
        geography=["US"],
        fund_size_m=425,
        aum_m=3000,
        portfolio_highlights=["Twitter", "Yelp", "New Relic", "Elastic", "Docker"],
        notable_exits=["Yelp (IPO)", "New Relic (IPO)", "Elastic (IPO)", "Twitter (IPO)"],
        bio=(
            "Known for backing developer-focused and open-source companies before they were mainstream. "
            "Led Benchmark's investments in Twitter, Yelp, and Elastic. "
            "Deep conviction on bottom-up enterprise adoption and community-led growth."
        ),
        status="prospect",
        tags=["developer-tools", "open-source", "enterprise", "infrastructure"],
        fit_score=8,
        added_date="2026-04-01",
    ),
    GP(
        id="josh-kopelman",
        name="Josh Kopelman",
        firm="First Round Capital",
        role="Founder & Partner",
        focus_areas=["Enterprise SaaS", "Consumer", "Marketplace", "Fintech"],
        stage=["Pre-Seed", "Seed"],
        geography=["US"],
        fund_size_m=500,
        aum_m=3200,
        portfolio_highlights=["Uber", "Square", "Warby Parker", "Roblox", "Flatiron Health"],
        notable_exits=["Uber (IPO)", "Square (IPO)", "Warby Parker (IPO)"],
        bio=(
            "Pioneer of seed-stage investing, founded First Round Capital in 2004. "
            "Previously founded Half.com, sold to eBay. Built First Round into a premier seed fund "
            "with an operator network that provides unique value-add to portfolio companies."
        ),
        status="contacted",
        tags=["seed-specialist", "operator-network", "top-tier", "east-coast"],
        website="https://firstround.com",
        fit_score=9,
        added_date="2026-01-05",
        last_contacted="2026-04-10",
    ),
    GP(
        id="elad-gil",
        name="Elad Gil",
        firm="Color Capital",
        role="Founder & Managing Partner",
        focus_areas=["AI/ML", "Enterprise SaaS", "Infrastructure", "Crypto"],
        stage=["Seed", "Series A", "Series B"],
        geography=["US"],
        fund_size_m=620,
        aum_m=1800,
        portfolio_highlights=["Stripe", "Airbnb", "Square", "Coinbase", "Airtable", "Notion"],
        notable_exits=["Airbnb (IPO)", "Coinbase (IPO)"],
        bio=(
            "Former VP at Twitter and co-founder of Color Genomics. "
            "Author of 'High Growth Handbook'. Prolific angel investor turned fund manager "
            "with an extraordinary early-stage hit rate. Hands-on operational support."
        ),
        status="prospect",
        tags=["ai", "operator-turned-investor", "early-stage", "top-tier"],
        twitter="@eladgil",
        fit_score=9,
        added_date="2026-05-01",
    ),
    GP(
        id="semil-shah",
        name="Semil Shah",
        firm="Haystack",
        role="Founder & General Partner",
        focus_areas=["Consumer", "Enterprise SaaS", "Fintech", "Healthcare"],
        stage=["Pre-Seed", "Seed"],
        geography=["US"],
        fund_size_m=180,
        aum_m=450,
        portfolio_highlights=["DoorDash", "Instacart", "HashiCorp", "Gusto"],
        notable_exits=["DoorDash (IPO)", "HashiCorp (acq. $6.4B)", "Instacart (IPO)"],
        bio=(
            "Solo GP who built Haystack from scratch to a top seed fund. "
            "Previously venture partner at GGV and investor at Bullpen Capital. "
            "Known for deep conviction investing and backing repeat founders."
        ),
        status="committed",
        tags=["seed-specialist", "solo-gp", "high-conviction", "diverse-gp"],
        twitter="@semil",
        website="https://haystack.vc",
        fit_score=8,
        added_date="2025-11-01",
        last_contacted="2026-06-01",
        notes=["Committed to Haystack Fund IV at $3M allocation — strong seed-stage differentiation"],
    ),
    GP(
        id="alex-zukin",
        name="Alex Zukin",
        firm="Meritech Capital",
        role="Partner",
        focus_areas=["Enterprise SaaS", "Cloud Infrastructure", "AI/ML"],
        stage=["Series B", "Series C", "Growth"],
        geography=["US"],
        fund_size_m=1100,
        aum_m=5000,
        portfolio_highlights=["Snowflake", "HashiCorp", "Figma", "UiPath", "Zendesk"],
        notable_exits=["Snowflake (IPO, $33B)", "UiPath (IPO)", "Zendesk (acq. $10.2B)"],
        bio=(
            "Former equity research analyst at RBC before joining Meritech. "
            "Brings deep public markets perspective to late-stage private investing. "
            "Focus on enterprise software with strong distribution and network effects."
        ),
        status="passed",
        tags=["enterprise-saas", "growth-stage", "ai-ml", "cloud"],
        fit_score=6,
        added_date="2026-04-20",
        notes=["Fund size ($1.1B) is above our target range — revisit for growth-stage allocation"],
    ),
]

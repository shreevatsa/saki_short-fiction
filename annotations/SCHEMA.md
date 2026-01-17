## Story annotations schema

This repo contains **142** Saki short-fiction items (as listed in `src/epub/toc.xhtml`, excluding front/back matter).

`annotations/stories.json` is the authoritative annotations file (easy to edit without CSV column drift).

`annotations/stories.csv` may exist as an optional/legacy export; prefer JSON going forward.

### JSON fields

- `index` (number): 1-based index in TOC order.
- `title` (string): story title (as shown in the TOC).
- `href` (string): relative path from `src/epub/` (e.g. `text/the-open-window.xhtml`).
- `rating_story` (number|null): how good it is *as a story* (`1`–`5`, or `null` if unrated).
- `tone` (string|null): `funny` | `serious` | `mixed` (or `null` if unknown).
- Theme fields (boolean|null): `true`/`false`/`null` (unset).
  - `theme_children_triumph`: children triumphing over adults.
  - `theme_animals`: wild/animals making themselves felt.
  - `theme_child_lies`: a child making up stories / lying.
  - `theme_trickster`: a clever trickster (often Reginald/Clovis) outwits others.
  - `theme_comeuppance`: ironic comeuppance / poetic justice.
  - `theme_supernatural`: supernatural/uncanny element.
  - `theme_social_satire`: social/class satire as a primary driver.
  - `theme_meddling_aunt_guardian`: meddling/tyrannical aunt or guardian.
  - `theme_hoax_practical_joke`: practical joke / hoax / engineered misunderstanding.
  - `theme_etiquette_weapon`: social etiquette used as a weapon/trap.
  - `theme_snobbery_status_anxiety`: snobbery/status anxiety as a major driver.
  - `theme_hypocrisy_respectability`: “respectability”/earnestness revealed as hypocrisy.
  - `theme_philanthropy_backfires`: charity/do-gooding backfires.
  - `theme_country_house_politics`: country-house / weekend-visit / house-party politics.
  - `theme_gossip_scandal_reputation`: gossip/scandal/reputation management.
  - `theme_exotic_elsewhere_disruption`: outsider/foreigner/exotic “elsewhere” disrupts.
  - `theme_sudden_darkness_punchline`: sudden darkness/violence as punchline/turn.
- `themes_other` (string[]|null): optional extra themes/tags.
- `notes` (string|null): optional notes (can include spoilers).

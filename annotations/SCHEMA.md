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
- `setting` (string|null): `london_town` | `country_house` | `rural_village` | `colonial_outpost` | `foreign_abroad` | `historical_pastiche` (or `null` if unknown).
- `ending_type` (string|null): `twist_reveal` | `ironic_reversal` | `dark_punchline` | `comic_deflation` | `open_ended` (or `null` if unknown).
- `darkness_level` (number|null): overall grimness/violence (`1`–`5`, or `null` if unknown).
- `body_count` (number|null): approximate number of deaths in-story (usually `0`).
- `central_mechanism` (string|null): primary plot engine, e.g. `hoax` | `misunderstanding` | `wager_bet` | `animal_intrusion` | `blackmail_reputation` | `bureaucratic_absurdity` | `storytelling_imagination` | `monologue_essay` (or `null` if unknown).
- `protagonist_type` (string|null): `child` | `trickster` | `society_adult` | `outsider_naif` | `professional_clergy_military` | `ensemble` (or `null` if unknown).
- `agency_driver` (string|null): who “wins” the plot: `child` | `trickster` | `adult_authority` | `animal` | `chance` (or `null` if unknown).
- `recurring_character` (string[]|null): optional recurring character tags (e.g. `clovis`, `reginald`, `comus`).
- `social_target` (string[]|null): what’s being skewered: `snobbery` | `philanthropy` | `politics` | `religion` | `domesticity` | `aestheticism` | `respectability`.
- `constraint_pressure` (string[]|null): what constrains characters: `etiquette` | `money` | `family_guardianship` | `reputation` | `career_politics`.
- Theme fields (boolean|null): `true`/`false`/`null` (unset).
  - `theme_children_triumph`: children triumphing over adults.
  - `theme_animals`: wild/animals making themselves felt.
  - `theme_animals_triumph`: animals/wild have their triumph (animals decisively “win” or determine the outcome).
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

## Story annotations schema

This repo contains **142** Saki short-fiction items (as listed in `src/epub/toc.xhtml`, excluding front/back matter).

`annotations/stories.csv` is intended to be edited by hand (spreadsheet-friendly).

### Columns

- `index`: 1-based index in TOC order.
- `title`: story title (as shown in the TOC).
- `href`: relative path from `src/epub/` (e.g. `text/the-open-window.xhtml`).
- `rating_story`: how good it is *as a story* (suggested scale: `1`–`5`, blank if unrated).
- `tone`: `funny` | `serious` | `mixed` (blank if unknown).
- `theme_children_triumph`: `y`/`n` — children triumphing over adults.
- `theme_animals`: `y`/`n` — wild/animals making themselves felt.
- `theme_child_lies`: `y`/`n` — a child making up stories / lying.
- `theme_trickster`: `y`/`n` — a clever trickster (often Reginald/Clovis) outwits others.
- `theme_comeuppance`: `y`/`n` — ironic comeuppance / poetic justice.
- `theme_supernatural`: `y`/`n` — supernatural/uncanny element.
- `theme_social_satire`: `y`/`n` — social/class satire as a primary driver.
- `theme_meddling_aunt_guardian`: `y`/`n` — meddling/tyrannical aunt or guardian.
- `theme_hoax_practical_joke`: `y`/`n` — practical joke / hoax / engineered misunderstanding.
- `theme_etiquette_weapon`: `y`/`n` — social etiquette used as a weapon/trap.
- `theme_snobbery_status_anxiety`: `y`/`n` — snobbery/status anxiety as a major driver.
- `theme_hypocrisy_respectability`: `y`/`n` — “respectability”/earnestness revealed as hypocrisy.
- `theme_philanthropy_backfires`: `y`/`n` — charity/do-gooding backfires.
- `theme_country_house_politics`: `y`/`n` — country-house / weekend-visit / house-party politics.
- `theme_gossip_scandal_reputation`: `y`/`n` — gossip/scandal/reputation management.
- `theme_exotic_elsewhere_disruption`: `y`/`n` — outsider/foreigner/exotic “elsewhere” disrupts.
- `theme_sudden_darkness_punchline`: `y`/`n` — sudden darkness/violence as punchline/turn.
- `themes_other`: free-text (comma-separated) for any other themes.
- `notes`: free-text notes (plot/characters/highlights).

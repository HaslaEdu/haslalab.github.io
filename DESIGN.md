# HaslaLab design history

The design published on 2026-10-30 uses the existing sky-blue graph paper and original H logo in light mode, and black with pale purple accents in dark mode. The home page keeps the original experiment animation and home copy, followed by live community posts/notices and native archive cards. Community, account, ranking, learning and exam workflows keep their existing layouts and behavior.

The previous production design is preserved in [`codex/design-before-refresh-20261030`](https://github.com/HaslaEdu/haslalab.github.io/tree/codex/design-before-refresh-20261030), at commit [`f010af3fb1cc45d137db1af662077fa3f24d2f9d`](https://github.com/HaslaEdu/haslalab.github.io/commit/f010af3fb1cc45d137db1af662077fa3f24d2f9d). That branch contains the complete site and assets from immediately before the refresh, so it can be compared or used to restore the earlier presentation without relying on a local preview.

`site-design.css` contains the shared colors, responsive header, avatar alignment and home presentation. `site-design.js` composes the home from the original experiment and archive renderers, loads public activity through the existing API, and stores only the appearance preference under `hlTheme`. Update `SITE_UPDATES` when publishing archive changes; its entries describe actual repository changes, while notices come from the community API.

The local design preview's sample account, cached posts, read-only API replacements and preview toolbar are not included in production.

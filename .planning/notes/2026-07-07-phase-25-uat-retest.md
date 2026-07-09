---
date: "2026-07-07 15:25"
promoted: false
---

During Phase 25 UAT retest (paused job): if you blur the Title input right after creating a person inline, the new person persists as chosen, but the match itself isn't actually saved until you save the row — so a page refresh loses the "resolved" state (though the newly created person does still show up in the dropdown to re-select). This is expected current behavior, but user is warming to the idea that inline person creation should also persist the match immediately rather than requiring a separate save.

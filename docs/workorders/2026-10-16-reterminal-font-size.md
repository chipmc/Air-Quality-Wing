# reTerminal distance readability — 16 October 2026

Request: increase the smallest fonts for easier reading at a distance.

Changes: minimum text size increased from 12 to 16 points. Panel subtitles
increase from 13 to 16, trend details from 17 to 20, category labels from 23
to 25, and panel headings from 25 to 28. The large readings, colours,
measurements, polling, credentials and startup launcher are unchanged.

Validation: all 19 local display/setup unit tests passed. Physical readability and clipping at
1280×720 require owner validation after deployment. No hardware deployment yet.

Deployment: after the OS package upgrade finishes, copy only
`display/reterminal/air_quality_display.py` to `~/air-quality-display/` on the
reTerminal and reboot. Preserve its local rotation-customized launcher.


## Follow-up: units beside readings

Moved each units label into the reading row, to the right of the number. Increased
the normal number size at 1280 pixels wide from approximately 134 to 160 points.
Both panels share one font, reduced together if the readings and units would
exceed panel width. Resizing and new readings recalculate the fit. The earlier
minimum label sizes remain unchanged. No API or startup changes.

Validation: all 19 existing tests, diff whitespace checks, and Python 3.7 syntax
compatibility passed; physical layout/readability remains an owner check on the reTerminal. Copy only the app file to preserve the local launcher.

# FBref secondary-source audit

The completion script attempted the FBref schedule endpoints for K League 1, A-League and Liga MX for seasons 2021–2024 with a browser-like User-Agent. In this run the endpoints returned Cloudflare/403 or empty HTML, so **no FBref response was accepted as match data**.

This directory intentionally contains no fabricated CSV. The accepted fallback files are under `data/raw/secondary/openfootball/` and are raw Football.TXT files from the public `openfootball/world` repository. They contain real FT scores; the completion policy stores HT as `null` for the added catalog rows.

K League 1 was not added because a complete, reproducible four-season export could not be verified in this run.

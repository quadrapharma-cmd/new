# Floorplan plugin (vendored copy)

Copy of https://github.com/haydenschmitty/floorplan v0.11.0, commit 94f81b463b7617e06d873ac71323ce71644c8399 (MIT, see LICENSE).
Only the plugin manifests and the skill are kept (no docs, images or tests). The cloud environment's setup script installs it
from this folder, so new sessions do not download it from GitHub:

    claude plugin marketplace add ./tools/claude-plugins/floorplan
    claude plugin install floorplan@floorplan

To update: copy a newer release over this folder and update the commit above.

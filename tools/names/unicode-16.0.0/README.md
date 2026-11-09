# Unicode security data (UTS #39) and Arabic joining data, version 16.0.0 — vendored

Used by `tools/names/name_rule.mjs` to generate the name rule of migrations 0038, 0039_names_rule_2, 0039_names_rule_3,
0039_names_rule_4 … 0039_names_rule_9 (its second to ninth versions) and of the live app (`web/src/live/adapter.js`). `tools/names/pixel-twins.txt`
(next to this folder, not Unicode data) adds the letters — and, since the fourth version, the marks, and since the fifth a letter + mark
(ģ / ġ) — that draw alike in the app's font stacks and the system fonts at weights 400-700 (`tools/names/render_scan.py`) while TR39
keys them apart.
Do not edit these files; to move to a newer Unicode version, vendor the new files into a new folder and write a new migration.

| File | Version | Date in the file | SHA-256 |
|---|---|---|---|
| `IdentifierStatus.txt` | 16.0.0 | 2024-05-04 | `c6108ca140e054b55a5b0378e7ebed8b1ef0e846251f6195361bc9af8ffc61b1` |
| `confusables.txt` | 16.0.0 | 2024-08-14 | `95bd0aad6dced5ebc63436f459c06ab21a8d107cd842fb57f5c3a1e91bca8611` |
| `ArabicShaping.txt` | 16.0.0 | 2024-07-30 | `764f420cedfc8b43d9fec251c957a5d55fc45d40f6573f162990ed1dce7e36e0` |

Source: the Unicode Consortium's security data for UTS #39 (https://www.unicode.org/Public/security/16.0.0/), copied
byte-for-byte from the Unicode Consortium's own repository `unicode-org/unicodetools`, `unicodetools/data/security/16.0.0/`
(commit 578f6c05), which holds the published files. `ArabicShaping.txt` (ninth version: the joining type of each Arabic
letter — where ى / ں take their final form — and the letter a hamza / madda / wasla form is written on) is the Unicode Character
Database file of the same release, copied byte-for-byte from `unicodetools/data/ucd/16.0.0/` at the same commit.

Licence: © 2024 Unicode®, Inc. Distributed under the Unicode License v3 (Unicode Terms of Use,
https://www.unicode.org/terms_of_use.html and https://www.unicode.org/license.txt), which allows copying and redistributing the
data files provided the copyright and permission notice is kept — it is kept in each file's header.

The Unicode version must match the one built into Node (`process.versions.unicode`, Node 22 = 16.0); the generator refuses to
run otherwise.

---
name: nafes
description: >-
  نافس — the owner's simple Arabic way to start the arena tournament. Use
  whenever the user writes «نافس» or «نافس على ...», «خليهم يتنافسوا»,
  «اعملها مسابقة», «عايز أحسن إجابة», «دي مش عاجباني، حاول أحسن», or any
  Arabic request to make several versions compete on a task. Runs the arena
  skill with 100 competitors (16 when the user says «سريعة») and no flags for
  the user to remember, and reports back in Egyptian Arabic.
argument-hint: "<المهمة بالعربي>"
---

# نافس

A thin front door for the `arena` skill, made for a user who should never have to type flags.

What the user wrote: `$ARGUMENTS`

## What to do

1. **The task.** Everything the user wrote after «نافس» / «نافس على» is the task, in their words.
   If they wrote nothing else (just «نافس», or «خليهم يتنافسوا» right after an answer), the task
   is their most recent request in this conversation and your last answer to it is the baseline
   to beat.
2. **The size.** 100 competitors by default (`--agents 100`, about 595 sub-agent calls), as the
   arena repository intends. Use `--quick` (16, about 91 calls) only when the user says so in
   words, such as «سريعة» or «16». Never ask about flags or seeds.
3. **No extra question.** The user asked for the competition by saying «نافس», so do not ask
   "are you sure". Tell them in one Arabic line, for example:
   «بدأت: 100 نسخة هيتنافسوا على المهمة، 7 جولات.» If permission prompts will appear for every
   file, add one short line: «لو طلعتلك طلبات موافقة كتير، دوس Shift+Tab مرة.»
4. **Run it.** Follow `.claude/skills/arena/SKILL.md` exactly, from Step 2 (task file) to Step 5,
   with the size from point 2. The tool is `python3 .claude/skills/arena/bracket.py <command>`, run from the
   project root. Write `.arena/task.md` in the user's language and words, standing on its own,
   with every requirement from the conversation; add nothing of your own.
5. **Progress.** After each round one Arabic line only: «خلصت الجولة 2: فاضل 25 من 100.»
6. **The result, in Egyptian Arabic, short:**
   - الإجابة الفايزة كاملة (in the language the task asked for).
   - ليه كسبت: two or three short points, from the attacks it survived.
   - لو كان فيه إجابة قديمة: قارنها بأمانة، ولو القديمة أحسن قول كده.
   - لو الإجابة فيها تعديل على ملفات المشروع: ما تطبّقهاش، اسأل «أطبّقها؟».

Keep every arena rule: you only run the tournament, you never judge, and sub-agents write only
inside `.arena/`.

"""Claude inside the program (the «decide» stage): the decisions its rules cannot make, made by Claude through the Claude API and
written to the decisions file as a person's would be. brain (the conversation, the budget), case (what Claude reads), store (what
it writes, checked), tasks (the playbook, the tools, the case files), run (the order, and the stages made again)."""
from .run import TASKS, run  # noqa: F401

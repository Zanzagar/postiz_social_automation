<!--
grill-gate (claude-harness docs/git-hygiene.md, rule 14). With squash merges set
to "Pull request title and description", this description IS the squashed
commit's message, and CI checks it like one before the merge. Its LAST paragraph
must be the trailer: keep the Decided line and point it at the recorded decision
this pull request implements, or replace it with ONE of
  Fix: <why>   Docs: <why>   Chore: <why>   Test: <why>
Co-Authored-By lines may sit in the same paragraph. No blank line inside it.
-->

## What and why



Decided: <repo-path>#<anchor>

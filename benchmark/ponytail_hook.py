"""Install Ponytail into the Codex Docker home mount used by SlopCodeBench.

Deprecated shim: prefer `benchmark.skill_hook`.
"""

from __future__ import annotations

from benchmark.skill_hook import install_skill_hook, uninstall_skill_hook

install_ponytail_hook = install_skill_hook
uninstall_ponytail_hook = uninstall_skill_hook

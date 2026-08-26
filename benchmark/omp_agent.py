"""Omp (oh-my-pi) CLI agent adapter for SlopCodeBench.

The ``omp`` binary is flag-compatible with the vendored ``pi`` adapter
(``--print --mode json --no-session --provider --model --thinking``), so this
module subclasses :class:`PiAgent` and only changes:

- binary name and Docker image payload (npm package ``@oh-my-pi/pi-coding-agent``);
- the agent-state directory (``~/.omp/agent`` instead of ``~/.pi/agent``;
  ``PI_CODING_AGENT_DIR`` relocates the omp base dir, so no bind mount and no
  host-side credential copying are needed);
- provider-id allowlist (adds ``opencode-zen``, ``opencode-go``, ``cursor``,
  ``gitlab-duo``, ``gitlab-duo-agent`` unknown to the upstream pi mapping).

Credentials are resolved by SCB through a normal env-var provider
(``omp_auth`` -> ``OPENCODE_API_KEY``), registered below so no vendor file
changes are needed.
"""

from __future__ import annotations

import typing as tp
from pathlib import Path

from slop_code.agent_runner.agents.pi import PiAgent, PiConfig
from slop_code.agent_runner.agents.utils import HOME_PATH
from slop_code.agent_runner.credentials import CredentialType, ProviderCatalog, ProviderDefinition
from slop_code.agent_runner.registry import register_agent

BENCHMARK_ASSETS = Path(__file__).resolve().parent / "assets"

# omp provider ids accepted in configs/agent_omp.yaml (`provider:` field).
_OMP_PROVIDER_IDS = frozenset(
    {
        "opencode-zen",
        "opencode-go",
        "cursor",
        "gitlab-duo",
        "gitlab-duo-agent",
    }
)


def _ensure_omp_auth_provider() -> None:
    """Register the ``omp_auth`` env-var credential provider once."""
    ProviderCatalog.ensure_loaded()
    if "omp_auth" not in ProviderCatalog.list_providers():
        ProviderCatalog.register(
            ProviderDefinition(
                name="omp_auth",
                credential_type=CredentialType.ENV_VAR,
                env_var="OPENCODE_API_KEY",
                description=(
                    "opencode zen API key routed through the omp CLI "
                    "(export OPENCODE_API_KEY before launching)"
                ),
            )
        )


class OmpConfig(PiConfig, agent_type="omp"):
    """Configuration for :class:`OmpAgent` instances."""

    type: tp.Literal["omp"] = "omp"
    binary: str = "omp"
    version: str
    docker_template: Path = BENCHMARK_ASSETS / "omp.docker.j2"


class OmpAgent(PiAgent):
    """Agent implementation for the oh-my-pi (omp) CLI."""

    @staticmethod
    def _resolve_pi_provider(provider: str) -> str:
        if provider in _OMP_PROVIDER_IDS:
            return provider
        return PiAgent._resolve_pi_provider(provider)

    def setup(self, session) -> None:  # type: ignore[no-untyped-def]
        """PiAgent.setup contract, but with the omp state dir inside the image."""
        self._session = session
        self._environment = session.spec
        self._artifact_payloads = []
        self._tmp_dir = None
        self._pi_auth_dir = None
        # PI_CODING_AGENT_DIR relocates the ~/.omp/agent base; the directory is
        # created (and owned by user ``agent``) by benchmark/assets/omp.docker.j2.
        self._pi_agent_dir_env = f"{HOME_PATH}/.omp/agent"
        self._runtime = session.spawn(
            mounts={},
            env_vars={
                "HOME": HOME_PATH,
                "PI_CODING_AGENT_DIR": self._pi_agent_dir_env,
            },
            image=self._image,
            user="agent",
            disable_setup=True,
        )


_ensure_omp_auth_provider()

register_agent("omp", OmpAgent)

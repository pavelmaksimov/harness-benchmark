"""Omp (oh-my-pi) CLI agent adapter for SlopCodeBench.

The ``omp`` binary is flag-compatible with the vendored ``pi`` adapter
(``--print --mode json --no-session --provider --model --thinking``), so this
module subclasses :class:`PiAgent` and only changes:

- binary name and Docker image payload (prebuilt omp binary installed by
  ``benchmark/assets/omp.docker.j2``);
- the agent-state directory: the host ``~/.omp/agent`` dir (which holds the
  provider tokens installed inside pi, e.g. openrouter) is bind-mounted over
  the container ``~/.omp/agent``; ``PI_CODING_AGENT_DIR`` relocates the base;
- provider-id allowlist (adds ``opencode-zen``, ``opencode-go``, ``cursor``,
  ``gitlab-duo``, ``gitlab-duo-agent`` unknown to the upstream pi mapping).

Credentials come from the mounted pi auth store, so no env-var provider is
required; ``omp_auth`` stays registered for validation compatibility.
"""

import typing as tp
from pathlib import Path

from slop_code.agent_runner.agents.pi import PiAgent, PiConfig
from slop_code.agent_runner.agents.utils import HOME_PATH
from slop_code.agent_runner.credentials import CredentialType, ProviderCatalog, ProviderDefinition
from slop_code.agent_runner.registry import register_agent

BENCHMARK_ASSETS = Path(__file__).resolve().parent / "assets"
OMP_AGENT_HOST_DIR = Path.home() / ".omp" / "agent"

# omp provider ids accepted in configs/agent_omp.yaml (`provider:` field).
_OMP_PROVIDER_IDS = frozenset(
    {
        "openrouter",
        "opencode-zen",
        "opencode-go",
        "cursor",
        "gitlab-duo",
        "gitlab-duo-agent",
    }
)


def _ensure_omp_auth_provider() -> None:
    """Register the ``omp_auth`` pseudo-provider (marker-file credential)."""
    ProviderCatalog.ensure_loaded()
    if "omp_auth" in ProviderCatalog.list_providers():
        return
    marker = OMP_AGENT_HOST_DIR / ".scb-credential"
    if not marker.exists():
        OMP_AGENT_HOST_DIR.mkdir(parents=True, exist_ok=True)
        marker.write_text("omp tokens are read from the mounted ~/.omp/agent store\n")
    ProviderCatalog.register(
        ProviderDefinition(
            name="omp_auth",
            credential_type=CredentialType.FILE,
            file_path=str(marker),
            destination_key="OMP_AUTH_MARKER",
            description=(
                "routing alias for the omp CLI; tokens are read from the "
                "mounted host ~/.omp/agent store, not from this credential"
            ),
        )
    )


class OmpConfig(PiConfig, agent_type="omp"):
    """Configuration for :class:`OmpAgent` instances."""

    type: tp.Literal["omp"] = "omp"
    binary: str = "/tmp/agent_home/.local/bin/omp"
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
        """PiAgent.setup contract, with the omp state dir (tokens) mounted."""
        self._session = session
        self._environment = session.spec
        self._artifact_payloads = []
        self._tmp_dir = None
        self._pi_auth_dir = None
        # PI_CODING_AGENT_DIR relocates the ~/.omp/agent base; the directory is
        # created by benchmark/assets/omp.docker.j2 and the host agent-state dir
        # (~/.omp/agent with stored provider tokens) is mounted over it.
        self._pi_agent_dir_env = f"{HOME_PATH}/.omp/agent"
        mounts = {
            str(OMP_AGENT_HOST_DIR): {
                "bind": self._pi_agent_dir_env,
                "mode": "rw",
            },
        }
        self._runtime = session.spawn(
            mounts=mounts,
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

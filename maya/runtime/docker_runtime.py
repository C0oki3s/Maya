from __future__ import annotations

from pathlib import Path
from time import sleep
from typing import Any

import requests

try:
    import docker
except Exception:  # noqa: BLE001
    docker = None

from .runtime import Runtime, SandboxInfo


class DockerRuntime(Runtime):
    def __init__(self, image: str = "maya-sandbox:latest") -> None:
        self.image = image
        self._client = None
        if docker is not None:
            try:
                self._client = docker.from_env()
                self._client.ping()  # Verify daemon is reachable
            except Exception:  # noqa: BLE001
                self._client = None
        self._containers: dict[str, Any] = {}

    def create_sandbox(
        self,
        agent_id: str,
        auth_token: str,
        local_sources: list[str] | None = None,
        host_gateway: str = "host.docker.internal",
    ) -> SandboxInfo:
        if self._client is None:
            # Dry-run fallback for environments without Docker.
            return SandboxInfo(
                workspace_id=f"dryrun-{agent_id}",
                server_url="",
                auth_token=auth_token,
                agent_id=agent_id,
            )

        volumes = {}
        for src in local_sources or []:
            src_path = Path(src).resolve()
            if src_path.exists():
                volumes[str(src_path)] = {"bind": f"/workspace/{src_path.name}", "mode": "ro"}

        try:
            container = self._client.containers.run(
                self.image,
                detach=True,
                environment={
                    "SANDBOX_AUTH_TOKEN": auth_token,
                    "ADB_SERVER_SOCKET": f"tcp:{host_gateway}:5037",
                    "FRIDA_HOST": f"{host_gateway}:27042",
                    "COMPANION_HOST": f"{host_gateway}:9999",
                },
                ports={"8000/tcp": None, "8080/tcp": 8080},
                volumes=volumes,
                extra_hosts={"host.docker.internal": "host-gateway"},
                cap_add=["SYS_PTRACE"],
                security_opt=["seccomp=unconfined"],
                mem_limit="4g",
                nano_cpus=2_000_000_000,
            )
        except Exception:
            return SandboxInfo(
                workspace_id=f"dryrun-{agent_id}",
                server_url="",
                auth_token=auth_token,
                agent_id=agent_id,
            )
        self._containers[agent_id] = container

        # Initial delay before attempting service health checks.
        sleep(1)
        container.reload()
        mapped_port = (
            container.attrs.get("NetworkSettings", {}).get("Ports", {}).get("8000/tcp", [{}])[0].get("HostPort", "8000")
        )
        server_url = f"http://127.0.0.1:{mapped_port}"

        if not self._wait_for_health(server_url):
            self.destroy_sandbox(agent_id)
            return SandboxInfo(
                workspace_id=f"dryrun-{agent_id}",
                server_url="",
                auth_token=auth_token,
                agent_id=agent_id,
            )

        if not self._register_agent(server_url, auth_token, agent_id):
            self.destroy_sandbox(agent_id)
            return SandboxInfo(
                workspace_id=f"dryrun-{agent_id}",
                server_url="",
                auth_token=auth_token,
                agent_id=agent_id,
            )

        return SandboxInfo(
            workspace_id=container.id[:12],
            server_url=server_url,
            auth_token=auth_token,
            agent_id=agent_id,
        )

    def _wait_for_health(self, server_url: str) -> bool:
        retries = 30
        for _ in range(retries):
            try:
                r = requests.get(f"{server_url}/health", timeout=2)
                if r.status_code == 200:
                    return True
            except Exception:  # noqa: S110
                pass  # server not ready yet
            sleep(2)
        return False

    def _register_agent(self, server_url: str, auth_token: str, agent_id: str) -> bool:
        headers = {"Authorization": f"Bearer {auth_token}"}
        payload = {"agent_id": agent_id}
        try:
            r = requests.post(f"{server_url}/register_agent", json=payload, headers=headers, timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def destroy_sandbox(self, agent_id: str) -> None:
        container = self._containers.pop(agent_id, None)
        if container is None:
            return
        try:
            container.stop(timeout=10)
            container.remove()
        except Exception:
            return

    def destroy_all(self) -> None:
        for agent_id in list(self._containers.keys()):
            self.destroy_sandbox(agent_id)

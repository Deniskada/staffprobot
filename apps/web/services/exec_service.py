import os
import shlex
import subprocess
from typing import Tuple, Optional

from core.logging.logger import logger


class CommandExecutor:
    """Абстракция для выполнения команд локально или по SSH."""

    def run(self, command: str, timeout: int = 30) -> Tuple[int, str, str]:
        raise NotImplementedError

    def write_file(self, path: str, content: str, sudo: bool = True) -> Tuple[int, str, str]:
        raise NotImplementedError


class LocalExecutor(CommandExecutor):
    def run(self, command: str, timeout: int = 30) -> Tuple[int, str, str]:
        logger.info("[local] run", command=command)
        res = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
        return res.returncode, res.stdout, res.stderr

    def write_file(self, path: str, content: str, sudo: bool = True) -> Tuple[int, str, str]:
        try:
            # Локальная запись напрямую без shell
            dir_path = os.path.dirname(path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return 0, "written", ""
        except Exception as e:
            return 1, "", str(e)


class SSHExecutor(CommandExecutor):
    def __init__(self, host: str, user: Optional[str] = None, key_path: Optional[str] = None):
        self.host = host
        self.user = user
        self.key_path = key_path

    def _ssh_prefix(self) -> str:
        target = f"{self.user}@{self.host}" if self.user else self.host
        key = f"-i {shlex.quote(self.key_path)}" if self.key_path else ""
        return f"ssh -o StrictHostKeyChecking=no {key} {shlex.quote(target)}"

    def run(self, command: str, timeout: int = 30) -> Tuple[int, str, str]:
        ssh_cmd = f"{self._ssh_prefix()} {shlex.quote(command)}"
        logger.info("[ssh] run", command=command, host=self.host)
        res = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return res.returncode, res.stdout, res.stderr

    def write_file(self, path: str, content: str, sudo: bool = True) -> Tuple[int, str, str]:
        # Используем here-doc через SSH
        redir = "sudo tee" if sudo else "tee"
        cmd = f"bash -lc 'cat > {shlex.quote(path)} << \"EOF\"\n{content}\nEOF\n'"
        # Альтернативно через tee для корректных прав
        cmd = f"bash -lc 'cat << \"EOF\" | {redir} {shlex.quote(path)} > /dev/null\n{content}\nEOF'"
        return self.run(cmd)


def get_executor() -> CommandExecutor:
    """Выбор исполнителя: SSH при наличии переменных окружения, иначе локальный."""
    host = os.getenv("NGINX_REMOTE_HOST")
    if host:
        return SSHExecutor(
            host=host,
            user=os.getenv("NGINX_REMOTE_USER"),
            key_path=os.getenv("NGINX_REMOTE_KEY_PATH"),
        )
    return LocalExecutor()



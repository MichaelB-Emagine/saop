import argparse
import os
import subprocess
from pathlib import Path
import shutil
from tempfile import NamedTemporaryFile

# Defining the docker constants.
REPO_ROOT = Path(__file__).resolve().parents[1]

COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"

PROJECT_NAME = "saop"


def ensure_agent_exists(agent_name: str, entry_file: str = "main.py") -> Path:
    """
    Checks that agents/<agent_name> exists and contains entry_file.
    """
    agent_dir = REPO_ROOT / "agents" / agent_name
    if not agent_dir.is_dir():
        print(f"Error: {agent_dir} not found. Did you scaffold it?")
        raise SystemExit(1)
    entry = agent_dir / entry_file
    if not entry.exists():
        print(
            f"Warning: {entry} not found. Adjust your Dockerfile/CMD or template entry script."
        )
        raise SystemExit(1)
    return agent_dir


def require_docker() -> None:
    """
    Ensure Docker and Docker Compose v2 are available.
    Exits with a helpful message if not present.
    """
    if shutil.which("docker") is None:
        print("Error docker is not installed or not in PATH")
        raise SystemExit(1)
    try:
        subprocess.run(
            ["docker", "compose", "version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        print(
            "Error: 'docker compose' is not available. Install a Docker Desktop or the Compose Plugin"
        )
        raise SystemExit(1)


def run_compose(*args: str, env: dict | None = None, check: bool = True) -> int:
    """
    Build and run a 'docker compose' command with the fixed compose file and project name.
    Returns the process return code; raises on failure if check=True.
    """

    cmd = [
        "docker",
        "compose",
        "-f",
        str(COMPOSE_FILE),
        "-p",
        PROJECT_NAME,
        *args,
    ]
    completed = subprocess.run(cmd, env=env)
    if check and completed.returncode != 0:
        raise SystemExit(completed.returncode)
    return completed.returncode


def cmd_up(args: argparse.Namespace) -> None:
    """
    'saop up' -> start the stack.
    Supports --detach/-d, --build, and optional --profile.
    Writes a temp compose env-file that defines AGENT_NAME=<agent>,
    copies agents/<agent>/.env to project .agent.env (runtime env for the app),
    then invokes `docker compose ... --env-file <tempfile> up ...`.
    """
    require_docker()
    ensure_agent_exists(args.agent)

    # --- 1) Compose env-file with AGENT_NAME (used for variable interpolation) ---
    # On Windows, NamedTemporaryFile must be opened with delete=False so docker can read it.
    with NamedTemporaryFile("w", delete=False, dir=REPO_ROOT, encoding="utf-8") as tf:
        tf.write(f"AGENT_NAME={args.agent}\n")
        envfile_path = tf.name  # keep this path; we'll pass it to compose

    # --- 2) Copy the agent's runtime env into .agent.env for the app container ---
    src_env = REPO_ROOT / "agents" / args.agent / ".env"
    dst_env = REPO_ROOT / ".agent.env"
    if not src_env.is_file():
        print(f"Error: missing {src_env}")
        raise SystemExit(1)
    shutil.copyfile(src_env, dst_env)

    # --- 3) Prepare process environment for the compose subprocess ---
    env = os.environ.copy()
    env["AGENT_NAME"] = args.agent

    # --- 4) Build the compose args list ---
    compose_args = ["--env-file", envfile_path, "up"]
    if args.detach:
        compose_args.append("-d")
    if args.build:
        compose_args.append("--build")
    if args.profile:
        compose_args.extend(["--profile", args.profile])

    # --- 5) Helpful logs (show both sources of truth) ---
    print(f"AGENT_NAME for compose (process env): {env.get('AGENT_NAME')}")
    print(f"Compose env-file: {envfile_path}")
    try:
        # with open(envfile_path, "r", encoding="utf-8") as f:
        #     print("--- compose env-file contents ---\n" + f.read().rstrip() + "\n---------------------------------")
        pass
    except Exception:
        pass

    print(
        "Compose command:",
        [
            "docker",
            "compose",
            "-f",
            str(COMPOSE_FILE),
            "-p",
            PROJECT_NAME,
            *compose_args,
        ],
    )

    # --- 6) Run compose ---
    try:
        # If run_compose does NOT automatically prepend "-f ... -p ...",
        # change this to: run_compose("-f", str(COMPOSE_FILE), "-p", PROJECT_NAME, *compose_args, env=env, check=True)
        run_compose(*compose_args, env=env, check=True)
    finally:
        # Always clean the temp file (Windows keeps handles until we close the process)
        if os.path.exists(envfile_path):
            try:
                os.remove(envfile_path)
                print(f"Cleaned up temp env file: {envfile_path}")
            except OSError:
                print(f"Warning: could not remove temp env file: {envfile_path}")


def cmd_down(args: argparse.Namespace) -> None:
    """
    'saop down' -> stop and remove containers, and volumes (-v) for a clean slate.
    """
    require_docker()
    # Ensure .agent.env exists so compose can parse
    dst_env = REPO_ROOT / ".agent.env"
    if not dst_env.exists():
        # If an agent was provided, copy its env; else create an empty stub
        if args.agent:
            src_env = REPO_ROOT / "agents" / args.agent / ".env"
            if src_env.is_file():
                shutil.copyfile(src_env, dst_env)
            else:
                dst_env.touch()
        else:
            dst_env.touch()

    env = os.environ.copy()
    run_compose("down", "-v", env=env, check=True)


def cmd_logs(args: argparse.Namespace) -> None:
    """
    'saop logs' -> stream logs. If a service is provided, limit to that service.
    Use --follow/-f to follow.
    """
    require_docker()
    env = os.environ.copy()
    if args.agent:
        env["AGENT_NAME"] = args.agent
    compose_args = ["logs"]
    if args.follow:
        compose_args.append("-f")
    if args.service:
        compose_args.append(args.service)
    run_compose(*compose_args, env=env, check=False)


def cmd_ps(args: argparse.Namespace) -> None:
    """
    'saop ps' -> show container status for the project.
    """
    require_docker()
    env = os.environ.copy()
    if args.agent:
        env["AGENT_NAME"] = args.agent
    run_compose("ps", env=env, check=True)


# def scaffold_agent(agent_name: str):
#     """
#     Scaffolds a new agent directory from a template.

#     This function now simply copies the entire template directory,
#     ensuring all necessary files like graph.py are included.
#     """
#     # The template directory is relative to the location of this script.
#     template_dir = os.path.join(os.path.dirname(__file__), "templates/base_agent")
#     repo_root = os.path.abspath(
#         os.path.join(os.path.dirname(__file__), "..")
#     )  # points to repo root
#     agents_root = os.path.join(repo_root, "agents")
#     new_agent_dir = os.path.join(agents_root, agent_name)

#     if not os.path.exists(template_dir):
#         print(f"Error: Template directory '{template_dir}' not found.")
#         print(
#             "Please ensure you have a 'templates/base_agent' directory with your template files."
#         )
#         return

#     if os.path.exists(new_agent_dir):
#         print(f"Error: Directory '{new_agent_dir}' already exists.")
#         return

#     # Use shutil.copytree to copy the entire template directory recursively.
#     os.makedirs(agents_root, exist_ok=True)
#     shutil.copytree(template_dir, new_agent_dir)
#     print(f"Created new agent directory '{new_agent_dir}' from template.")

#     print("\n✅ New agent scaffolded successfully!")
#     print(f"To get started, navigate to the directory: cd {agent_name}")
#     print("Please fill in the placeholder values in your new '.env' and YAML files.")


def _resolve_template_dir(template_arg: str | None) -> str:
    """
    1) CLI arg (-t/--template): name or path
    2) SAOP_DEFAULT_TEMPLATE env var
    3) 'base_agent' fallback
    """
    base_dir = os.path.dirname(__file__)
    chosen = template_arg or os.getenv("SAOP_DEFAULT_TEMPLATE") or "base_agent"

    if os.path.isabs(chosen) or any(sep in chosen for sep in (os.sep, "/")):
        candidate = chosen  # treat as path
    else:
        candidate = os.path.join(base_dir, "templates", chosen)  # treat as name

    return os.path.abspath(candidate)


def scaffold_agent(agent_name: str, template: str | None = None):
    template_dir = _resolve_template_dir(template)
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    agents_root = os.path.join(repo_root, "agents")
    new_agent_dir = os.path.join(agents_root, agent_name)

    if not os.path.exists(template_dir):
        print(f"Error: Template directory '{template_dir}' not found.")
        print(
            "Tip: pass --template <name> (under ./templates/) or --template </abs/path>."
        )
        return

    if os.path.exists(new_agent_dir):
        print(f"Error: Directory '{new_agent_dir}' already exists.")
        return

    os.makedirs(agents_root, exist_ok=True)
    shutil.copytree(template_dir, new_agent_dir)
    print(f"Created '{new_agent_dir}' from template '{template_dir}'.")
    print("✅ Done. Next: cd agents/{agent_name} and review .env + agent.yaml")


def main():
    parser = argparse.ArgumentParser(description="SAOP CLI for agent orchestration.")
    subparsers = parser.add_subparsers(dest="command")

    scaffold_parser = subparsers.add_parser(
        "scaffold", help="Create a new agent from a template."
    )
    scaffold_parser.add_argument(
        "agent_name", type=str, help="The name of the new agent."
    )
    scaffold_parser.set_defaults(func=lambda a: scaffold_agent(a.agent_name))

    # Up command parser

    up_parser = subparsers.add_parser("up", help="Start the stack for a given agent.")
    up_parser.add_argument(
        "agent", help="Agent name under ./agents (used for mount/build)."
    )
    up_parser.add_argument(
        "-d", "--detach", action="store_true", help="Run in background."
    )
    up_parser.add_argument(
        "--build", action="store_true", help="Build images before starting."
    )
    up_parser.add_argument("--profile", type=str, help="Compose profile (optional).")
    up_parser.set_defaults(func=cmd_up)

    # New down command parser

    down_parser = subparsers.add_parser(
        "down", help="Stop and remove the stack (and volumes)."
    )
    down_parser.add_argument("--agent", help="Agent name.")
    down_parser.set_defaults(func=cmd_down)

    # New logs command parser

    logs_parser = subparsers.add_parser("logs", help="Show container logs.")
    logs_parser.add_argument("--agent", help="Agent name.")
    logs_parser.add_argument("service", nargs="?", help="Service to filter.")
    logs_parser.add_argument("-f", "--follow", action="store_true", help="Follow logs.")
    logs_parser.set_defaults(func=cmd_logs)

    # New PS command parser

    ps_parser = subparsers.add_parser("ps", help="List project containers.")
    ps_parser.add_argument("--agent", help="Agent name.")
    ps_parser.set_defaults(func=cmd_ps)

    scaffold_parser.add_argument(
        "-t",
        "--template",
        type=str,
        default=None,
        help="Template name under ./templates/<name> or a directory path.",
    )
    scaffold_parser.set_defaults(
        func=lambda a: scaffold_agent(a.agent_name, a.template)
    )

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

"""Shell completion script generators for kt studio."""

import argparse

from kohakuterrarium.utils.logging import get_logger

logger = get_logger(__name__)

STUDIO_SUBCOMMANDS = (
    "init launch apply profiles profile doctor "
    "sessions session statusline theme targets target copilot "
    "cost record replay compare completion diff"
)


def generate_bash_completion() -> str:
    """Generate bash completion script for kt studio."""
    return f'''\
# bash completion for kt studio
# Add to ~/.bashrc: eval "$(kt studio completion bash)"

_kt_studio_completions() {{
    local cur prev subcmds
    cur="${{COMP_WORDS[COMP_CWORD]}}"
    prev="${{COMP_WORDS[COMP_CWORD-1]}}"

    subcmds="{STUDIO_SUBCOMMANDS}"

    case "$prev" in
        studio)
            COMPREPLY=( $(compgen -W "$subcmds" -- "$cur") )
            return 0
            ;;
        profile)
            COMPREPLY=( $(compgen -W "create show edit delete" -- "$cur") )
            return 0
            ;;
        session)
            COMPREPLY=( $(compgen -W "name resume fork inspect delete export incognito" -- "$cur") )
            return 0
            ;;
        statusline)
            COMPREPLY=( $(compgen -W "install preview uninstall" -- "$cur") )
            return 0
            ;;
        theme)
            COMPREPLY=( $(compgen -W "list show apply" -- "$cur") )
            return 0
            ;;
        target)
            COMPREPLY=( $(compgen -W "status" -- "$cur") )
            return 0
            ;;
        copilot)
            COMPREPLY=( $(compgen -W "status model models patch unpatch" -- "$cur") )
            return 0
            ;;
        completion)
            COMPREPLY=( $(compgen -W "bash zsh fish powershell" -- "$cur") )
            return 0
            ;;
        launch|apply|--profile)
            local profiles
            profiles=$(kt studio profiles --names-only 2>/dev/null)
            COMPREPLY=( $(compgen -W "$profiles" -- "$cur") )
            return 0
            ;;
    esac

    if [[ "${{COMP_WORDS[1]}}" == "studio" && $COMP_CWORD -eq 2 ]]; then
        COMPREPLY=( $(compgen -W "$subcmds" -- "$cur") )
    fi
}}

complete -F _kt_studio_completions kt
'''


def generate_zsh_completion() -> str:
    """Generate zsh completion script for kt studio."""
    return f'''\
#compdef kt

# zsh completion for kt studio
# Add to ~/.zshrc: eval "$(kt studio completion zsh)"

_kt_studio() {{
    local -a subcmds
    subcmds=({STUDIO_SUBCOMMANDS})

    _arguments \\
        '1:command:(studio)' \\
        '*::arg:->args'

    case $state in
        args)
            case $words[1] in
                studio)
                    _arguments '1:subcommand:($subcmds)'
                    ;;
            esac
            ;;
    esac
}}

compdef _kt_studio kt
'''


def generate_fish_completion() -> str:
    """Generate fish completion script for kt studio."""
    subcmds = STUDIO_SUBCOMMANDS.split()
    lines = [
        "# fish completion for kt studio",
        "# Add to ~/.config/fish/completions/kt.fish",
        "",
        "# Disable file completion by default",
        "complete -c kt -f",
        "",
        "# Top-level: studio",
        "complete -c kt -n '__fish_use_subcommand' -a studio -d 'Manage AI coding CLI profiles'",
        "",
        "# Studio subcommands",
    ]
    descriptions = {
        "init": "Create default config",
        "launch": "Launch with profile",
        "apply": "Output merged settings",
        "profiles": "List profiles",
        "profile": "Manage a profile",
        "doctor": "Health checks",
        "sessions": "List sessions",
        "session": "Manage sessions",
        "statusline": "Manage status line",
        "theme": "Manage themes",
        "targets": "List targets",
        "target": "Manage target",
        "copilot": "Manage Copilot CLI",
        "cost": "Show API cost summary",
        "record": "Record CLI session",
        "replay": "Replay recorded session",
        "compare": "Compare targets",
        "completion": "Generate completions",
        "diff": "Compare two profiles",
    }
    for cmd in subcmds:
        desc = descriptions.get(cmd, cmd)
        lines.append(
            f"complete -c kt -n '__fish_seen_subcommand_from studio' -a {cmd} -d '{desc}'"
        )

    return "\n".join(lines) + "\n"


def generate_powershell_completion() -> str:
    """Generate PowerShell completion script for kt studio."""
    subcmds = STUDIO_SUBCOMMANDS.split()
    subcmd_list = ", ".join(f"'{s}'" for s in subcmds)
    return f'''\
# PowerShell completion for kt studio
# Add to $PROFILE: . (kt studio completion powershell)

Register-ArgumentCompleter -CommandName kt -ScriptBlock {{
    param($wordToComplete, $commandAst, $cursorPosition)

    $subcmds = @({subcmd_list})

    $subcmds | Where-Object {{ $_ -like "$wordToComplete*" }} | ForEach-Object {{
        [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
    }}
}}
'''


def handle_completion_command(args: argparse.Namespace) -> int:
    """CLI handler for 'kt studio completion'."""
    match args.shell:
        case "bash":
            print(generate_bash_completion())
        case "zsh":
            print(generate_zsh_completion())
        case "fish":
            print(generate_fish_completion())
        case "powershell":
            print(generate_powershell_completion())
        case _:
            print(f"Unsupported shell: {args.shell}")
            return 1
    return 0

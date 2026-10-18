"""The `plan help` and `plan shell-completion` commands.

Long-form usage text and the shell completion scripts, kept apart from the
command that does the work.
"""

from __future__ import annotations

import click

from scriptplan import __version__

__all__ = ["register"]


def register(cli: click.Group) -> None:
    """Attach the help and shell-completion commands to the CLI group."""

    @cli.command()
    def help() -> None:
        """
        Show detailed help and usage information.

        Displays comprehensive help including all available commands,
        common usage patterns, and examples.
        """
        help_text = (
            """
    ScriptPlan - Enterprise Project Planning Tool

    DESCRIPTION:
        ScriptPlan schedules projects written in the .tjp format. It provides
        scheduling, resource management, and reporting for managing complex
        projects.

    USAGE:
        plan [OPTIONS] COMMAND [ARGS]...

    COMMANDS:
        report      Generate reports from .tjp project files
        help        Show this detailed help message

    GLOBAL OPTIONS:
        -v, --version       Show version information
        --verbose           Enable verbose/debug output
        --quiet             Suppress non-error messages
        -h, --help          Show command help

    REPORT COMMAND:
        plan report [OPTIONS] <tjp-file>

        Generate scheduling reports in JSON or CSV format from .tjp project
        files.

        Options:
            --csv               Generate CSV output (default: JSON)
            -o, --output PATH   Specify output file path
            --force             Overwrite existing output files
            -h, --help          Show report command help

    EXAMPLES:
        # Generate JSON report from project file
        $ plan report project.tjp

        # Generate CSV report
        $ plan report --csv project.tjp

        # Save report to specific file
        $ plan report --output report.json project.tjp

        # Enable verbose output for debugging
        $ plan --verbose report project.tjp

        # Quiet mode (only show errors)
        $ plan --quiet report project.tjp

    OUTPUT FORMATS:
        JSON:
            Clean, structured data with no HTML metadata.
            Format: {"data": [...], "columns": [...], "report_id": "..."}

        CSV:
            Comma-separated values suitable for spreadsheet applications.
            First row contains column headers.

    EXIT CODES:
        0   Success
        1   File not found or invalid input
        2   Report generation failed
        3   Output file exists (use --force)

    ENVIRONMENT:
        PLAN_VERBOSE        Set to '1' to enable verbose output
        PLAN_OUTPUT_DIR     Default directory for output files

    TJP FILE REQUIREMENTS:
        Your .tjp file must contain at least one report definition:

        taskreport my_report "My Report" {
            formats json      # or csv
            columns id, start, end
        }

    MORE INFORMATION:
        Documentation: https://github.com/rodmena-limited/scriptplan
        Issues: https://github.com/rodmena-limited/scriptplan/issues

    VERSION:
        ScriptPlan """
            + __version__
            + """
    """
        )
        click.echo(help_text)


    @cli.command(name="shell-completion")
    @click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
    def shell_completion(shell: str) -> None:
        """
        Generate shell completion script.

        Outputs shell completion configuration for the specified shell.
        Add the output to your shell's configuration file to enable
        tab completion for the 'plan' command.

        \b
        Supported shells: bash, zsh, fish

        \b
        Examples:
            # Bash
            plan shell-completion bash >> ~/.bashrc

            # Zsh
            plan shell-completion zsh >> ~/.zshrc

            # Fish
            plan shell-completion fish > ~/.config/fish/completions/plan.fish
        """
        if shell == "bash":
            completion = """
    # plan bash completion
    _plan_completion() {
        local IFS=$'\\n'
        COMPREPLY=( $(env COMP_WORDS="${COMP_WORDS[*]}" \\
                         COMP_CWORD=$COMP_CWORD \\
                         _PLAN_COMPLETE=complete $1) )
        return 0
    }

    complete -F _plan_completion -o default plan
    """
        elif shell == "zsh":
            completion = """
    # plan zsh completion
    #compdef plan

    _plan() {
        local -a completions
        local -a completions_with_descriptions
        local -a response
        response=("${(@f)$( env COMP_WORDS="${words[*]}" \\
                            COMP_CWORD=$((CURRENT-1)) \\
                            _PLAN_COMPLETE="complete_zsh" \\
                            plan )}")

        for key descr in ${(kv)response}; do
          if [[ "$descr" == "_" ]]; then
              completions+=("$key")
          else
              completions_with_descriptions+=("$key":"$descr")
          fi
        done

        if [ -n "$completions_with_descriptions" ]; then
            _describe -V unsorted completions_with_descriptions -U
        fi

        if [ -n "$completions" ]; then
            compadd -U -V unsorted -a completions
        fi
        compstate[insert]="automenu"
    }

    compdef _plan plan
    """
        else:  # fish
            completion = """
    # plan fish completion
    complete -c plan -f -a "(env _PLAN_COMPLETE=complete_fish COMP_WORDS=(commandline -cp) COMP_CWORD=(commandline -t) plan)"
    """

        click.echo(completion)

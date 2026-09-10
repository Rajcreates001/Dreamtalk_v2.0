# Adapted from Letta (MemGPT) - Apache 2.0 License
import typer

from dreamtalk.brain.memory.core.letta_memory.cli.cli import server

app = typer.Typer(pretty_exceptions_enable=False)

# Register server as both the default command and as a subcommand
app.command(name="server")(server)


# Also make server the default when no command is specified
@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        # If no subcommand is specified, run the server
        server()

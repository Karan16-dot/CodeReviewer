import sys
from pathlib import Path

# Add src to the python path to resolve imports cleanly
sys.path.append(str(Path(__file__).parent / "src"))

from cli import InteractiveCLI

def main():
    cli = InteractiveCLI()
    cli.run()

if __name__ == "__main__":
    main()

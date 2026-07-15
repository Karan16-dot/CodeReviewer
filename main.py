import sys
from pathlib import Path

# Add src to the python path to resolve imports cleanly
sys.path.append(str(Path(__file__).parent / "src"))

def main():
    print("Claude Code Agent v0.1")

if __name__ == "__main__":
    main()

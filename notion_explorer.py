import argparse
import sys
import os

# Import CLI logic from cli/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cli'))

from notion_cli import (
    reset_db,
    analyze_notes,
    load_gemini_outputs,
    launch_gui
)

def main():
    parser = argparse.ArgumentParser(description="Notion Theme Explorer CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Reset DB from Notion notes and fetch missing metadata
    subparsers.add_parser(
        "reset_db",
        help="Reset and populate DB from Notion notes, fetch missing metadata",
        description="Integrate Notion notes, update the database with new IDs, and fetch missing metadata from the Notion API recursively."
    )

    # Analyze notes with Gemini
    analyze_parser = subparsers.add_parser(
        "analyze_notes",
        help="Analyze notes with Gemini and store results",
        description="Run Gemini analysis on all notes that have not yet been analyzed for the selected question version and model. Stores results in the database."
    )
    analyze_parser.add_argument("--questions_version", type=str, help="Question version to use (default: auto-detect latest)")

    # Load Gemini output JSONs into DB
    subparsers.add_parser(
        "load_outputs",
        help="Load Gemini output JSONs into DB",
        description="Scan the outputs directory for Gemini output JSON files and load their contents into the database."
    )

    # Launch the GUI
    subparsers.add_parser(
        "launch_gui",
        help="Start the interactive GUI",
        description="Start the web-based graphical user interface for exploring your notes and themes."
    )

    args = parser.parse_args()
    if args.command == "reset_db":
        reset_db()
    elif args.command == "analyze_notes":
        analyze_notes(questions_version=args.questions_version)
    elif args.command == "load_outputs":
        load_gemini_outputs()
    elif args.command == "launch_gui":
        launch_gui()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

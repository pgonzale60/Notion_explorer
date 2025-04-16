import argparse
import sys
import os

# Import CLI logic from cli/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cli'))

from notion_cli import (
    reset_db,
    analyze_notes,
    load_gemini_outputs,
    launch_gui,
    update_questions
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
    analyze_parser.add_argument("--from_date", type=str, help="Only analyze notes created/edited on or after this date (format: DD/MM/YYYY)")

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
    
    # Update questions in the database
    update_questions_parser = subparsers.add_parser(
        "update_questions",
        help="Update questions in the database",
        description="Updates the questions in the database from the questions JSON files for UI display."
    )
    update_questions_parser.add_argument("--version", type=str, help="Question version to update (default: all versions)")
    update_questions_parser.add_argument("--force", action="store_true", help="Force update even if version already exists in the database")

    args = parser.parse_args()
    if args.command == "reset_db":
        reset_db()
    elif args.command == "analyze_notes":
        analyze_notes(questions_version=args.questions_version, from_date=args.from_date)
    elif args.command == "load_outputs":
        load_gemini_outputs()
    elif args.command == "launch_gui":
        launch_gui()
    elif args.command == "update_questions":
        success, message = update_questions(
            version=args.version if hasattr(args, 'version') else None, 
            force_update=args.force if hasattr(args, 'force') else False
        )
        print(message)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

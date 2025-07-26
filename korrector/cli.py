import argparse

from korrector import korrect_all

def main():
    parser = argparse.ArgumentParser(description="Korrector CLI")
    parser.add_argument("db_path", help="Path to Komga database file")
    parser.add_argument("--backup", help="Directory to store database backup")
    parser.add_argument("--library", default="", help="path to komga library in filesystem")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without making changes")
    args = parser.parse_args()

    result = korrect_all(args.db_path, args.backup, args.library, args.dry_run)
    print(result)

if __name__ == "__main__":
    main()
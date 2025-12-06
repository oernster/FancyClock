import os
from pathlib import Path

def main():
    # Move one directory up from helper_scripts/
    project_root = Path(__file__).resolve().parent.parent

    translations_dir = project_root / "localization" / "translations"

    if not translations_dir.exists():
        print("ERROR: Expected directory not found:", translations_dir)
        return

    json_files = sorted([f.name for f in translations_dir.glob("*.json")])

    if not json_files:
        print("No JSON translation files found in:", translations_dir)
        return

    # Output file goes into project root (not helper_scripts)
    output_path = project_root / "supported_locales.txt"
    output_path.write_text("\n".join(json_files), encoding="utf-8")

    print("Found translation files:")
    for name in json_files:
        print(" ", name)

    print("\nWritten to:", output_path.resolve())


if __name__ == "__main__":
    main()

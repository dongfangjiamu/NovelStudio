#!/usr/bin/env python3
"""Create a reusable webnovel project scaffold from bundled templates."""

from __future__ import annotations

import argparse
import re
import shutil
from datetime import date
from pathlib import Path


def safe_name(text: str) -> str:
    text = text.strip()
    if not text:
        return "novel-project"
    text = re.sub(r'[\/:*?"<>|]+', '-', text)
    text = re.sub(r'\s+', '-', text)
    text = text.strip('-')
    return text or "novel-project"


def fill_placeholders(text: str, mapping: dict[str, str]) -> str:
    for key, value in mapping.items():
        text = text.replace('{{' + key + '}}', value)
    return text


def copy_tree(template_root: Path, output_root: Path, mapping: dict[str, str]) -> list[Path]:
    created: list[Path] = []
    for source in template_root.rglob('*'):
        relative = source.relative_to(template_root)
        target = output_root / relative
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix.lower() in {'.md', '.yml', '.yaml', '.txt'}:
            content = source.read_text(encoding='utf-8')
            target.write_text(fill_placeholders(content, mapping), encoding='utf-8')
        else:
            shutil.copy2(source, target)
        created.append(target)
    return created


def main() -> None:
    parser = argparse.ArgumentParser(description='Initialize a webnovel writing project folder.')
    parser.add_argument('--title', required=True, help='Novel title or working title')
    parser.add_argument('--out', required=True, help='Destination folder')
    parser.add_argument('--genre', default='待定', help='Genre or subgenre')
    parser.add_argument('--audience', default='待定', help='Target audience')
    parser.add_argument('--author', default='待定', help='Author or team name')
    parser.add_argument('--zip', action='store_true', help='Also create a zip archive next to the output folder')
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    template_root = script_dir.parent / 'assets' / 'project-kit'
    if not template_root.exists():
        raise SystemExit(f'Template folder not found: {template_root}')

    output_root = Path(args.out).resolve()
    if output_root.exists() and any(output_root.iterdir()):
        raise SystemExit(f'Output directory is not empty: {output_root}')
    output_root.mkdir(parents=True, exist_ok=True)

    mapping = {
        'NOVEL_TITLE': args.title,
        'GENRE': args.genre,
        'TARGET_AUDIENCE': args.audience,
        'AUTHOR_NAME': args.author,
        'DATE_CREATED': str(date.today()),
    }

    created = copy_tree(template_root, output_root, mapping)

    for extra_dir in ['chapters', 'volumes', 'notes', 'exports']:
        (output_root / extra_dir).mkdir(exist_ok=True)

    print(f'Created project scaffold: {output_root}')
    for item in created:
        print(f' - {item.relative_to(output_root)}')

    if args.zip:
        archive_base = output_root.parent / safe_name(output_root.name)
        archive_path = shutil.make_archive(str(archive_base), 'zip', root_dir=output_root.parent, base_dir=output_root.name)
        print(f'Created archive: {archive_path}')


if __name__ == '__main__':
    main()

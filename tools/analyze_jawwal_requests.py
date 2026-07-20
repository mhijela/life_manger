"""Analyze captured Jawwal Pay network events and print API summary."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

CAPTURE_FILE = Path(__file__).resolve().parent / 'jawwal_captured_requests.json'


def main() -> int:
    if not CAPTURE_FILE.exists():
        print(f'Missing capture file: {CAPTURE_FILE}')
        return 1

    data = json.loads(CAPTURE_FILE.read_text(encoding='utf-8'))
    events = data.get('events', [])

    by_path: dict[str, list[dict]] = defaultdict(list)
    for event in events:
        if event.get('type') == 'response':
            continue
        path = event.get('path') or event.get('url', '')
        by_path[path].append(event)

    print(f"Captured at: {data.get('captured_at')}")
    print(f"Total events: {len(events)}")
    print(f"Unique request paths: {len(by_path)}\n")

    for path, items in sorted(by_path.items(), key=lambda x: (-len(x[1]), x[0])):
        sample = items[0]
        print('=' * 70)
        print(f'{sample["method"]} {path}  (x{len(items)})')
        if sample.get('query'):
            print(f'  query: {sample["query"]}')
        if sample.get('post_data'):
            print(f'  body: {sample["post_data"][:500]}')

        for event in events:
            if event.get('type') != 'response':
                continue
            if event.get('path') == path and event.get('method') == sample['method']:
                print(f'  -> status {event.get("status")}')
                if event.get('body'):
                    print(f'  <- {str(event["body"])[:500]}')
                break

    return 0


if __name__ == '__main__':
    sys.exit(main())

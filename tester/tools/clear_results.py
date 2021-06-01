from sys import argv, exit
from pathlib import Path
from typing import Iterable

from tester.core.metrics import EncodingRunMetrics


def process(file, keep: [Iterable, None] = None, force=False):
    directory = Path(file)
    keep = keep or []
    if not directory.is_dir():
        raise FileNotFoundError(f"{file} is not a directory")
    files = [x for x in directory.glob("*.json")]
    if not files:
        raise FileNotFoundError(f"No metric files found in {argv[1]}")

    metrics = []
    for f in files:
        run_metrics = EncodingRunMetrics(f)
        for iten in keep:
            try:
                run_metrics[iten]
            except KeyError:
                if not force:
                    raise ValueError(f"Can't find {iten} in {f}")
        metrics.append(run_metrics)

    for m in metrics:
        temp = dict()
        for k in keep:
            try:
                temp[k] = m[k]
            except KeyError:
                continue
        m.clear()
        for x, y in temp.items():
            m[x] = y


if __name__ == '__main__':
    if len(argv) < 2:
        print()
        exit(1)
    try:
        kept = argv[2].split(",")
    except KeyError:
        kept = []

    forced = len(argv) >= 4

    try:
        process(argv[1], kept, forced)
    except (FileNotFoundError, ValueError) as e:
        print(e.args[0])
        exit(1)


"""Add root L3 reports from stored evidence; never creates model clients."""
import argparse
from experiments.common.routing_reports import write_routing_summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', required=True)
    parser.add_argument('--refresh', action='store_true', help='Replace only reporter-owned L3 summaries')
    args = parser.parse_args(argv)
    try:
        report = write_routing_summary(args.run_dir, refresh=args.refresh)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        parser.exit(1, f'Cannot summarize stored run: {exc}\n')
    c=report['coverage'];t=report['totals']
    print(f"L3 reports written: scored traces {c['read_traces']}/{c['planned_traces']}; events {t['candidate_batches']}; issues {sum(report['issue_counts'].values())}.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

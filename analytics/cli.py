import argparse
import json


def main() -> None:
    parser = argparse.ArgumentParser(description="CornerScout offline pipeline")
    parser.add_argument("command", choices=["ingest", "build", "train", "clean", "scr15", "features"])
    args = parser.parse_args()
    if args.command == "ingest":
        from analytics.io import ingest
        result = ingest()
    elif args.command == "build":
        from analytics.pipeline import build
        result = build()
    elif args.command == "train":
        from analytics.pipeline import train
        result = train()
    else:
        from analytics.pipeline import run_stage
        result = run_stage(args.command)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()

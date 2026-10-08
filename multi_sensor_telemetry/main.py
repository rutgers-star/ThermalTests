import argparse
import math
import time
from datetime import datetime

if __package__:
    from .multi_tmpsensor import MultiTMPSensors
else:
    from multi_tmpsensor import MultiTMPSensors


def main():
    parser = argparse.ArgumentParser(
        description="TMP100 multi-sensor telemetry. Default is multi-sensor mode."
    )
    parser.add_argument(
        "--address",
        type=lambda x: int(x, 0),
        default=0x4F,
        help="I2C address for --single (e.g. 0x4f or 79). Default: 0x4f",
    )
    parser.add_argument("--fake", action="store_true", help="Use simulated sensors (no I2C)")
    parser.add_argument(
        "--single",
        action="store_true",
        help="Read one sensor instead of scanning the TMP100 address range",
    )
    parser.add_argument("--channel", type=int, default=1, help="I2C bus number (default: 1)")
    parser.add_argument(
        "--list",
        action="store_true",
        help="Scan the TMP100 address range, print the addresses found, and exit",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Seconds between printed/logged rows (e.g. --interval 5). Default: 1.0",
    )
    parser.add_argument(
        "--csv",
        nargs="?",
        const="multi_tmp100_log.csv",
        metavar="FILE",
        help="Also append rows to a CSV file (default file: multi_tmp100_log.csv)",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=0,
        help="Stop after this many rows (0 = run until Ctrl-C). Default: 0",
    )
    args = parser.parse_args()

    if not math.isfinite(args.interval) or args.interval <= 0:
        parser.error("--interval must be finite and positive")
    if args.rows < 0:
        parser.error("--rows must be nonnegative")
    if not 0x48 <= args.address <= 0x4F:
        parser.error("--address must be between 0x48 and 0x4f")

    if args.list:
        _run_list(args)
    else:
        _run_multi(args, addresses=[args.address] if args.single else None)


def _run_list(args):
    sensors = MultiTMPSensors(use_fake=args.fake, channel=args.channel)
    try:
        addrs = sensors.get_addrs()
    except (ImportError, OSError, IOError) as exc:
        raise SystemExit(str(exc)) from exc
    finally:
        sensors.stop()

    if not addrs:
        raise SystemExit(f"No TMP100 sensors found on I2C bus {args.channel}.")
    print(f"Found {len(addrs)} TMP100 sensor(s) on I2C bus {args.channel}:")
    for addr in addrs:
        print(" ", hex(addr))


def _run_multi(args, addresses=None):
    sample = min(0.5, args.interval)
    sensors = MultiTMPSensors(use_fake=args.fake, channel=args.channel,
                              interval=sample, addresses=addresses)
    try:
        sensors.start()
        columns = [hex(s.addr) for s in sensors.get_sensors()]
        count = 0
        time.sleep(sample + 0.1)
        while True:
            latest = sensors.get_latest()
            print(latest, flush=True)
            if args.csv:
                row = {"timestamp": datetime.now().isoformat(timespec="milliseconds")}
                row.update({col: latest.get(col, "") for col in columns})
                sensors.write_csv([row], args.csv)
            count += 1
            if args.rows and count >= args.rows:
                break
            time.sleep(args.interval)
        if args.csv:
            print(f"wrote {count} row(s) to {args.csv}", flush=True)
    except KeyboardInterrupt:
        pass
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    finally:
        # A blocked hardware read can outlast the stop timeout; report it, do not traceback.
        try:
            sensors.stop()
        except TimeoutError as exc:
            raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()

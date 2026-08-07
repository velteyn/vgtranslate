"""Command-line entry point: ``python -m vgtranslate`` / ``vgtranslate``.

Subcommands:
  serve      run the RetroArch translation server in the foreground
  tray       run the system-tray app (Windows + Linux)
  bench      benchmark harness (see ``vgtranslate bench --help``)
  status     print engine availability + LLM connection status
  detect     probe local LLM endpoints and show detected settings
"""

from __future__ import annotations

import argparse
import logging
import socket
import sys

from . import __version__
from .benchmark.cli import main as bench_main

log = logging.getLogger("vgtranslate")


def _make_console_unicode_safe() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except Exception:
            pass


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def _enumerate_ips() -> list[str]:
    """All reachable non-loopback IPv4 addresses of this machine.

    Uses the hostname address list plus a local UDP "connect" (no packets are
    sent) to also capture the default-route interface, so both a LAN cable and
    a Wi-Fi adapter show up when present.
    """
    ips: set[str] = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127."):
                ips.add(ip)
    except OSError:
        pass
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        ip = probe.getsockname()[0]
        if not ip.startswith("127."):
            ips.add(ip)
        probe.close()
    except OSError:
        pass
    return sorted(ips)


def _print_serve_hint(config) -> None:
    host = config.server.host
    port = config.server.port
    box = "=" * 60
    if host in ("0.0.0.0", "::"):
        ips = _enumerate_ips()
        print(f"\n{box}")
        print(f"  vgtranslate {__version__} serving on port {port}")
        if ips:
            print("  Connect RetroArch on any device (Retroid, phone, PC) with:")
            for ip in ips:
                print(f"    AI Service URL: http://{ip}:{port}/")
        else:
            print(f"  Connect RetroArch with: http://<this-machine-ip>:{port}/")
        print(f"  (from this PC itself: http://localhost:{port}/)")
        print("  Then in RetroArch: Settings > AI Service > enable, set the URL,")
        print("  and bind the AI Service hotkey under Settings > Input > Hotkeys.")
        print(f"{box}\n")
    else:
        print(f"\nvgtranslate {__version__} serving on http://{host}:{port}")
        print(f"RetroArch AI Service URL: http://localhost:{port}/")
        if host in ("127.0.0.1", "localhost"):
            from .config import config_path

            print("NOTE: this server only listens on localhost, so devices on your network")
            print('(Retroid, phone) cannot reach it. Set server.host to "0.0.0.0" in')
            print(f"{config_path()} and restart to allow them.")
        print("Press Ctrl+C to stop.\n")


def cmd_serve(args) -> None:
    from .config import detect_llm, load_config, merge_llm_detected
    from .server import Server

    config = load_config(args.config) if args.config else load_config()
    if args.detect_llm and not config.llm.base_url:
        config.llm = merge_llm_detected(config.llm, detect_llm())
        from .config import save_config

        save_config(config)
    server = Server(config)
    server.start()
    _print_serve_hint(config)
    try:
        while True:
            import time

            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()


def cmd_tray(args) -> None:
    from .config import load_config
    from .tray_app import TrayApp

    config = load_config(args.config) if args.config else load_config()
    try:
        TrayApp(config).run()
    except ImportError as exc:
        sys.exit(f"tray app dependencies missing ({exc}); install with `pip install vgtranslate[tray]`")


def cmd_status(args) -> None:
    from .config import load_config
    from .mt import list_providers as list_mt
    from .ocr import list_providers as list_ocr

    config = load_config(args.config) if args.config else load_config()
    path = args.config or config_path()
    print(f"vgtranslate {__version__}")
    print(f"config: {path}")
    print(f"active profile: {config.active_profile} ({config.active().mode})")
    print("OCR engines:")
    for name, info in list_ocr().items():
        print(f"  {name:12} {'OK' if info['available'] else 'missing':8} {info['description']}")
    print("Translators:")
    for name, info in list_mt().items():
        print(f"  {name:12} {'OK' if info['available'] else 'missing':8} "
              f"frame={info['frame_capable']} {info['description']}")
    if config.llm.base_url:
        from .mt.openai_compat import OpenAICompatTranslator

        ok, detail = OpenAICompatTranslator(config.llm).check_connection()
        print(f"LLM: {config.llm.base_url} model='{config.llm.model}' -> {'reachable' if ok else 'NOT reachable'} ({detail})")
    else:
        print("LLM: not configured (run `vgtranslate serve --detect-llm` or set base_url)")


def cmd_detect(args) -> None:
    from .config import detect_llm

    result = detect_llm()
    print(f"base_url: {result.base_url or '(none found)'}")
    print(f"model:    {result.model or '(auto)'}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vgtranslate", description="Local-first RetroArch translator")
    parser.add_argument("--version", action="version", version=f"vgtranslate {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="run the translation server in the foreground")
    serve.add_argument("--config", type=str, default=None, help="path to config.json")
    serve.add_argument("--detect-llm", action="store_true", help="auto-detect a local LLM before serving")
    serve.add_argument("-v", "--verbose", action="store_true")
    serve.set_defaults(func=cmd_serve)

    tray = sub.add_parser("tray", help="run the system-tray app")
    tray.add_argument("--config", type=str, default=None, help="path to config.json")
    tray.set_defaults(func=cmd_tray)

    bench = sub.add_parser("bench", help="benchmark harness")
    bench.set_defaults(func=lambda args: bench_main([]))

    status = sub.add_parser("status", help="show engine availability")
    status.add_argument("--config", type=str, default=None, help="path to config.json")
    status.set_defaults(func=cmd_status)

    detect = sub.add_parser("detect", help="probe local LLM endpoints")
    detect.set_defaults(func=cmd_detect)

    return parser


def main(argv: list[str] | None = None) -> int:
    _make_console_unicode_safe()
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "bench":
        from .benchmark.cli import main as bench_main

        return bench_main(argv[1:])
    args = build_parser().parse_args(argv)
    if getattr(args, "verbose", False):
        _setup_logging(True)
    elif args.command in ("serve", "bench"):
        _setup_logging(False)
    args.func(args)
    return 0


def config_path():
    from .config import config_path as cp

    return cp()


if __name__ == "__main__":
    raise SystemExit(main())

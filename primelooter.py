import argparse
import logging
import sys
import asyncio
import time
import traceback
from api import primelooter, AuthException
from logging import LogRecord

def build_handler_filters(handler: str):
    def handler_filter(record: LogRecord):
        if hasattr(record, "block"):
            if record.block == handler:
                return False
        return True

    return handler_filter


stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.addFilter(build_handler_filters("console"))
file_handler = logging.FileHandler("primelooter.log")
file_handler.addFilter(build_handler_filters("file"))

logging.basicConfig(
    level=logging.INFO,
    # format="%(asctime)s [%(levelname)s] %(msg)s",
    format="{asctime} [{levelname}] {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[file_handler, stream_handler],
)

log = logging.getLogger()

def use_api(cookie_file, publisher_file):
    asyncio.run(primelooter(cookie_file, publisher_file))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Notification bot for the lower saxony vaccination portal")

    parser.add_argument(
        "-p",
        "--publishers",
        dest="publishers",
        help="Path to publishers.txt file",
        required=False,
        default="publishers.txt",
    )
    parser.add_argument(
        "-c",
        "--cookies",
        dest="cookies",
        help="Path to cookies.txt file",
        required=False,
        default="cookies.txt",
    )
    parser.add_argument(
        "-l",
        "--loop",
        dest="loop",
        help="Shall the script loop itself? (Cooldown 24h)",
        required=False,
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-d",
        "--debug",
        dest="debug",
        help="Print Log at debug level",
        required=False,
        action="store_true",
        default=False,
    )

    arg = vars(parser.parse_args())

    with open(arg["publishers"]) as f:
        publishers = f.readlines()
    publishers = [x.strip() for x in publishers]
    cookie_file = arg["cookies"]
    if arg["debug"]:
        log.level = logging.DEBUG

    while True:
        try:
            log.info("Starting Prime Looter\n")
            use_api(cookie_file, publishers)
            log.info("Finished Looting!\n")
        except AuthException as ex:
            log.error(ex)
            sys.exit(1)
        except Exception as ex:
            log.error(ex)
            traceback.print_tb(ex.__traceback__)
            time.sleep(60)
        else:
            if arg["loop"]:
                log.info("Loop Enabled, sleeping for 24 hours.")
                stream_handler.terminator = "\r"

                sleep_time = 60 * 60 * 24
                for time_slept in range(sleep_time):
                    m, s = divmod(sleep_time - time_slept, 60)
                    h, m = divmod(m, 60)
                    log.info(
                        f"{h:d}:{m:02d}:{s:02d} till next run...",
                        extra={"block": "file"},
                    )
                    time.sleep(1)

                stream_handler.terminator = "\n"

        if not arg["loop"]:
            break

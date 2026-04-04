import logging
import time
from datetime import datetime, timezone

from backend.services.ingest_service import process_one_strava_ingest_job
from backend.services.notification_service import send_daily_readiness


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

DAILY_READINESS_USER_ID = "sergey"
DAILY_READINESS_HOUR_UTC = 7


def maybe_send_daily_readiness() -> None:
    now = datetime.now(timezone.utc)

    if now.hour != DAILY_READINESS_HOUR_UTC:
        return

    sent = send_daily_readiness(DAILY_READINESS_USER_ID, for_date=now.date())

    if sent:
        logging.info("Daily readiness summary sent for %s", DAILY_READINESS_USER_ID)


def main() -> None:
    logging.info("Human Engine worker started")

    while True:
        try:
            maybe_send_daily_readiness()

            result = process_one_strava_ingest_job()

            if result.get("message") == "no pending jobs":
                logging.info("No pending jobs, sleeping 10s")
                time.sleep(10)
            else:
                logging.info("Processed job: %s", result)
                time.sleep(1)

        except Exception as e:
            logging.exception("Worker error: %s", e)
            time.sleep(5)


if __name__ == "__main__":
    main()
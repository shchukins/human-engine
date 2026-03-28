import logging
import time

from backend.services.ingest_service import process_one_strava_ingest_job


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def main() -> None:
    logging.info("Human Engine worker started")

    while True:
        try:
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

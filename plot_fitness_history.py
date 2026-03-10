import json
from urllib.request import urlopen

import matplotlib.pyplot as plt


API_URL = "http://127.0.0.1:8000/fitness/history/sergey?limit=120"
OUTPUT_PATH = "/srv/human-engine/fitness_history.png"


def main() -> None:
    with urlopen(API_URL) as response:
        payload = json.load(response)

    data = payload["data"]

    dates = [item["date"] for item in data]
    tss = [item["tss"] for item in data]
    fitness = [item["fitness"] for item in data]
    fatigue = [item["fatigue"] for item in data]
    freshness = [item["freshness"] for item in data]

    fig, ax1 = plt.subplots(figsize=(14, 7))

    ax1.plot(dates, fitness, label="Fitness")
    ax1.plot(dates, fatigue, label="Fatigue")
    ax1.plot(dates, freshness, label="Freshness")
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Signals")
    ax1.tick_params(axis="x", rotation=45)
    ax1.legend(loc="upper left")

    ax2 = ax1.twinx()
    ax2.bar(dates, tss, alpha=0.25, label="Daily TSS")
    ax2.set_ylabel("Daily TSS")

    plt.title("Human Engine - Fitness / Fatigue / Freshness")
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH, dpi=150)
    print(f"Saved chart to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

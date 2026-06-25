"""Call Center Simulation — Entry Point.

Runs the ticket processing simulation for each configured test case,
producing one output CSV per case.

Usage:
    python main.py <input_csv>
    python main.py tickets.csv
    python main.py tickets.csv --agents 3 5 7
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from call_center.services.csv_reader import TicketReader
from call_center.services.simulation_process import Simulation


logger = logging.getLogger(__name__)

DEFAULT_AGENT_CASES = [3, 5, 7]
OUTPUT_DIR = Path("output")


def setup_logging() -> None:
    """Configure logging with a clean, readable format."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-5s | %(message)s",
        datefmt="%H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Call Center Ticket Simulation"
    )
    parser.add_argument(
        "input_csv",
        type=str,
        help="Path to the input tickets CSV file",
    )
    parser.add_argument(
        "--agents",
        type=int,
        nargs="+",
        default=DEFAULT_AGENT_CASES,
        help="Number of agents for each test case (default: 3 5 7)",
    )

    return parser.parse_args()


async def run_all_cases(
    input_csv: str, agent_cases: list[int]
) -> None:
    """Run the simulation for each agent configuration.

    Args:
        input_csv: Path to the input tickets CSV file.
        agent_cases: List of agent counts to simulate.
    """
    reader = TicketReader(input_csv)

    for num_agents in agent_cases:
        output_file = OUTPUT_DIR / f"result_agents_{num_agents}.csv"

        logger.info(
            "=" * 50 + "\n  CASE: %d agents\n" + "=" * 50,
            num_agents,
        )

        # A fresh stream per case: the CSV is re-read lazily so only a
        # bounded number of tickets ever live in memory, no matter how
        # large the file is. Re-reading is negligible next to the 2–3s
        # simulated work per ticket.
        simulation = Simulation(
            tickets=reader.stream(),
            num_agents=num_agents,
            output_path=output_file,
        )
        await simulation.run()

    logger.info("All cases completed. Results in: %s/", OUTPUT_DIR)


def main() -> None:
    """Application entry point."""
    setup_logging()
    args = parse_args()

    try:
        asyncio.run(run_all_cases(args.input_csv, args.agents))
    except FileNotFoundError as e:
        logging.error(str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        logging.info("Simulation interrupted by user")
        sys.exit(130)


if __name__ == "__main__":
    main()
import argparse
import logging
import sys

from PySide6.QtWidgets import QApplication

from controller.main_controller import UIController
from ui.main_window import MainWindow


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="count", default=0)
    args = parser.parse_args()

    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = levels[min(args.verbose, len(levels) - 1)]
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    app = QApplication(sys.argv)
    window = MainWindow(UIController())
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

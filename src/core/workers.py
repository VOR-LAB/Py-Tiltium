from PySide6.QtCore import QThread, QObject, Signal
from hardware import device

class DeviceWorker(QObject):
    finished = Signal(object);

    def run(self):
        self.finished.emit(device.connect())

def start_worker(worker, on_finished):
    thread = QThread()
    worker.moveToThread(thread)

    thread.started.connect(worker.run)

    worker.finished.connect(on_finished)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)

    thread.finished.connect(thread.deleteLater)

    thread.start()
    return thread, worker

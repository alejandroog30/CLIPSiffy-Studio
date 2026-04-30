from PyQt6.QtCore import pyqtSignal, QThread, pyqtSignal

class CLIPSRunThread(QThread):
    """
    A background worker thread to execute the CLIPS engine asynchronously.
    It runs the engine in small chunks to allow for safe interruption (halting) 
    without blocking the main GUI thread.
    """
    signal_finished = pyqtSignal()
    signal_error = pyqtSignal(str)

    def __init__(self, env, steps=None, parent=None):
        super().__init__(parent)
        self.env = env
        self.steps = steps
        self.is_running = True

    def run(self):
        if self.steps is not None:
            try:
                self.env.run(self.steps)
            except Exception as e:
                if "rule firing limit reached" not in str(e).lower():
                    self.signal_error.emit(str(e))
                    return
            self.signal_finished.emit()
            
        else:
            chunk_size = 500
            
            while self.is_running:
                try:
                    fired = self.env.run(chunk_size)
                    
                    if fired == 0:
                        break
                        
                    pendientes = list(self.env.activations())
                    if len(pendientes) == 0:
                        break
                        
                except Exception as e:
                    if "rule firing limit reached" in str(e).lower():
                        continue 
                    else:
                        self.signal_error.emit(str(e))
                        return
                        
            self.signal_finished.emit()

    def stop(self):
        """Safely signals the thread to stop execution at the next chunk boundary."""
        self.is_running = False

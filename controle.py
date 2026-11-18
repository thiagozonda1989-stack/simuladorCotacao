"""Controle cooperativo compartilhado entre threads e processos."""
from multiprocessing import get_context
from time import monotonic


class ProcessingCancelled(RuntimeError):
    pass


class ProcessingControl:
    def __init__(self):
        context = get_context("spawn")
        self.ready = context.Event()
        self.ready.set()
        self.cancelled = context.Event()
        self.paused_at = None
        self.paused_seconds = 0.0

    def pause(self):
        if self.paused_at is None:
            self.paused_at = monotonic()
            self.ready.clear()

    def resume(self):
        if self.paused_at is not None:
            self.paused_seconds += monotonic() - self.paused_at
            self.paused_at = None
            self.ready.set()

    def cancel(self):
        self.cancelled.set()
        self.resume()

    def checkpoint(self):
        self.ready.wait()
        if self.cancelled.is_set():
            raise ProcessingCancelled("Processamento cancelado.")

    def elapsed(self, started, prior_paused=0.0):
        now = monotonic()
        paused_at = self.paused_at
        current_pause = now-max(paused_at, started) if paused_at is not None else 0.0
        return max(0.0, now-started-(self.paused_seconds-prior_paused)-current_pause)

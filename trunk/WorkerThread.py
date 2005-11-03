from threading import Thread
from Queue import Queue
from AppKit import *


class WorkerThread(Thread):

	def __init__(self):
		"""Create a worker thread. Start it by calling the start() method."""
		self.queue = Queue()
		Thread.__init__(self)

	def stop(self):
		"""Stop the thread a.s.a.p., meaning whenever the currently running
		job is finished."""
		self.working = 0
		self.queue.put(None)

	def scheduleWork(self, func, *args, **kwargs):
		"""Schedule some work to be done in the worker thread."""
		self.queue.put((func, args, kwargs))

	def run(self):
		"""Fetch work from a queue, block when there's nothing to do.
		This method is called by Thread, don't call it yourself."""
		self.working = 1
		while self.working:
			work = self.queue.get()
			if work is None or not self.working:
				break
			func, args, kwargs = work
			pool = NSAutoreleasePool.alloc().init()
			try:
				func(*args, **kwargs)
			finally:
			# delete all local references; if they are the last refs they
			# may invoke autoreleases, which should then end up in our pool
				del func, args, kwargs, work
				del pool
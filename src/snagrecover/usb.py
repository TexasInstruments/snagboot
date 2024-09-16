import usb
import platform
import weakref
import gc

class SnagbootUSBContext():
	"""
	This class manages USB device objects instanciated by calling
	usb.core.find(). It makes sure that all previous USB devices are
	unreferenced when a rescan is issued.

	This is necessary to dodge a bug in some versions of libusb for
	Windows, where two different root hubs are assigned the same bus
	number. This can happen when a reenumeration is issued on an existing
	libusb context. By returning only weak references to USB device
	objects, we can ensure that the underlying libusb context is destroyed
	and recreated every time an enumeration is performed.
	"""

	instance = None

	def finalizer(usb_ctx):
		for ref in usb_ctx.devices:
			del ref

	def get_context():
		if __class__.instance is None:
			__class__.instance = __class__()

		return weakref.proxy(__class__.instance)

	def rescan():
		if __class__.instance is not None:
			# delete what should be the last references to the underlying libusb context

			__class__.instance = None

			gc.collect()

		__class__.instance = __class__()
		return weakref.proxy(__class__.instance)

	def __init__(self):
		self.devices = list(usb.core.find(find_all=True))
		self.check_for_libusb_bug()
		self._finalizer = weakref.finalize(self, __class__.finalizer, self)

	def check_for_libusb_bug(self):
		"""
		sanity check: some versions of libusb on Windows sometime allocate the same bus number
		to two different root hubs. Check if this has happened and try to fix it if
		it has.
		"""
		if platform.system() != "Windows":
			return

		root_hubs = [dev for dev in self.devices if dev.parent is None]
		bus_numbers = set([dev.bus for dev in root_hubs])
		if len(root_hubs) > len(bus_numbers):
			raise ValueError("libusb bug detected! Two root hubs were assigned the same bus number! Please update libusb to a newer version and replace the dll provided by the 'libusb' Python package!")

	def find(self, **args):
		for dev in self.devices:
			tests = (hasattr(dev, key) and val == getattr(dev, key) for key, val in args.items())
			if all(tests):
				yield weakref.proxy(dev)


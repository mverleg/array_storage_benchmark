
import gzip
from base64 import urlsafe_b64encode, urlsafe_b64decode
from genericpath import getsize
from os import fsync, remove
from os.path import join
from pickle import dump as pkl_dump, load as pkl_load
from tempfile import mkdtemp
from time import time
from fortranfile import FortranFile
from json_tricks import dump as jt_dump, load as jt_load
from numpy import mean, array_equal, savetxt, loadtxt, frombuffer, save as np_save, load as np_load, savez_compressed, array, std
from scipy.io import savemat, loadmat
from imgarray import save_array_img, load_array_img


def sync(fh):
	"""
	This makes sure data is written to disk, so that buffering doesn't influence the timings.
	"""
	fh.flush()
	fsync(fh.fileno())


class TimeArrStorage(object):
	extension = 'data'
	
	def __init__(self, reps=100):
		self.save_times = []
		self.load_times = []
		self.storage_spaces = []
		self.reps = int(reps)
		self.paths = tuple(join(mkdtemp(), self.__class__.__name__.lower() + '{0:03d}.{1:s}'
			.format(k, self.extension)) for k in range(self.reps))
	
	@property
	def save_time(self):
		return mean(self.save_times)
	
	@property
	def load_time(self):
		return mean(self.load_times)
	
	@property
	def storage_space(self):
		return mean(self.storage_spaces)
	
	@property
	def save_time_std(self):
		return std(self.save_times)
	
	@property
	def load_time_std(self):
		return std(self.load_times)
	
	@property
	def storage_space_std(self):
		return std(self.storage_spaces)
	
	def __str__(self):
		return self.__class__.__name__
	
	def save(self, arr, pth):
		# implementations have to call `sync`!
		raise NotImplementedError
	
	def load(self, pth):
		raise NotImplementedError
	
	def time_save(self, arr):
		for pth in self.paths:
			t0 = time()
			self.save(arr, pth)
			self.save_times.append((time() - t0))
		self.storage_spaces = tuple(getsize(pth) for pth in self.paths)
	
	def time_load(self, ref_arr):
		arr = None
		for pth in self.paths:
			t0 = time()
			arr = self.load(pth)
			self.load_times.append((time() - t0))
		self.storage_spaces = tuple(getsize(pth) for pth in self.paths)
		for pth in self.paths:
			remove(pth)
		assert array_equal(arr, ref_arr), 'load failed for {0:}'.format(self)
	
	def log(self):
		print('{0:12s}  {1:8.6f}s  {2:8.6f}s  {3:6.0f}kb'.format(self, self.save_time, self.load_time, self.storage_space/1024.))


class Csv(TimeArrStorage):
	def save(self, arr, pth):
		with open(pth, 'w+') as fh:
			savetxt(fh, arr, delimiter=',')
			sync(fh)
	
	def load(self, pth):
		with open(pth, 'r') as fh:
			return loadtxt(fh, delimiter=',')


class CsvGzip(TimeArrStorage):
	def save(self, arr, pth):
		with gzip.open(pth, 'w+') as fh:
			savetxt(fh, arr, delimiter=',')
			sync(fh)
		
	def load(self, pth):
		with gzip.open(pth, 'r') as fh:
			return loadtxt(fh, delimiter=',')


class JSON(TimeArrStorage):
	def save(self, arr, pth):
		jt_dump(arr, pth, force_flush=True)
		
	def load(self, pth):
		return jt_load(pth)


class JSONGzip(TimeArrStorage):
	def save(self, arr, pth):
		jt_dump(arr, pth, compression=True, force_flush=True)
		
	def load(self, pth):
		return jt_load(pth)


class Binary(TimeArrStorage):
	#todo: this one is suspiciously slow
	def save(self, arr, pth):
		with gzip.open(pth, 'wb+') as fh:
			fh.write(b'{0:s} {1:d} {2:d}\n'.format(arr.dtype, *arr.shape))
			fh.write(arr.data)
			sync(fh)

	def load(self, pth):
		with gzip.open(pth, 'rb') as fh:
			dtype, w, h = str(fh.readline()).split()
			return frombuffer(fh.read(), dtype=dtype).reshape((int(w), int(h)))


class Pickler(TimeArrStorage):
	def save(self, arr, pth):
		with open(pth, 'wb+') as fh:
			pkl_dump(arr, fh)
			sync(fh)

	def load(self, pth):
		with open(pth, 'rb') as fh:
			return pkl_load(fh)


class PickleGzip(TimeArrStorage):
	def save(self, arr, pth):
		with gzip.open(pth, 'wb+') as fh:
			pkl_dump(arr, fh)
			sync(fh)

	def load(self, pth):
		with gzip.open(pth, 'rb') as fh:
			return pkl_load(fh)


class NPY(TimeArrStorage):
	extension = 'npy'
	def save(self, arr, pth):
		with open(pth, 'wb+') as fh:
			np_save(fh, arr, allow_pickle=False)
			sync(fh)
		
	def load(self, pth):
		return np_load(pth)


class NPYCompr(TimeArrStorage):
	extension = 'npz'
	def save(self, arr, pth):
		with open(pth, 'wb+') as fh:
			savez_compressed(fh, data=arr)
			sync(fh)
		
	def load(self, pth):
		return np_load(pth)['data']


class PNG(TimeArrStorage):
	def save(self, arr, pth):
		with open(pth, 'wb+') as fh:
			save_array_img(arr, pth, img_format='png')
			sync(fh)
			
	def load(self, pth):
		return load_array_img(pth)


class b64Enc(TimeArrStorage):
	def save(self, arr, pth):
		with open(pth, 'w+') as fh:
			fh.write(b'{0:s} {1:d} {2:d}\n'.format(arr.dtype, *arr.shape))
			fh.write(urlsafe_b64encode(arr.data))
			sync(fh)

	def load(self, pth):
		with open(pth, 'r') as fh:
			dtype, w, h = str(fh.readline()).split()
			return frombuffer(urlsafe_b64decode(fh.read()), dtype=dtype).reshape((int(w), int(h)))


class FortUnf(TimeArrStorage):
	# this implementation assumes float64
	def save(self, arr, pth):
		with FortranFile(pth, mode='wb+') as fh:
			for k in range(arr.shape[0]):
				fh.writeReals(arr[k, :], prec='d')  #todo: is this the correct index for fastness?
			sync(fh)

	def load(self, pth):
		rows = []
		with FortranFile(pth, mode='rb') as fh:
			try:
				while True:
					row = fh.readReals(prec='d')
					rows.append(row)
			except IOError:
				pass
		return array(rows)


class MatFile(TimeArrStorage):
	extension = 'mat'
	def save(self, arr, pth):
		with open(pth, 'w+') as fh:
			savemat(fh, dict(data=arr))
			sync(fh)

	def load(self, pth):
		with open(pth, 'r') as fh:
			return loadmat(fh)['data']



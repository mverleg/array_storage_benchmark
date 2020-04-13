
import gzip
from base64 import b64encode, b64decode
from genericpath import getsize
from os import fsync, remove, path
from pickle import dump as pkl_dump, load as pkl_load
from time import time

import h5py
import msgpack
import msgpack_numpy
from imgarray import save_array_img, load_array_img
from json_tricks import dump as jt_dump, load as jt_load
from numpy import array_equal, savetxt, loadtxt, frombuffer, save as np_save, load as np_load, savez_compressed, array, \
	float64
from pandas import read_stata, DataFrame, read_html, read_excel
from scipy.io import savemat, loadmat, FortranFile


def sync(fh):
	"""
	This makes sure data is written to disk, so that buffering doesn't influence the timings.
	"""
	fh.flush()
	fsync(fh.fileno())


class TimeArrStorage(object):
	extension = 'data'
	
	def __init__(self, reps=100):
		self.save_time = None
		self.load_time = None
		self.storage_space = None

	@classmethod
	def method_name(cls):
		return cls.__name__
	
	def save(self, arr, pth):
		# implementations have to call `sync`!
		raise NotImplementedError
	
	def load(self, pth):
		raise NotImplementedError
	
	def time_save(self, arr, pth):
		t0 = time()
		self.save(arr, pth)
		self.save_time = time() - t0
		self.storage_space = getsize(pth)
	
	def time_load(self, ref_arr, pth):
		t0 = time()
		arr = self.load(pth)
		sm = arr.sum()  # this is necessary to make sure it isn't lazy-loaded
		self.load_time = time() - t0
		remove(pth)
		assert array_equal(arr, ref_arr), 'load failed for {0:}'.format(self)
		return sm
	

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
	def save(self, arr, pth):
		with open(pth, 'wb+') as fh:
			fh.write('{0:} {1:} {2:}\n'.format(arr.dtype, arr.shape[0], arr.shape[1]).encode('ascii'))
			fh.write(arr.data)
			sync(fh)

	def load(self, pth):
		with open(pth, 'rb') as fh:
			header = fh.readline()
			data = fh.read()
		dtype, w, h = header.decode('ascii').strip().split()
		return frombuffer(data, dtype=dtype).reshape((int(w), int(h)))


class BinaryGzip(TimeArrStorage):
	def save(self, arr, pth):
		with gzip.open(pth, 'wb+') as fh:
			fh.write('{0:} {1:} {2:}\n'.format(arr.dtype, arr.shape[0], arr.shape[1]).encode('ascii'))
			fh.write(arr.data)
			sync(fh)

	def load(self, pth):
		with gzip.open(pth, 'rb') as fh:
			header = fh.readline()
			data = fh.read()
		dtype, w, h = header.decode('ascii').strip().split()
		return frombuffer(data, dtype=dtype).reshape((int(w), int(h)))


class Pickle(TimeArrStorage):
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


class JsonTricks(TimeArrStorage):
	extension = 'json.gz'
	def save(self, arr, pth):
		with open(pth, 'wb+') as fh:
			jt_dump([arr], fh, compression=True, properties={'ndarray_compact': True})
			sync(fh)

	def load(self, pth):
		return jt_load(pth, ignore_comments=False)[0]


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
			fh.write('{0:} {1:} {2:}\n'.format(arr.dtype, arr.shape[0], arr.shape[1]))
			fh.write(b64encode(arr.data).decode('ascii'))
			sync(fh)

	def load(self, pth):
		with open(pth, 'r') as fh:
			dtype, w, h = str(fh.readline()).split()
			return frombuffer(b64decode(fh.read()), dtype=dtype).reshape((int(w), int(h)))


class FortUnf(TimeArrStorage):
	# this implementation assumes float64
	def save(self, arr, pth):
		with FortranFile(pth, mode='w') as fh:
			for k in range(arr.shape[0]):
				fh.write_record(arr[k, :])
			# NOTE: no sync available for FortranFile

	def load(self, pth):
		rows = []
		with FortranFile(pth, mode='r') as fh:
			try:
				while True:
					row = fh.read_reals(dtype=float64)
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


class Stata(TimeArrStorage):
	# converts to and from DataFrame since it's a pandas method
	extension = 'sta'
	def save(self, arr, pth):
		with open(pth, 'wb+') as fh:
			colnames = tuple('c{0:03d}'.format(k) for k in range(arr.shape[1]))
			DataFrame(data=arr, columns=colnames).to_stata(fh)
			# sync(fh)  # file handle already closed

	def load(self, pth):
		with open(pth, 'rb') as fh:
			data = read_stata(fh)
			return data.as_matrix(columns=data.columns[1:])


class HTML(TimeArrStorage):
	def save(self, arr, pth):
		with open(pth, 'w+') as fh:
			colnames = tuple('c{0:03d}'.format(k) for k in range(arr.shape[1]))
			DataFrame(data=arr, columns=colnames).to_html(fh, index=False)
			sync(fh)

	def load(self, pth):
		with open(pth, 'r') as fh:
			data = read_html(fh)[0]
			arr = data.as_matrix()#columns=data.columns[1:])
			return arr


class Excel(TimeArrStorage):
	def save(self, arr, pth):
		with open(pth, 'w+') as fh:
			colnames = tuple('c{0:03d}'.format(k) for k in range(arr.shape[1]))
			DataFrame(data=arr, columns=colnames).to_excel(fh, sheet_name='data', index=False)
			sync(fh)

	def load(self, pth):
		with open(pth, 'r') as fh:
			data = read_excel(fh, sheetname='data')
			return data.as_matrix()


class HDF5(TimeArrStorage):
	def name(self, pth):
		return 'bench_{}'.format(path.basename(pth).replace('.', '_'))

	def method_name(self):
		return 'HDF5(?)'

	def save(self, arr, pth):
		with h5py.File(pth, 'w') as fh:
			fh.create_dataset(self.name(pth), data=arr)
			fh.flush()

	def load(self, pth):
		with h5py.File(pth, 'r') as fh:
			data = fh[self.name(pth)][:]
			# Do something with the data, as it is lazy-loaded
			_ = data.min()
			return data


class HDF5Gzip(HDF5):
	def method_name(self):
		return 'HDF5(?)Gzip'

	def save(self, arr, pth):
		with h5py.File(pth, 'w') as fh:
			fh.create_dataset(self.name(pth), compression='gzip', data=arr)
			fh.flush()


class MsgPack(TimeArrStorage):
	def save(self, arr, pth):
		with open(pth, 'wb+') as fh:
			bin = msgpack.packb(arr, default=msgpack_numpy.encode)
			fh.write(bin)
			sync(fh)

	def load(self, pth):
		with open(pth, 'rb') as fh:
			return msgpack.unpackb(fh.read(), object_hook=msgpack_numpy.decode)


METHODS = (
	Csv,
	CsvGzip,
	JSON,
	JSONGzip,
	b64Enc,
	JsonTricks,
	MsgPack,
	Pickle,
	PickleGzip,
	Binary,
	BinaryGzip,
	NPY,
	NPYCompr,
	# HDF5,
	# HDF5Gzip,
	PNG,
	FortUnf,
	# Excel,
	# HTML,
	# MatFile,
	# Stata,
)

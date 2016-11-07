
import gzip
from base64 import urlsafe_b64encode, urlsafe_b64decode
from os import remove, fsync, environ
from os.path import join, getsize
from scipy import sparse
from tempfile import mkdtemp
from time import time
from matplotlib.pyplot import subplots, show
import seaborn
from numpy import mean, savetxt, loadtxt, frombuffer, array, array_equal, arange, std
from numpy import save as np_save, load as np_load, savez_compressed
from numpy.random import RandomState
from imgarray import save_array_img, load_array_img
from json_tricks import load as jt_load, dump as jt_dump
from pickle import dump as pkl_dump, load as pkl_load
from fortranfile import FortranFile


def sync(fh):
	"""
	This makes sure data is written to disk, so that buffering doesn't influence the timings.
	"""
	fh.flush()
	fsync(fh.fileno())


class TimeArrStorage:
	extension = 'data'
	
	def __init__(self, reps=100):
		self.save_time = None
		self.load_time = None
		self.storage_space = None
		self.reps = int(reps)
		self.paths = tuple(join(mkdtemp(), self.__class__.__name__.lower() + '{0:03d}.{1:s}'
			.format(k, self.extension)) for k in range(self.reps))
	
	def __str__(self):
		return self.__class__.__name__
	
	def save(self, arr, pth):
		raise NotImplementedError
	
	def load(self, pth):
		raise NotImplementedError
	
	def time_save(self, arr):
		t0 = time()
		for pth in self.paths:
			self.save(arr, pth)
		self.save_time = (time() - t0) / self.reps
		self.storage_space = mean(tuple(getsize(pth) for pth in self.paths))
	
	def time_load(self, ref_arr):
		t0 = time()
		arr = None
		for pth in self.paths:
			arr = self.load(pth)
		self.load_time = (time() - t0) / self.reps
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
			return loadtxt(pth, delimiter=',')

	
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
		save_array_img(arr, pth, img_format='png')
			
	def load(self, pth):
		return load_array_img(pth)


class b64Enc(TimeArrStorage):
	def save(self, arr, pth):
		with open(pth, 'w+') as fh:
			fh.write(b'{0:s} {1:d} {2:d}\n'.format(arr.dtype, *arr.shape))
			fh.write(urlsafe_b64encode(arr.data))

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


#todo: pandas formats - http://pandas.pydata.org/pandas-docs/stable/io.html


#todo: hdf5 - http://stackoverflow.com/a/9619713/723090


#todo: bloscpack http://stackoverflow.com/a/22225337/723090


#todo: pytables


def random_data(size, is_sparse=False):
	"""
	Make data
	"""
	rs = RandomState(seed=123456789)
	if is_sparse:
		sparse.rand(1000, 200, density=0.01, random_state=rs)
	else:
		return (2 * rs.rand(*size).astype('float64') - 1) * 1.7976931348623157e+308


def load_example_data():
	return loadtxt(join(environ['HOME'], 'testdata.csv'), delimiter=',')


def run_benchmark(data, insts):
	"""
	Run benchmark
	"""
	for inst in insts:
		inst.time_save(data)
		inst.time_load(data)
		inst.log()


def plot_results(insts, fname='benchmark.png'):
	"""
	Make some bar charts with results
	"""
	cm = iter(seaborn.color_palette('colorblind'))
	names = tuple(str(inst) for inst in insts)
	fig, ax = subplots(figsize=(10, 10), tight_layout=True)
	indx = - arange(0, len(insts))
	height = 0.2
	twax = ax.twiny()
	save_times = tuple(inst.save_time for inst in insts)
	lsave = ax.barh(indx - 0.3, save_times, height=height, color=next(cm), label='store')
	lload = ax.barh(indx - 0.6, tuple(inst.load_time for inst in insts), height=height, color=next(cm), label='retrieve')
	lmem  = twax.barh(indx - 0.9, tuple(inst.storage_space / 1024. ** 2 for inst in insts), height=height, color=next(cm), label='disk space')
	ax.tick_params(axis='both', which='major', labelsize=18)
	twax.tick_params(axis='both', which='major', labelsize=18)
	ax.set_yticks(indx - 0.5)
	ax.set_yticklabels(names)
	ax.set_ylim([- len(insts), 0])
	ax.set_xlim([0, mean(save_times) + std(save_times)])
	# ax.set_xscale('log')
	ax.set_xlabel('average save/load time (s)', fontsize=18)
	twax.set_xlabel('disk space use (Mb)', fontsize=18)
	ax.grid(axis='y')
	twax.grid('off')
	fig.savefig(fname)
	ax.legend((lsave, lload, lmem), ('store', 'retrieve', 'disk space'), loc='upper right', fontsize=18, frameon=True)
	return fig, ax


#todo: need to have different arrays to compare compression


"""
Setup & params
"""
clss = (Csv, CsvGzip, JSON, JSONGzip, b64Enc, Pickler, PickleGzip, Binary, NPY, NPYCompr, PNG, FortUnf)


if __name__ == '__main__':
	for data, fname in (
		(random_data((1000, 200)), 'benchmark_randdata.png'),
		(random_data((1000, 200), is_sparse=True), 'benchmark_sparsedata.png'),
		(load_example_data(), 'bechmark_exampledata.png'),
	):
		insts = tuple(cls(20) for cls in clss)
		run_benchmark(data, insts)
		sinsts = sorted(insts, key=lambda inst: (inst.save_time + inst.load_time) * inst.storage_space)
		fig, ax = plot_results(sinsts, fname=fname)
	
	# ax.set_title('Numpy ndarray storage for 1000x200 random array (avg of 10)', fontsize=20)
	# plot_memory_results(insts)
	show()




from os import environ
from os.path import join, exists
from tempfile import mkdtemp
from json_tricks import load as jt_load, dump as jt_dump
from matplotlib.pyplot import show
from numpy import mean, loadtxt, array, std
from numpy.random import RandomState
from scipy import sparse
from methods import Csv, CsvGzip, JSON, JSONGzip, Binary, Pickler, PickleGzip, NPY, NPYCompr, PNG, b64Enc, FortUnf, MatFile
from visualize import plot_results


class Benchmark(object):
	extension = 'data'
	
	def __init__(self, cls, data, reps=50):
		self.cls = cls
		self.data = data
		self.data_name = str(hash(data.tobytes())).replace('-', '')[:8]
		self.reps = int(reps)
		self.todo = []
		self.done = []
		for k in range(reps):
			pth = 'cache/{0:s}.{1:s}.{2:03d}.json'.format(self.cls.__name__, self.data_name, k)
			if exists(pth):
				self.done.append(jt_load(pth))
			else:
				inst = self.cls()
				inst._cache = pth
				self.todo.append(inst)
	
	@property
	def save_time(self):
		assert self.done
		return mean(tuple(inst.save_time for inst in self.done))
	
	@property
	def load_time(self):
		assert self.done
		return mean(tuple(inst.load_time for inst in self.done))
	
	@property
	def storage_space(self):
		assert self.done
		return mean(tuple(inst.storage_space for inst in self.done))
	
	@property
	def save_time_std(self):
		assert self.done
		return std(tuple(inst.storage_space for inst in self.done))
	
	@property
	def load_time_std(self):
		assert self.done
		return std(tuple(inst.storage_space for inst in self.done))
	
	@property
	def storage_space_std(self):
		assert self.done
		return std(tuple(inst.storage_space for inst in self.done))
	
	def __str__(self):
		return 'benchmark {0:s} {2:d}/{1:d}'.format(self.cls.__name__, self.reps, len(self.done))
	
	def run(self):
		while self.todo:
			inst = self.todo.pop()
			pth = join(mkdtemp(), '{0:s}_{1:d}.{2:s}'.format(self.__class__.__name__, len(self.done), inst.extension))
			inst.time_save(self.data, pth)
			inst.time_load(self.data, pth)
			jt_dump(inst, inst._cache)
			self.done.append(inst)
	
	def log(self):
		print('{0:12s}  {4:2d}/{5:2d}  {1:8.6f}s  {2:8.6f}s  {3:6.0f}kb'.format(self.cls.__name__, self.save_time,
			self.load_time, self.storage_space/1024., len(self.done), self.reps))


def random_data(size, is_sparse=False):
	rs = RandomState(seed=123456789)
	if is_sparse:
		return array(sparse.rand(size[0], size[1], density=0.01, random_state=rs).todense())
	else:
		return (2 * rs.rand(*size).astype('float64') - 1) * 1.7976931348623157e+308


def load_example_data():
	return loadtxt(join(environ['HOME'], 'testdata.csv'), delimiter=',')


# def run_benchmark(data, insts):
# 	"""
# 	Run benchmark
# 	"""
# 	for inst in insts:
# 		inst.time_save(data)
# 		inst.time_load(data)
# 		inst.log()

 
"""
Setup & params
"""
clss = (Csv, CsvGzip, JSON, JSONGzip, b64Enc, Pickler, PickleGzip, Binary, NPY, NPYCompr, PNG, FortUnf, MatFile)
# clss = (PNG, FortUnf, MatFile)


if __name__ == '__main__':
	reps = 3
	size = (1000, 400)
	for data, name, label in (
		(random_data(size, is_sparse=True), 'sparse', 'Sparse(0.01) random array'),
		(random_data(size), 'random', 'Dense random array'),
		(load_example_data(), 'example', 'Real data'),
	):
		print '>> benchmark {0:s} <<'.format(name)
		# cache_pth = 'results_{0:s}_{1:d}x.json'.format(name, rep)
		# if exists(cache_pth):
		# 	print('loading {0:s} for cache'.format(name))
		# 	sinsts = jt_load(cache_pth)
		# else:
		insts = tuple(Benchmark(cls, data, reps=reps) for cls in clss)
		for bm in insts:
			bm.run()
			bm.log()
		# run_benchmark(data, insts)
		sinsts = sorted(insts, key=lambda inst: (inst.save_time + inst.load_time) * inst.storage_space)
		# jt_dump(sinsts, cache_pth, indent=2)
		fig, ax = plot_results(sinsts, fname='benchmark_{0:s}_data.png'.format(name))
		fig.suptitle('{1:s} storage performance ({2:d}x{3:d}, avg of {0:d}x)'.format(reps, label, *size), fontsize=20)
	show()



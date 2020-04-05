
from os.path import join, exists
from sys import argv
from tempfile import mkdtemp
from json_tricks import load as jt_load, dump as jt_dump
from matplotlib.pyplot import show
from numpy import mean, loadtxt, array, std
from numpy.random import RandomState
from scipy import sparse
from methods import METHODS
from visualize import plot_results


class Benchmark(object):
	extension = 'data'
	
	def __init__(self, cls, data, data_name=None, reps=50):
		self.cls = cls
		self.data = data
		if data_name:
			self.data_name = data_name
		else:
			self.data_name = str(hash(data.tobytes())).replace('-', '')[:8]
		self.reps = int(reps)
		self.todo = []
		self.done = []
		self.label = self.cls.__name__
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
		return std(tuple(inst.save_time for inst in self.done))
	
	@property
	def load_time_std(self):
		assert self.done
		return std(tuple(inst.load_time for inst in self.done))
	
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
		print('{0:12s}  {4:2d}/{5:2d}  {1:8.6f}+-{6:8.6f}s  {2:8.6f}+-{7:8.6f}s  {3:6.0f}+-{8:8.6f}kb'.format(self.cls.__name__, self.save_time,
			self.load_time, self.storage_space/1024., len(self.done), self.reps, self.save_time_std, self.load_time_std, self.storage_space_std/1024.))


def random_data(size, is_sparse=False, is_big=True):
	rs = RandomState(seed=123456789)
	if is_sparse:
		arr = array(sparse.rand(size[0], size[1], density=0.01, random_state=rs).todense())
	else:
		arr = rs.rand(*size).astype('float64')
	if is_big:
		# don't use the full range, since some formats (Stata) uses the highest values for special meanings.
		arr = (arr - 0.5) * 1.7976931348623157e+308
	return arr


def load_example_data():
	return loadtxt('testdata.csv', delimiter=',')


if __name__ == '__main__':
	reps = int(argv[1]) if len(argv) > 1 else 30
	for data, name, label in (
		(random_data((1000, 400)), 'random', 'Random array'),
		(random_data((1000, 400), is_sparse=True), 'sparse', 'Sparse (0.01)'),
		(random_data((100000, 3), is_big=False), 'long', 'Long array'),
		(load_example_data(), 'example', 'Real data'),
	):
		print('>> benchmark {0:s} <<'.format(name))
		insts = tuple(Benchmark(cls, data, data_name=name, reps=reps) for cls in METHODS)
		for bm in insts:
			bm.run()
			bm.log()
		# sinsts = sorted(insts, key=lambda inst: (inst.save_time + inst.load_time) * inst.storage_space)
		fig, ax = plot_results(insts, fname='bm_{0:s}.png'.format(name),
			suptitle='{1:s} storage performance ({2:d}x{3:d}, avg of {0:d}x)'.format(reps, label, *data.shape))
	show()




from os import environ
from os.path import join, exists
import seaborn
from json_tricks import load as jt_load, dump as jt_dump
from matplotlib.pyplot import subplots, show
from numpy import mean, loadtxt, array, arange, std
from numpy.random import RandomState
from scipy import sparse
from methods import Csv, CsvGzip, JSON, JSONGzip, Binary, Pickler, PickleGzip, NPY, NPYCompr, PNG, b64Enc, FortUnf, MatFile


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
		return array(sparse.rand(1000, 200, density=0.01, random_state=rs).todense())
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


def add_bar_labels(ax, patches, values, xlim=None, fontsize=16, template='{0:.3f}'):
	xlim = xlim or ax.get_xlim()[1]
	for rect, val in zip(patches, values):
		ax.text(min(rect.get_x() + rect.get_width() + xlim / 100, xlim*0.88),
			rect.get_y() + rect.get_height() / 2, template.format(rect.get_width()),
			ha='left', va='center', fontsize=fontsize)


def plot_results(insts, fname='benchmark.png'):
	"""
	Make some bar charts with results
	"""
	fontsize = 16
	cm = iter(seaborn.color_palette('colorblind'))
	names = tuple(str(inst) for inst in insts)
	fig, ax = subplots(figsize=(9, 10), tight_layout=False)
	fig.subplots_adjust(left=0.16, right=0.96, bottom=0.08, top=0.88)
	indx = - arange(0, len(insts))
	height = 0.2
	twax = ax.twiny()
	save_times = tuple(inst.save_time for inst in insts)
	load_times = tuple(inst.save_time for inst in insts)
	xlim = mean(save_times) + std(save_times)
	lsave = ax.barh(indx - 0.3, save_times, height=height, color=next(cm), label='store')
	add_bar_labels(ax, lsave, save_times, xlim=xlim, fontsize=fontsize-3, template='{0:.3f}s')
	lload = ax.barh(indx - 0.6, tuple(inst.load_time for inst in insts), height=height, color=next(cm), label='retrieve')
	add_bar_labels(ax, lload, load_times, xlim=xlim, fontsize=fontsize-3, template='{0:.3f}s')
	lmem  = twax.barh(indx - 0.9, tuple(inst.storage_space / 1024.**2 for inst in insts), height=height, color=next(cm), label='disk space')
	add_bar_labels(twax, lmem, load_times, fontsize=fontsize-3, template='{0:.2f}Mb')
	ax.set_ylim([- len(insts), 0])
	ax.set_xlim([0, xlim])
	ax.tick_params(axis='both', which='major', labelsize=fontsize-1)
	twax.tick_params(axis='both', which='major', labelsize=fontsize-1)
	ax.set_yticks(indx - 0.5)
	ax.set_yticklabels(names)
	# ax.set_xscale('log')
	ax.set_xlabel('average save/load time (s)', fontsize=fontsize)
	twax.set_xlabel('disk space use (Mb)', fontsize=fontsize)
	ax.grid(axis='y')
	twax.grid('off')
	fig.savefig(fname)
	ax.legend((lsave, lload, lmem), ('store', 'retrieve', 'disk space'), loc='upper right', fontsize=fontsize, frameon=True)
	return fig, ax


#todo: need to have different arrays to compare compression


"""
Setup & params
"""
clss = (Csv, CsvGzip, JSON, JSONGzip, b64Enc, Pickler, PickleGzip, Binary, NPY, NPYCompr, PNG, FortUnf, MatFile)
# clss = (PNG, FortUnf, MatFile)


if __name__ == '__main__':
	rep, size = 2, (1000, 400)
	for data, name, label in (
		(random_data(size, is_sparse=True), 'sparse', 'Sparse(0.01) random array'),
		(random_data(size), 'random', 'Dense random array'),
		(load_example_data(), 'example', 'Real data'),
	):
		print '>> benchmark {0:s} <<'.format(name)
		cache_pth = 'results_{0:s}_{1:d}x.json'.format(name, rep)
		if exists(cache_pth):
			print('loading {0:s} for cache'.format(name))
			sinsts = jt_load(cache_pth)
		else:
			insts = tuple(cls(rep) for cls in clss)
			run_benchmark(data, insts)
			sinsts = sorted(insts, key=lambda inst: (inst.save_time + inst.load_time) * inst.storage_space)
			jt_dump(sinsts, cache_pth, indent=2)
		fig, ax = plot_results(sinsts, fname='benchmark_{0:s}_data.png'.format(name))
		fig.suptitle('{1:s} storage performance ({2:d}x{3:d}, avg of {0:d}x)'.format(rep, label, *size), fontsize=20)
	show()



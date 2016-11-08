
import seaborn
from matplotlib.pyplot import subplots
from numpy import arange, mean, std


def add_bar_labels(ax, patches, values, xlim=None, fontsize=16, template='{0:.3f}'):
	xlim = xlim or ax.get_xlim()[1]
	for rect, val in zip(patches, values):
		ax.text(min(rect.get_x() + rect.get_width() + xlim / 10, xlim*0.88),
			rect.get_y() + rect.get_height() / 2, template.format(rect.get_width()),
			ha='left', va='center', fontsize=fontsize)


def plot_results(insts, fname='benchmark.png'):
	"""
	Make some bar charts with results
	"""
	fontsize = 16
	cm = iter(seaborn.color_palette('colorblind'))
	names = tuple(inst.label for inst in insts)
	fig, ax = subplots(figsize=(9, 10), tight_layout=False)
	fig.subplots_adjust(left=0.16, right=0.96, bottom=0.08, top=0.88)
	indx = - arange(0, len(insts))
	height = 0.2
	twax = ax.twiny()
	save_times = tuple(inst.save_time for inst in insts)
	load_times = tuple(inst.save_time for inst in insts)
	xlim = mean(save_times) + std(save_times)
	lsave = ax.barh(indx - 0.3, save_times, height=height, color=next(cm), label='store',
		xerr=tuple(inst.save_time_std for inst in insts))
	add_bar_labels(ax, lsave, save_times, xlim=xlim, fontsize=fontsize-3, template='{0:.3f}s')
	lload = ax.barh(indx - 0.6, tuple(inst.load_time for inst in insts), height=height, color=next(cm), label='retrieve',
		xerr=tuple(inst.load_time_std for inst in insts))
	add_bar_labels(ax, lload, load_times, xlim=xlim, fontsize=fontsize-3, template='{0:.3f}s')
	lmem  = twax.barh(indx - 0.9, tuple(inst.storage_space / 1024.**2 for inst in insts), height=height, color=next(cm),
		label='disk space', xerr=tuple(inst.storage_space_std / 1024.**2 for inst in insts))
	add_bar_labels(twax, lmem, load_times, fontsize=fontsize-3, template='{0:.2f}Mb')
	ax.set_ylim([- len(insts), 0])
	ax.set_xlim([0, xlim])
	ax.tick_params(axis='both', which='major', labelsize=fontsize-1)
	twax.tick_params(axis='both', which='major', labelsize=fontsize-1)
	ax.set_yticks(indx - 0.5)
	ax.set_yticklabels(names)
	ax.set_xlabel('average save/load time (s)', fontsize=fontsize)
	twax.set_xlabel('disk space use (Mb)', fontsize=fontsize)
	ax.grid(axis='y')
	twax.grid('off')
	fig.savefig(fname)
	ax.legend((lsave, lload, lmem), ('store', 'retrieve', 'disk space'), loc='upper right', fontsize=fontsize, frameon=True)
	return fig, ax



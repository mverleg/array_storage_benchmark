

from numpy.random.mtrand import RandomState
from pandas import DataFrame, read_html

pth = '/tmp/demo.dta'
rs = RandomState(seed=123456789)
data = (2 * rs.rand(1000, 400).astype('float64') - 1) * 1.7976931348623157e+308

colnames = tuple('c{0:03d}'.format(k) for k in range(data.shape[1]))
frame = DataFrame(data=data, columns=colnames)
with open(pth, 'wb+') as fh:
	frame.to_html(fh)

with open(pth, 'rb') as fh:
	frame2 = read_html(fh)[0]

print(frame2.tail())



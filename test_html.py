
# todo issue: https://github.com/pandas-dev/pandas/issues/14623

from numpy import float64
from pandas import DataFrame, read_html


def floatformat(val):
	return '{:.16e}'.format(val)

x = 1.18047406523e+307
s = floatformat(x)
y = float64(s)
assert x == y

frame = DataFrame(data=[[x]], columns=['a'])
pth = '/tmp/demo.dta'
with open(pth, 'w+') as fh:
	frame.to_html(fh, float_format=floatformat)
with open(pth, 'r') as fh:
	frame2 = read_html(fh, flavor='bs4')[0]

assert frame.a[0] == frame2.a[0], floatformat(frame.a[0] - frame2.a[0])
assert x == frame2.a[0]

# exit()
# print(pth)
# rs = RandomState(seed=123456789)
# data = (2 * rs.rand(100, 40).astype('float64') - 1) * 1.7976931348623157e+308
#
# colnames = tuple('c{0:03d}'.format(k) for k in range(data.shape[1]))
# frame = DataFrame(data=data, columns=colnames)
# with open(pth, 'w+') as fh:
# 	frame.to_html(fh, float_format=lambda val: '{:.24e}'.format(val))
#
# with open(pth, 'r') as fh:
# 	frame2 = read_html(fh)[0]
# arr2 = frame2.as_matrix(columns=frame2.columns[1:])
#
# print(frame.tail())
# print(frame2.tail())
#
# print(data.dtype, data.shape)
# print(arr2.dtype, arr2.shape)
# print(data - arr2)
# print(data[0, 0])
# print(arr2[0, 0])
# print(data[0, 0] - arr2[0, 0])
# print('{:.24e}'.format(data[0, 0]))
# print(float64('{:.24e}'.format(data[0, 0])))
# assert (data == arr2).all()



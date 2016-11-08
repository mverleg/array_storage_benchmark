Array storage benchmark
---------------------------------------

Compare the storage speed, retrieval speed and file size for various methods of storing 2D numpy arrays.

Hardware etc
---------------------------------------

The results here are obtained on a normal desktop PC that's several years old and running Ubuntu and has a SSD for storage. You can easily run the benchmarks on your own PC to get more relevant results. You can also apply it to your own data.

Results
---------------------------------------

Dense random matrix
=======================================

.. image:: https://raw.githubusercontent.com/mverleg/array_storage_benchmark/master/result/bm_random.png

.. image:: https://raw.githubusercontent.com/mverleg/array_storage_benchmark/master/result/bm_long.png

Sparse random matrix
=======================================

99% of values are zero, so compression ratios are very good.

.. image:: https://raw.githubusercontent.com/mverleg/array_storage_benchmark/master/result/bm_sparse.png

Real data
=======================================

Scattering probabilities for hydrogen and carbon monoxide (many doubles between 0 and 1, most close to 0).

.. image:: https://raw.githubusercontent.com/mverleg/array_storage_benchmark/master/result/bm_example.png

More methods
---------------------------------------

Pull requests with other methods (serious or otherwise) are welcome! There might be some ideas in the issue tracker.



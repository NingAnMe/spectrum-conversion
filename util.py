#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2019/1/10
@Author  : AnNing
"""
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta

import numpy as np
import pandas as pd
from netCDF4 import Dataset
import h5py


def is_day_timestamp_and_lon(timestamp, lon):
    """
    根据距离 1970-01-01 年的时间戳和经度计算是否为白天
    :param timestamp: 距离 1970-01-01 年的时间戳
    :param lon: 经度
    :return:
    """
    zone = int(lon / 15.)
    stime = datetime.utcfromtimestamp(timestamp)
    hh = (stime + relativedelta(hours=zone)).strftime('%H')
    if 6 <= int(hh) <= 18:
        return True
    else:
        return False


def statistics_print(data):
    print(data[0], data[-1], np.size(data), np.min(data), np.max(data), np.mean(data))


def iasi_apod(x, fwhm=0.5):
    """
    Gaussian function
    :param x: iasi 光谱
    :param fwhm: Gaussian 参数
    :return:
    """
    gft_fwhm = fwhm  # Gaussian function FWHM (cm^-1)
    gft_hwhm = gft_fwhm / 2.0
    ln2 = 0.693147180559945309417232

    sigma = ln2 / (np.pi * gft_hwhm)
    result = np.exp(-ln2 * (x / sigma) ** 2)
    return result


def cris_apod(x, opd=0.8):
    """
    Hamming Apod
    :param x:  cris 光谱
    :param opd: 光程差
    :return: cris_apod
    """
    a0 = 0.54
    a1 = 0.46
    opd = opd
    result = a0 + a1 * np.cos(np.pi * x / opd)
    return result


def rad2tbb(radiance, center_wave):
    """
    辐射率转亮温
    :param radiance: 辐射率
    :param center_wave: 中心波数
    :return: 亮温
    """
    c1 = 1.1910427e-5
    c2 = 1.4387752

    tbb = (c2 * center_wave) / np.log(1 + ((c1 * center_wave ** 3) / radiance))
    return tbb


def read_lbl_nc(in_file):
    """
    读取 LBL 文件
    :param in_file: 文件绝对路径
    :return: 文件内容
    """
    f = Dataset(in_file)

    spectrum = f.variables['spectrum'][:]
    begin_wn = f.variables['begin_frequency'][:]
    end_wn = f.variables['end_frequency'][:]
    wn_interval = f.variables['frequency_interval'][:]

    data = {
        'SPECTRUM': spectrum,  # 光谱
        'BEGIN_FREQUENCY': begin_wn,  # 开始频率
        'END_FREQUENCY': end_wn,  # 结束频率
        'FREQUENCY_INTERVAL': wn_interval,  # 频率间隔
    }
    f.close()
    return data


def read_lbl_hdf5(in_file):
    with h5py.File(in_file, 'r') as hdf5:
        spectrum = hdf5.get('spectrum').value
        wavenumber = hdf5.get('wavenumber').value
        begin_wn = wavenumber[0]
        end_wn = wavenumber[-1]
        wn_interval = wavenumber[1] - wavenumber[0]

        data = {
            'SPECTRUM': spectrum,  # 光谱
            'BEGIN_FREQUENCY': begin_wn,  # 开始频率
            'END_FREQUENCY': end_wn,  # 结束频率
            'FREQUENCY_INTERVAL': wn_interval,  # 频率间隔
        }
        return data


def get_range_index(data_ranges, step=1.):
    """
    根据范围获取数据的index
    :return:
    """
    index = []
    count = 0
    for start, end, _ in data_ranges:
        index_x = int(count)
        increment = (end - start) / step + 1
        index_y = int(increment + count)

        count += increment

        index_xy = [index_x, index_y]

        index.append(index_xy)

    return np.array(index, dtype=np.int)


def get_cris_full_train_data(in_files, x_ranges=None, y_ranges=None, count=None):
    """
    返回训练数据
    :param in_files: 读取数据文件的列表
    :param x_ranges: X 的光谱范围
    :param y_ranges: Y 的光谱范围
    :param count: 读取光谱的数量
    :return:
    """
    data_all = None
    wavenumber = None
    for in_file in in_files:
        with h5py.File(in_file, 'r') as hdf5_r:
            data = hdf5_r.get('spectrum_radiance')[:].astype(np.float32)
            if data_all is None:
                data_all = data
            else:
                data_all = np.concatenate((data_all, data), axis=0)
            if wavenumber is None:
                wavenumber = hdf5_r.get('spectrum_wavenumber')[:].astype(np.float32)

            if count is not None:
                if len(data_all) > count:
                    data_all = data_all[:count]
                    break

    x = list()
    if x_ranges is None:
        x_ranges = [(650., 1095.), (1210., 1750.), (2155., 2550.)]
    for start, end in x_ranges:
        index_start = int(np.where(wavenumber == start)[0])
        index_end = int(np.where(wavenumber == end)[0])
        if len(x) <= 0:
            x = data_all[:, index_start:index_end+1]
        else:
            x = np.concatenate((x, data_all[:, index_start:index_end+1]), axis=1)
    y = list()
    if y_ranges is None:
        y_ranges = [(1095.625, 1209.375), (1750.625, 2154.375), (2550.625, 2755.)]
    for start, end in y_ranges:
        index_start = int(np.where(wavenumber == start)[0])
        index_end = int(np.where(wavenumber == end)[0])
        if len(y) <= 0:
            y = data_all[:, index_start:index_end+1]
        else:
            y = np.concatenate((y, data_all[:, index_start:index_end+1]), axis=1)

    x = pd.DataFrame(x, dtype='float32')
    y = pd.DataFrame(y, dtype='float32')

    return x, y


def get_linear_model_attributes(in_file):
    """
    获取线性模型的系数
    """
    with h5py.File(in_file, 'r') as hdf5:
        obj1 = hdf5.get('P0')
        if obj1 is not None:
            coef = obj1[:]
        else:
            coef = None
        obj2 = hdf5.get('C0')
        if obj2 is not None:
            intercept = obj2[:]
        else:
            intercept = None
    return coef, intercept


def load_cris_full_data(in_files, all_cris_full_data_file=None, sample_count=None):
    """
    读取并清洗数据
    """
    if not os.path.isfile(all_cris_full_data_file):
        x, y = get_cris_full_train_data(in_files, count=sample_count)

        compression = 'gzip'  # 压缩算法种类
        compression_opts = 1  # 压缩等级
        shuffle = True
        with h5py.File(all_cris_full_data_file, 'w') as hdf5:
            hdf5.create_dataset('spectrum_radiance_X',
                                dtype=np.float32, data=x, compression=compression,
                                compression_opts=compression_opts,
                                shuffle=shuffle)
            hdf5.create_dataset('spectrum_radiance_Y',
                                dtype=np.float32, data=y, compression=compression,
                                compression_opts=compression_opts,
                                shuffle=shuffle)
    else:
        with h5py.File(all_cris_full_data_file, 'r') as hdf5:
            x = hdf5.get('spectrum_radiance_X')[:]
            y = hdf5.get('spectrum_radiance_Y')[:]

    print(x.shape, y.shape)

    return x, y


def get_wavenumber_by_range(ranges):
    """
    通过波段范围和分辨率获取波段的波数
    :param ranges:
    :return:
    """
    wavenumbers = np.array([])
    for s, e, f in ranges:
        wavenumbers = np.append(wavenumbers, np.arange(s, e + f, f))
    return wavenumbers


if __name__ == '__main__':
    test_file = 'IASI_xxx_1C_M01_20180108003259Z_20180108003554Z_N_O_20180108012525Z__20180108012654'
    x_, y_ = get_cris_full_train_data([test_file, test_file], count=2000)
    print(x_.shape)
    print(y_.shape)
    print(type(x_))
    print(type(y_))

    print(get_range_index([(650., 1095.), (1210., 1750.), (2155., 2550.)], 0.625))

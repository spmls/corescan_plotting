"""
Created on Wednesday Septebmer 25 17:07 2019

tools to work with XRF data from the Geotek MSCL (Olympus head)

@author: SeanPaul La Selle
"""

import os
import sys
import glob
import tkinter
from tkinter import filedialog
import numpy as np
import csv
import pandas
import matplotlib as matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import (MultipleLocator, FormatStrFormatter,
                               AutoMinorLocator)
import warnings
from corescan_plotting import plot_ct_tools, plot_linescan_tools

###############################################################################
def xrf_in(filename=''):
    """
    read in Geotek MSCL (v7.9) XRF data from from .out file
    """
    ## Get filename if not specified in function call
    if not filename:
        filename = filedialog.askopenfilename()
        if not filename:
            sys.exit()
    header, data = csv_xrf_parser(filename)
    dict = xrf_array2dict(header, data)
    # Determine the directory of the file
    directory = os.path.dirname(filename)
    ## Read other files
    # if not xml_fname:
    #     xml_fname = glob.glob(os.path.splitext(filename)[0]+'*.xml')[0]
    # xml_dic = linescan_xml(xml_fname)
    return dict

###############################################################################
def csv_xrf_parser(filename):
    """
    parses a Geotek XRF .out file (MSCL v7.9), returns the elements and an
    array with depths, counts, ppm and errors
    """
    with open(filename) as csvfile:
        readcsv = csv.reader(csvfile,delimiter='\t')
        header=[]
        data = []
        for i,row in enumerate(readcsv): # Assume header is 9 rows
            header.append(row)
            if(i>=9):
                break
        for row in readcsv: # From here, csv should be data
            data.append([float(i) for i in row])
    for i,r in enumerate(data): # Need to pad rows with empty data
        if len(r) != len(max(data,key=len)):
            r = np.append(r,np.ones((len(max(data,key=len))-len(r))))
            data[i] = np.nan*r
    data = np.reshape(data,(np.shape(data)[0],len(max(data,key=len))))

    return header, data

###############################################################################
def xrf_array2dict(header,data):
    """
    passes an array of Geotek XRF data (MSCL v7.9) to a dictionary of values
    for each element
    """
    dict =  {'ID': os.path.splitext(str.split(header[0][0])[4])[0]}
    dict["elements"] = header[7][5::2] # Assume elements start on the 7th row
    dict["depth"] = data[:,0]
    dict["section number"] = data[:,1]
    dict["section depth"] = data[:,2]
    dict["xrf total counts"] = data[:,3]
    dict["live time"] = data[:,4]
    dict["comp"] = data[:,5::2] # full array of compositional data
    dict["error"] = data[:,6::2] # array of errors in measurement
    for i,e in enumerate(dict["elements"]): # create key-value pair for elements
        dict[e] = dict["comp"][:,i]
    #Process dictionary
    dict = remove_open(dict)
    dict['comp'] = removeinvalid(dict['comp'],tol=500)
    dict['clr'] = clr(dict['comp'])

    return dict

###############################################################################
def remove_open(dict,k=1000000):
    """
    removes rows from a compositional data array (measurements x elements) if
    they don't add up to a constant sum "k", which should equal
    k = 1, 100, 10^6, 10^9, etc. (proportions, %, ppm, ppb, etc.)
    Default is set for ppm (1,000,000)
    """
    sums = [np.sum(row) for row in dict['comp']]
    rounded_sums = np.around(sums,decimals=0)
    not_closed = np.where(rounded_sums != k)
    keys = ['comp','depth','section number','section depth','xrf total counts',
            'live time','error']
    for e in dict['elements']:
        keys.append(e)
    for key in keys:
        dict[key] = np.delete(dict[key],not_closed,axis=0)
    return dict

###############################################################################
def removeinvalid(array, tol=500.):
    """
    remove all XRF measurements whose concentrations are less than 'tol'.
    geotek recommends 500+ ppm in geochem mode, 50+ ppm in soil mode.
    """
    array[array < tol] = np.nan
    return array

###############################################################################
def clr(array):
    """
    centered log ratio transform on matrix with each column having a different
    compositional component

    ported to python and modified from matlab code written by:
    Thio-Henestrosa, S., and J. A. Martin-Fernandez (2005),
    Dealing with compositional data: the freeware CoDaPack,
    Math. Geol., 37(7), 773-793.
    """
    rows = np.shape(array)[0]
    clr = np.zeros_like(array)
    m = np.ma.log(array)
    for r in range(rows):
        clr[r,:] = m[r,:] - np.nanmean(m[r,:])
    return clr

###############################################################################
def makelogratio(dict, ratio):
    """
    dict[ratio] is the log ratio of elements e1 and e2
    ratio is a string in the form 'e1/e2' and e1 and e2 are
    elements in dic['elements']. If not in the form 'e1/e2',
    will not do anything (pass)
    """
    try:
        e1, e2 = ratio.split('/')
        dict[ratio] = np.log(dict[e1]/dict[e2])
    except ValueError:
        pass
    return dict

###############################################################################
def nptsmooth(y, n, inf_nan=True, keep_nans=True):
    """
    smooths the data in y using a running mean
	over 2*n+1 successive point, n points on each side of the
	current point. At the ends of the series skewed or one-sided
	means are used.

    slightly modified from code ported from Matlab code written by:
    Olof Liungman, 1997
	Dept. of Oceanography, Earth Sciences Centre
	Göteborg University, Sweden
	E-mail: olof.liungman@oce.gu.se
    """
    y = y.copy()
    if inf_nan:
        y[y == np.inf] = np.nan
        y[y == -np.inf] = np.nan
    d = len(y)
    filtr = np.isnan(y)
    out = np.zeros_like(y)
    temp = np.zeros((2*n+1, d-2*n))
    temp[n,:] = y[n:-n]
    for ii in range(n):
        out[ii] = np.nanmean(y[:ii+n+1])
        out[d-ii-1] = np.nanmean(y[d-ii-1-n:])
        temp[ii,:] = y[ii:d-2*n+ii]
        temp[ii+n+1,:] = y[ii+n+1:d-n+ii+1]
    out[n:d-n] = np.nanmean(temp, axis=0)
    if keep_nans:
        out[filtr] = np.nan
    return out

###############################################################################
def plot_xrf_clr(dict, elements, smooth=5 ):
    """
    plot centered log ratios or elemental ratios for elements/element pairs as a
    function of depth.
    elements = array of strings for elements/ratios to plot e.g. ['Al','Ti','Ca/K']
    smooth = window size to smooth xrf data
    """
    if not elements:
        elements = dict['elements']

    colormap = plt.cm.tab20
    norm = matplotlib.colors.Normalize(vmin=0,vmax = np.size(elements))
    n = np.size(elements)
    fig, ax = plt.subplots(nrows = 1, ncols = n, figsize=(3+n,8.5),
                    sharey=True)
    keep_nans=True # for npointssmooth
    for i,e in enumerate(elements):
        if '/' in e:
            dict = makelogratio(dict,e)
            p = ax[i].plot(dict[e],dict['depth'],color = colormap(norm(i)))
        else:
            clr_vector = dict['clr'][:,dict['elements'].index(e)]
            p = ax[i].plot(clr_vector,dict['depth'],color = colormap(norm(i)))
        if smooth:
            p[0].set_alpha(0.4)
            if '/' in e:
                x = nptsmooth(dict[e], smooth, keep_nans=keep_nans)
            else:
                x = nptsmooth(dict['clr'][:,dict['elements'].index(e)],
                smooth, keep_nans=keep_nans)
            ax[i].plot(x, dict['depth'], color=colormap(norm(i)))
        ax[i].set_title(e,color=colormap(norm(i)))
        ax[i].yaxis.grid(color='k',linewidth=0.1)

    ax[0].invert_yaxis()
    loc = matplotlib.ticker.MultipleLocator(base=10.0)
    ax[0].yaxis.set_major_locator(loc)
    ax[-1].yaxis.set_tick_params(labelright=True)

# %% TESTING
filename="/Volumes/tsudisk/Cascadia/Floras Lake/Floras_XRF/VC22-667-817cm_archive/VC22-667-817cm_archive.out"
dict = xrf_in(filename)


# %% Test CLR plots
elements = ['Ca/Ti','K/Ti','Si/Ti','Si/Al','Fe']
plot_xrf_clr(dict,elements=elements,smooth=3)
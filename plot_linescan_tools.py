"""
Created on Friday March 15 16:22 2019

tools to work with tiffs from the GeoTek RXCT scanner

@author: SeanPaul La Selle
"""

import os
import sys
import glob
import tkinter
from tkinter import filedialog
import numpy as np
import xml.etree.ElementTree
import tifffile
from skimage.transform import downscale_local_mean
from skimage import img_as_ubyte
import matplotlib as matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import (MultipleLocator, FormatStrFormatter,
                               AutoMinorLocator)
import warnings
from corescan_plotting import plot_ct_tools


###############################################################################
def linescan_xml(filename=''):
    """
    read in GeoTek linescan xml data to a dictionary
    """
    ## Get directory if not specified in function call
    if not filename:
        tk_root = tkinter.Tk()
        tk_root.wm_withdraw()
        filename = filedialog.askopenfilename()
        tk_root.destroy()
        if not filename:
            sys.exit()
    fname = filename
    dname = os.path.dirname(fname)
    ## Parse the xml file
    tree = xml.etree.ElementTree.parse(fname)
    root = tree.getroot()
    ## Add element tags and attributes to a dictionary
    dic = {}
    for elem in root.iter():
        try:
            if isinteger(elem.text) is True:
                dic[elem.tag] = int(elem.text)
            elif isfloat(elem.text) is True:
                dic[elem.tag] = float(elem.text)
            else:
                dic[elem.tag] = elem.text
        except: TypeError
    return dic

###############################################################################
def linescan_in(filename='',xml_fname=''):
    """
    read in linescan data from from tif file
    """
    ## Get filename if not specified in function call
    if not filename:
        tk_root = tkinter.Tk()
        tk_root.wm_withdraw()
        filename = filedialog.askopenfilename()
        tk_root.destroy()
        if not filename:
            sys.exit()
    im = tifffile.imread(filename)
    if np.size(np.shape(im)) > 2: # normalize rgb bands to 0.0 to 1.0
        im = bands_to_rgb(im)
    # Determine the directory of the file
    directory = os.path.dirname(filename)
    ## Read xml file
    if not xml_fname:
        xml_fname = glob.glob(os.path.splitext(filename)[0]+'*.xml')[0]
    xml_dic = linescan_xml(xml_fname)
    return im, xml_dic

###############################################################################
def linescan_plot(ls_data, ls_xml):
    """
    plot a linescan image, using xml data to generate scale
    """
    ## Downscale from 16 bit tif to 8 bit
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        im = img_as_ubyte(ls_data)
    ## Get screen size for figure
    root = tkinter.Tk()
    pix2in = root.winfo_fpixels('1i')
    screen_width = root.winfo_screenwidth()/pix2in
    screen_height = root.winfo_screenheight()/pix2in
    image_h2w = round(ls_xml['physical-height']/ls_xml['physical-width'])
    fig = plt.figure(figsize=(screen_height/image_h2w, screen_height))
    ## Plot images
    aspect = 'equal'
    ax = plt.subplot(1, 1, 1)
    plt.imshow(im, aspect=aspect, extent=(0,ls_xml['physical-width'],\
                        ls_xml['physical-top']+ls_xml['physical-height'],\
                        ls_xml['physical-top']))
    ax.set_title(ls_xml['coreID'])

    return fig

###############################################################################
def dpi_ls_plot(fig,ls_xml):
    """
    calculate a dpi to preserve the resolution of the original image
    """
    ## Calculate the new dpi from the original resolution and new image size
    orig_h_pixels = ls_xml['scan-lines']
    orig_w_pixels = ls_xml['pixel-width']
    bbox = fig.axes[0].get_window_extent().transformed(fig.dpi_scale_trans.inverted())
    new_w_in, new_h_in = bbox.width, bbox.height
    ## Average the new dpis
    new_dpi = np.round(np.average([orig_w_pixels/new_w_in,
                                    orig_h_pixels/new_h_in]))
    ## Calculate
    return new_dpi

###############################################################################
def linescan_histogram(ls_data):
    """
    plot a histogram of the linescan intensities
    """
    ## Downscale from 16 bit tif to 8 bit
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        im = img_as_ubyte(ls_data)
    ## Calculate histogram, uses 500 bins
    hist, bins = np.histogram(im,bins=100)
    width = 0.7 * (bins[1] - bins[0])
    center = (bins[:-1] + bins[1:])/2
    ## Plot histogram
    fig = plt.figure(figsize=(10,10))
    plt.bar(center, hist, align='center',width=width)
    plt.xlabel('Intensity')
    plt.ylabel('Count')
    return fig

###############################################################################
def isfloat(x):
    """
    determine if a string can be converted to float
    """
    try:
        a = float(x)
    except ValueError:
        return False
    else:
        return True

###############################################################################
def isinteger(x):
    """
    determine if a string can be converted to an integer
    """
    try:
        a = int(x)
    except ValueError:
        return False
    else:
        return True

###############################################################################
def cm2inch(*tupl):
    """
    convert centimeters to inches
    """
    inch = 2.54
    if isinstance(tupl[0], tuple):
        return tuple(i/inch for i in tupl[0])
    else:
        return tuple(i/inch for i in tupl)
###############################################################################
def get_ax_size(ax):
    """
    get the size of a matplotlib figure axis in inches
    """
    bbox = ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
    width, height = bbox.width, bbox.height
    return width,height
###############################################################################
def normalize(array):
    """
    Normalizes numpy arrays into scale 0.0 - 1.0
    """
    array_min, array_max = array.min(), array.max()
    return ((array-array_min)/(array_max-array_min))
###############################################################################
def bands_to_rgb(rgb_array):
    """
    Takes a m x n x 3 array (assumes in order of R, G, B), normalizes values to 0.0
    - 1.0, and then stacks into one array for plotting in imshow
    """
    r = normalize(rgb_array[:,:,0])
    g = normalize(rgb_array[:,:,1])
    b = normalize(rgb_array[:,:,2])
    return np.dstack((r,g,b))

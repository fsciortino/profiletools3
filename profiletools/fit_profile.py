#!/usr/bin/env python2.7
# Copyright 2014 Mark Chilenski
# This program is distributed under the terms of the GNU General Purpose License (GPL).
# Refer to http://www.gnu.org/licenses/gpl.txt
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import division
from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
from builtins import next
from builtins import str
from builtins import zip
from builtins import range

__version__ = '0.0'
PROG_NAME = 'fit_profile'

import collections

# Define the systems that can be selected for each signal:
SYSTEM_OPTIONS = collections.OrderedDict([
    ('ne', ['CTS', 'ETS', 'TCI', 'reflect']),
    ('Te', ['CTS', 'ETS', 'GPC', 'GPC2', 'FRCECE', 'Mic']),
    ('emiss', ['AXA', 'AXJ'])
])

# List of all valid systems:
valid_systems = set()
for sig, sys in SYSTEM_OPTIONS.items():
    for s in sys:
        valid_systems.add(s)
# Shortcut flag for ETS+CTS:
valid_systems.add('TS')

# Define which systems are excluded by default:
DEFAULT_EXCLUDE = ['TCI', 'reflect']

# Define the coordinates that can be specified:
COORDINATE_OPTIONS = [
    'r/a', 'psinorm', 'Rmid', 'volnorm', 'phinorm',
    'sqrtpsinorm', 'sqrtr/a', 'sqrtvolnorm', 'sqrtphinorm'
]

# Define averaging methods available. First entry is default.
METHOD_OPTIONS = ['conventional', 'robust', 'all points']

# Define uncertainty methods available. First entry is default.
ERROR_METHOD_OPTIONS = ['sample', 'RMS', 'total', 'of mean', 'of mean sample']

# Make form suitable for command line entry:
error_method_cl = [s.replace(' ', '_') for s in ERROR_METHOD_OPTIONS]

# Define the kernels supported and their hyperparameters.
# The first entry is the label, the second is the description.
HYPERPARAMETERS = collections.OrderedDict([
    (
        'gibbstanh',
        collections.OrderedDict([
            (u"\u03C3f", "signal variance"),
            (u"\u21131", "core covariance length scale"),
            (u"\u21132", "edge covariance length scale"),
            (u"\u2113w", "core/edge transition width"),
            (u"x0", "core/edge transition location")
        ])
    ),
    (
        'gibbsdoubletanh',
        collections.OrderedDict([
            (u"\u03C3f", "signal variance"),
            (u"\u2113c", "core covariance length scale"),
            (u"\u2113m", "mid covariance length scale"),
            (u"\u2113e", "edge covariance length scale"),
            (u"\u2113a", "first transition width"),
            (u"\u2113b", "second transition width"),
            ("xa", "first transition"),
            ("xb", "second transition")
        ])
    ),
    (
        'SE',
        collections.OrderedDict([
            (u"\u03C3f", "signal variance"),
            (u"\u2113", "covariance length scale"),
        ])
    ),
    (
        'SEsym1d',
        collections.OrderedDict([
            ("1", "VOID"),
            ("2", "VOID"),
            (u"\u03C3f 2", "signal variance"),
            (u"\u2113 2", "covariance length scale")
        ])
    ),
    (
        'SEbeta',
        collections.OrderedDict([
            (u"\u03C3f", "signal variance"),
            (u"\u2113", "covariance length scale"),
            (u"\u03B1", "warping alpha"),
            (u"\u03B2", "warping beta")
        ])
    ),
    (
        'RQ',
        collections.OrderedDict([
            (u"\u03C3f", "signal variance"),
            (u"\u03B1", "order"),
            (u"\u2113", "covariance length scale")
        ])
    ),
    (
        'matern',
        collections.OrderedDict([
            (u"\u03C3f", "signal variance"),
            (u"\u03BD", "order"),
            (u"\u2113", "covariance length scale")
        ])
    ),
    (
        'matern52',
        collections.OrderedDict([
            (u"\u03C3f", "signal variance"),
            (u"\u2113", "covariance length scale")
        ])
    ),
    (
        'matern52beta',
        collections.OrderedDict([
            (u"\u03C3f", "signal variance"),
            (u"\u2113", "covariance length scale"),
            (u"\u03B1", "warping alpha"),
            (u"\u03B2", "warping beta")
        ])
    ),
])

# Configure and parse command line arguments:
import argparse

class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    pass

parser = argparse.ArgumentParser(
    description="""Fit univariate profile using gptools/profiletools.

BASIC USAGE DETAILS:

Calling without arguments will enter an interactive mode, or you can use the
command line flags to completely specify the options you wish to use. This
program can operate on ne, Te data from the tree, or you can provide data in a
NetCDF or CSV file.

You can choose whether to average over a time window, a specific set of points
or to use a single time slice. Even if providing data in a file, you should
specify the shot number and time window so that appropriate constraints can be
imposed on the fit at the magnetic axis and edge, and so that coordinate
transformations can be performed.

EXAMPLES:

Basic way to fit ne profile from shot 1101014006, averaged over the flat top
from 0.965s to 1.365s, using core and edge TS:

    %s --shot 1101014006 --signal ne --t-min 0.965 --t-max 1.365 --system TS

Basic way to fit data from NetCDF file foo.nc, assuming the data are from the
time window 0.965s to 1.365s of shot 1101014006. The abscissa is specified to be
normalized poloidal flux and is stored in the variable psin in the NetCDF file.
The ordinate is stored in the variable q and its uncertainty in err_q:

    %s -i foo.nc --coordinate psinorm --t-min 0.965 --t-max 1.365 -x psin -y q --shot 1101014006

FIXING/IMPROVING THE FIT:

Several things can go wrong in the fit. If there are bad points/outliers in your
data you can attempt to remove them by specifying one or both of
--change-threshold and --outlier-threshold, or you can flag specific points by
their indices using --remove-points. Change threshold rejects points that are
too distant from their neighbors, outlier threshold rejects points that are too
distant from the fit.

If there are not apparent outliers, but the fit still looks bad, then there is
likely an issue with the estimation of the fit's properties -- namely the
so-called hyperparameters that dictate the spatial correlation between points.
Try increasing the --random-starts flag to at least 8 as a first cut. This may
make the fit take quite a bit longer, but is parallelized, so the more cores
your computer has, the faster you will have your answer. If this still yields
unsatisfactory fits, try adjusting the bounds for the hyperparameters using
--bounds.

Note that many warnings regarding overflow in cosh and casting complex values
will be emitted -- these are usually benign. You will also see warnings that
the minimizer failed. These indicate that a particular random guess for the 
hyperparameters walked the minimizer into a bad state. At the end of the
optimization you will be told how many starts were accepted. Try to increase
--random-starts and/or adjust --bounds until this number is at least 4.

READING FROM FILES:

The support for reading data from NetCDF and CSV files is fairly powerful. With
either type of file, you can specify the column/variable names to be of the form
"name [units]" which will be automatically parsed to generate the right plot
labels. (Though it is better to just set the "units" attribute of each variable
in your NetCDF file, which is the preferred approach there.) The CSV reader is
smart enough to figure out your column names, as long as you put the time column
first when using data you haven't time-averaged yet. In either type of file you
can include the metadata needed to apply core/edge constraints. For CSV files,
start the file with as many lines needed of the form "name data" or
"name data,data,..." Be sure to either make the first line be "metadata N" where
N is the number of metadata lines used or specify --metadata-lines when doing
this! For NetCDF files, simply place the metadata in the appropriate attributes
of the file. The supported metadata are:

        ========== =======================================================
        shot       shot number
        times      comma-separated list of times included in the data
        t_min      minimum time included in the data
        t_max      maximum time included in the data
        coordinate the abscissa the data are represented as a function of,
                   valid choices are:
                   {psinorm,Rmid,r/a,volnorm,phinorm,sqrtpsinorm,sqrtr/a,
                    sqrtvolnorm,sqrtphinorm}
        ========== =======================================================
""" % (PROG_NAME, PROG_NAME,),
    formatter_class=CustomFormatter
)
parser.add_argument('--signal',
                    choices=list(SYSTEM_OPTIONS.keys()),
                    help="Which signal to fit when pulling data from the tree.")
parser.add_argument('--shot',
                    type=int,
                    help="Shot number to use. Required when pulling data from "
                         "the tree. When pulling data from a file, this is "
                         "needed to specify constraints at the magnetic axis and "
                         "limiter.")
parser.add_argument('--EFIT-tree',
                    help="EFIT tree to use. Default is ANALYSIS. Otherwise, give "
                         "a name like 'EFIT20'.")
parser.add_argument('--t-min',
                    type=float,
                    help="Starting time of period to average over. If you are "
                         "reading data from a file, you can set this flag to "
                         "tell the program what time window to average over "
                         "when finding the location of the limiter/magnetic axis "
                         "when applying constraints.")
parser.add_argument('--t-max',
                    type=float,
                    help="Ending time of period to average over. If you are "
                         "reading data from a file, you can set this flag to "
                         "tell the program what time window to average over when "
                         "finding the location of the limiter/magnetic axis "
                         "when applying constraints.")
parser.add_argument('-t', '--t-points',
                    type=float,
                    metavar='T_POINT',
                    nargs='+',
                    help="Individual time values to use. The nearest time to "
                         "each will be selected for each channel. You can use "
                         "this, for instance, to specify the times you have "
                         "determined are at a particular sawtooth/ELM phase. You "
                         "must either specify --t-min and --t-max, or -t.")
parser.add_argument('--npts',
                    type=int,
                    default=400,
                    help="Number of evenly-spaced points to evaluate the fit at.")
parser.add_argument('--x-min',
                    type=float,
                    default=0,
                    help="Starting point for the evenly-spaced points to evaluate "
                         "the fit at.")
parser.add_argument('--x-max',
                    type=float,
                    default=1.2,
                    help="Ending point for the evenly-spaced points to evaluate "
                         "the fit at.")
parser.add_argument('--x-pts',
                    type=float,
                    metavar='X_PT',
                    nargs='+',
                    help="Discrete points to evaluate the fit at. If present, "
                         "this overrides the effect of npts, x-min and x-max.")
parser.add_argument('--system',
                    nargs='+',
                    choices=valid_systems,
                    help="Which system(s) to take data from. If not provided, "
                         "all applicable systems will be used. The 'TS' option "
                         "is a shortcut to include both the core (CTS) and edge "
                         "(ETS) Thomson systems. Note that working with TCI data "
                         "is VERY slow. Also note that the statistics of "
                         "including the SOL reflectometer are questionable, so "
                         "you uncertainties should be taken with a grain of salt "
                         "when using those data.")
parser.add_argument('--kernel',
                    choices=list(HYPERPARAMETERS.keys()),
                    # default='gibbstanh',
                    help="Which covariance kernel to use. This dictates the "
                         "properties of the fit. "
                         "* gibbstanh is the Gibbs kernel with tanh warping of "
                         "the length scale. This kernel allows the entire "
                         "profile to be fit at once, and should be used if you "
                         "have edge data. "
                         "* gibbsdoubletanh is an experimental Gibbs kernel "
                         "whose warping function is the sum of two hyperbolic "
                         "tangents. This may be useful for whole profiles with "
                         "complicated shapes. "
                         "* SE is the squared exponential kernel, which is good "
                         "for core data. "
                         "* SEsym1d is an experimental SE kernel with symmetry "
                         "constraint imposed by construction. This is primarily "
                         "useful for core data. "
                         "* SEbeta is an experimental SE kernel whose arguments "
                         "are warped using the regularized incomplete beta "
                         "function. This is good when you have edge data. "
                         "* RQ is the rational quadratic kernel, good for "
                         "core data. "
                         "* matern is the Matern kernel, which is also "
                         "potentially useful for core data. Note that the matern "
                         "kernel is very SLOW to evaluate, particularly if you "
                         "need gradients. "
                         "* matern52 is a task-specific implementation of the "
                         "Matern kernel with the order fixed at nu=5/2. This is "
                         "MUCH faster than the basic matern. This is mostly "
                         "suitable for core data. "
                         "* matern52beta is the same as matern52, but with the "
                         "same warping as SEbeta applied. This is potentially "
                         "suitable for fitting entire profiles. "
                         "You will typically want to set --no-edge-constraint "
                         "and/or --core-only if you specify any kernel other "
                         "gibbstanh and gibbsdoubletanh. See also --core-only. "
                         "The default is gibbstanh, or SE if --core-only is set.")
parser.add_argument('--coordinate',
                    choices=COORDINATE_OPTIONS,
                    default='',
                    help="Which coordinate to fit against. Defaults to r/a "
                         "when pulling data from the tree. Used to determine how "
                         "to apply core/edge constraints when pulling data from "
                         "a file.")
parser.add_argument('--no-core-constraint',
                    action='store_true',
                    help="Set this flag to disable the slope=0 constraint at the "
                         "magnetic axis.")
parser.add_argument('--no-edge-constraint',
                    action='store_true',
                    help="Set this flag to disable the slope, value=0 constraint "
                         "at/outside the GH limiter.")
parser.add_argument('--core-constraint-location',
                    type=float,
                    metavar='LOC',
                    nargs='+',
                    help="Location to impose slope=0 constraint at. Typically "
                         "this is the magnetic axis. If you specify a shot "
                         "number and times then this will be found automatically, "
                         "but you can override it with this flag. Note that you "
                         "can specify multiple locations if you want to have "
                         "multiple points where the slope goes to exactly zero.")
parser.add_argument('--edge-constraint-locations',
                    type=float,
                    metavar='LOC',
                    nargs='+',
                    help="Location to impose slope~0, value~0 constraints at. "
                         "Typically this is at the location of the GH limiter. "
                         "If you specify a shot number and times then this will "
                         "be found automatically, but you can override it with "
                         "this flag. It helps to specify a couple of points "
                         "outside the GH limiter, as well.")
parser.add_argument('--core-only',
                    action='store_true',
                    help="Set this flag to only fit the data inside the LCFS. "
                         "This will switch to using a squared exponential kernel, "
                         "and will disable the edge value, slope constraints.")
parser.add_argument('--robust',
                    action='store_true',
                    help="Set this flag to use robust estimators (median, IQR) "
                         "when performing time-averages. Note that using robust "
                         "weighted estimators will not work for small numbers of "
                         "data points.")
parser.add_argument('--uncertainty-method',
                    choices=error_method_cl,
                    default='sample',
                    help="Method by which the uncertainty should be propagated "
                         "when time-averaging. "
                         "* sample will take the sample standard deviation, and "
                         "is usually appropriate for cases where you have many "
                         "points to average over and the data are not completely "
                         "stationary in time. "
                         "* RMS uses the root-mean-square standard deviation, "
                         "and is appropriate for small sample sizes. Note that "
                         "this is questionable when applied to diagnostics "
                         "other than TS for which the individual error bars are "
                         "estimated as some fixed percent of the value. "
                         "* total uses the law of total variance which is the "
                         "square root of the sum of the mean square uncertainty "
                         "and sample variance. This is appropriate when the "
                         "given points already represent actual sample "
                         "means/variances. "
                         "* of_mean uses the uncertainty in the mean using the "
                         "individual error bars on the points, and is only "
                         "appropriate if the data are steady in time. It is very "
                         "questionable to use this with robust estimators."
                         "* of_mean_sample uses the uncertainty in the mean "
                         "using the sample standard deviation, and is only "
                         "appropriate if the data are steady in time. It is very "
                         "questionable to use this with robust estimators.")
parser.add_argument('--unweighted',
                    action='store_true',
                    help="Set this flag to use unweighted estimators when "
                         "averaging the data. Otherwise the weights used are "
                         "1/sigma_i^2. Note that using robust weighted estimators "
                         "will not work for small numbers of data points. Note "
                         "that this is questionable when applied to diagnostics "
                         "other than TS for which the individual error bars are "
                         "estimated as some fixed percent of the value.")
parser.add_argument('--all-points', '--no-average',
                    action='store_true',
                    help="Set this flag to keep all points from the time window "
                         "selected instead of performing a time average. This "
                         "will make the fit take longer and is statistically "
                         "questionable, but may be useful in some cases.")
parser.add_argument('--change-threshold',
                    type=float,
                    help="If provided, any points whose differences with respect "
                         "to either of their neighbors are more than this many "
                         "times their own error bar will be rejected. This is "
                         "useful for getting rid of bad channels. A value of 9 "
                         "is often useful. Note that this does not take into "
                         "account the uncertainties on the neighbors -- it is "
                         "primarily designed to catch bad channels that don't "
                         "get caught by the method employed by "
                         "--outlier-threshold. This can lead to good data "
                         "getting thrown out if the threshold is too low.")
parser.add_argument('--outlier-threshold',
                    type=float,
                    help="If provided, any points whose values are more than this "
                         "many times their own error bar outside of the fit will "
                         "be rejected. A value of 3 is often useful. Note that "
                         "this can get thrown off by extremely bad channels that "
                         "drag the whole fit off.")
parser.add_argument('--remove-points',
                    type=int,
                    nargs='+',
                    help="Indices of points to remove. These are the indices in "
                         "the combined Profile object. These will usually be the "
                         "same from shot-to-shot, but may change if entire "
                         "channels are removed during data loading. Use "
                         "--plot-idxs to see the indices to use.")
parser.add_argument('--plot-idxs',
                    action='store_true',
                    help="Set this flag to overplot the indices of the points. "
                         "These are the indices to use with --remove-points.")
parser.add_argument('--random-starts',
                    type=int,
                    help="The number of random starts to use when trying to find "
                         "the MAP estimate for the hyperparameters. If you are "
                         "getting bad fits, try increasing this. If not "
                         "specified, this is set to the number of processors "
                         "available on your machine or 20, whichever is smaller.")
parser.add_argument('--upper-factor',
                    type=float,
                    default=5,
                    help="Factor by which the range of the data is multiplied "
                         "to generate the upper bound on the hyperparameters. If "
                         "you are getting bad fits, try adjusting this.")
parser.add_argument('--lower-factor',
                    type=float,
                    default=5,
                    help="Factor by which the range of the data is divided to "
                         "generate the lower bound on the hyperparameters. If "
                         "you are getting bad fits, try adjusting this.")
parser.add_argument('--bounds',
                    type=float,
                    nargs='+',
                    help="Bounds to use for each of the hyperparameters. "
                         "Specified as pairs of lower, upper bounds. If present, "
                         "there should be two such pairs for the squared "
                         "exponential kernel and five such pairs for the Gibbs "
                         "kernel with tanh length scale warping. If not specified, "
                         "somewhat intelligent guesses are made based on the data "
                         "itself. If you are getting bad fits, try tweaking these. "
                         "Note that this overrides --upper-factor and --lower-factor "
                         "if present.")
parser.add_argument('--use-MCMC',
                    action='store_true',
                    help="Set this flag to use MCMC integration over the "
                         "hyperparameters instead of MAP estimation. This is "
                         "the most rigorous way of capturing all uncertainty, "
                         "and should always be used if you are interested in "
                         "gradients and/or the details of the edge. Note that "
                         "this is very computationally expensive, but benefits "
                         "strongly from having many cores to run on.")
parser.add_argument('--walkers',
                    type=int,
                    default=200,
                    help="The number of walkers to use to explore the parameter "
                         "space. This number should be high, on the order of "
                         "a few hundred. If you are getting poor mixing of the "
                         "MCMC integration, try increasing this by a hundred at "
                         "a time.")
parser.add_argument('--MCMC-samp',
                    type=int,
                    default=200,
                    help="The number of samples to take with each walker. 200 is "
                         "a good number to get a look at the sample space and "
                         "dial in the bounds.")
parser.add_argument('--burn',
                    type=int,
                    default=100,
                    help="The number of samples to discard at the start of each "
                         "MCMC chain. This will usually need to be on the order "
                         "of a few hundred. If your chains are taking too long "
                         "to mix, try narrowing the bounds on the hyperparameters.")
parser.add_argument('--keep',
                    type=int,
                    default=200,
                    help="The number of MCMC samples to keep when fitting the "
                         "profiles. This lets you get a full picture of the "
                         "parameter space but only fit on the number of profiles "
                         "needed.")
parser.add_argument('--full-monte-carlo',
                    action='store_true',
                    help="Set this flag to compute these mean samples using a "
                         "full Monte Carlo simulation instead of error propagation.")
parser.add_argument('--monte-carlo-samples',
                    type=int,
                    default=500,
                    help="The number of Monte Carlo samples to use when "
                         "--full-monte-carlo is set and MAP estimation is used.")
parser.add_argument('--reject-negative',
                    action='store_true',
                    help="Set this flag to reject any Monte Carlo samples that go "
                         "negative during the full Monte Carlo simulation. Only "
                         "has an effect if --full-monte-carlo is set.")
parser.add_argument('--reject-non-monotonic',
                    action='store_true',
                    help="Set this flag to reject any Monte Carlo samples that "
                         "are not monotonic when performing the full Monte Carlo "
                         "simulation. Only has an effect if --full-monte-carlo "
                         "is set.")
parser.add_argument('--no-a-over-L',
                    action='store_true',
                    help="Set this flag to turn off the computation of a/L, "
                         "which can save some time if you don't need gradients/"
                         "scale lengths.")
parser.add_argument('--compute-vol-avg',
                    action='store_true',
                    help="Set this flag to compute the volume average of the "
                         "profile.")
parser.add_argument('--compute-peaking',
                    action='store_true',
                    help="Set this flag to compute the peaking figure of merit "
                         "of the profile.")
parser.add_argument('--compute-TCI',
                    action='store_true',
                    help="Set this flag to compute the integrals along the TCI "
                         "chords. This will only work if the TCI data are loaded.")
parser.add_argument('-i', '--input-filename',
                    help="Filename/path to a CSV or NetCDF file containing the "
                         "profile data to be fit. Note that if you wish to make "
                         "use of the core/edge value, slope constraints you must "
                         "provide t-min and t-max bracketing the times used so "
                         "that the program can find the locations of the magnetic "
                         "axis and GH limiter in the relevant coordinates. "
                         "(Though it will always be able to find the magnetic "
                         "axis if you use a normalized coordinate.) If the "
                         "extension of the file is .csv it will be treated as a "
                         "comma-separated values file, all other extensions will "
                         "be treated as NetCDF files. If using a CSV file, the "
                         "first row should be a comma-separated list of the field "
                         "names, as defined with --abscissa-name and "
                         "--ordinate-name. These columns can be in any order in "
                         "the actual file.")
parser.add_argument('-o', '--output-filename',
                    help="Filename/path to write a NetCDF or CSV file to"
                         "containing the results of the fit. If not specified, "
                         "you will be prompted for a filename upon completing "
                         "the fit.")
parser.add_argument('-x', '--abscissa-name',
                    nargs='+',
                    help="Name(s) of the variable(s) in the input/output NetCDF/"
                         "CSV files that contain the values of the abscissa "
                         "(independent variable(s)). The uncertainty in the "
                         "abscissa must then be in err_ABSCISSA_NAME, if "
                         "present. Note that uncertainties in the abscissa are "
                         "NOT used in the profile fit at present, but will be "
                         "shown on the plot. If you do not provide this when "
                         "using a CSV file, the names will automatically be "
                         "inferred by looking at the order of the header of the "
                         "CSV file. This argument is required when using a "
                         "NetCDF file. You must always put your time variable "
                         "first for this to work properly.")
parser.add_argument('-y', '--ordinate-name',
                    help="Name of the variable in the input/output NetCDF/CSV "
                         "files that contains the values of the ordinate "
                         "(dependent variable). The uncertainty in the ordinate "
                         "must then be in err_ORDINATE_NAME. If you do not "
                         "provide this when using a CSV file, the names will "
                         "automatically be inferred by looking at the order of "
                         "the header of the CSV file. This argument is required "
                         "when using a NetCDF file.")
parser.add_argument('--metadata-lines',
                    type=int,
                    help="Number of lines of metadata at the start of your CSV "
                         "file to read. You can include the shot, times and "
                         "coordinate in the CSV file itself in this manner. See "
                         "the documentation on profiletools.CMod.read_plasma_csv "
                         "for more details. If you leave this out, the program "
                         "will check to see if the first line of your file is of "
                         "the form 'metadata LINES', where LINES is the number of "
                         "lines of metadata present.")
parser.add_argument('--full-auto',
                    action='store_true',
                    help="Set this flag to disable all prompting for missing/"
                         "optional arguments and run fully automatically. The "
                         "program will exit with status 1 if any required "
                         "parameters are missing. The program will still stop to "
                         "allow the user to assess the quality of the fit.")
parser.add_argument('--no-interaction',
                    action='store_true',
                    help="Set this flag to not let the user interact with the "
                         "GUI. The fit will be automatically run and saved, "
                         "along with a picture of the plot, to the output file "
                         "specified.")
parser.add_argument('--no-mainloop',
                    action='store_true',
                    help="Set this flag to disable starting of the Tkinter "
                         "main loop. This is useful for debugging.")
parser.add_argument('--x-lim',
                    type=float,
                    nargs=2,
                    help="The upper and lower bounds for the horizontal plot "
                         "axis. If not provided, these will be set from the data.")
parser.add_argument('--y-lim',
                    type=float,
                    nargs=2,
                    help="The upper and lower bounds for the vertical plot axis. "
                         "If not provided, these will be set from the data.")

args = parser.parse_args()

### ======================== START OF MAIN PROGRAM ======================== ###

# Set up the GUI:
import sys
import socket
# Hackishly augment the path for now:
hostname = socket.gethostname().lower() 
if ('juggernaut' not in hostname and
    'sydney' not in hostname and
    'cosmonaut' not in hostname):
    sys.path.append("/home/markchil/codes/gptools")
    sys.path.append("/home/markchil/codes/profiletools")
    sys.path.append("/home/markchil/codes/efit/development/EqTools")

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.gridspec as mplgs
import tkinter as tk
import tkinter.filedialog
import tkinter.font
import tkinter.ttk
import time
import multiprocessing
import profiletools3 as profiletools
import gptools3 as gptools
import eqtools3 as eqtools
import MDSplus
import os.path
import copy
import re
import scipy
import scipy.io
import scipy.linalg
import numpy
import numpy.linalg
import itertools
import getpass
import inspect
import csv
import pickle as pickle

# What key to use for keyboard shortcuts: command on Mac, control otherwise:
COMMAND_KEY = 'Command' if sys.platform == 'darwin' else 'Control'

# Define the format used to print the date:
DATE_FORMAT = '%d %b %Y %H:%M:%S'

# Define the parameters for the basic Frame elements:
FRAME_PARAMS = {'relief': tk.RAISED, 'borderwidth': 2}

# Regex used to split lists up. This will let the list be delimted by any
# non-numeric characters, where the decimal point and minus sign are considered
# numeric.
LIST_REGEX = r'([-0-9.]+)[^-0-9.]*'

class TreeFileFrame(tk.Frame):
    """Frame to hold the buttons to choose between using the tree or a file,
    as well as the file specification.
    
    All arguments to the constructor are passed to :py:class:`tk.Frame`.
    """
    
    TREE_MODE = 1
    FILE_MODE = 2
    
    def __init__(self, *args, **kwargs):
        # Need to use old, hackish way since tkinter uses old-style classes:
        tk.Frame.__init__(self, *args, **kwargs)
        
        # Create radio buttons to select tree versus file:
        # When the buttons are pressed, they will enable/disable the file
        # selection Entry, Button and the variable specification Entries.
        self.source_state = tk.IntVar(self)
        self.tree_button = tk.Radiobutton(
            self,
            text="tree",
            variable=self.source_state,
            value=self.TREE_MODE,
            command=self.master.update_source
        )
        self.file_button = tk.Radiobutton(
            self,
            text="file:",
            variable=self.source_state,
            value=self.FILE_MODE,
            command=self.master.update_source
        )
        self.tree_button.grid(row=0, column=0)
        self.file_button.grid(row=0, column=1)
        
        # Create text entry to input file path:
        self.path_entry = tk.Entry(self)
        self.path_entry.grid(row=0, column=2, stick=tk.E + tk.W)
        
        # Create button to select file:
        self.choose_file_button = tk.Button(
            self,
            text="choose file",
            command=self.choose_file
        )
        self.choose_file_button.grid(row=0, column=3)
        
        # Set file path entry to expand:
        self.grid_columnconfigure(2, weight=1)
    
    def choose_file(self):
        """Create a dialog to let the user choose which file to read data from.
        """
        filepath = tkinter.filedialog.askopenfilename()
        if filepath:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, filepath)

class VariableNameFrame(tk.Frame):
    """Frame to hold the variable name specification frames.
    """
    def __init__(self, *args, **kwargs):
        # Need to use old, hackish way since tkinter uses old-style classes:
        tk.Frame.__init__(self, *args, **kwargs)
        
        # Create label for variables:
        self.variables_master_label = tk.Label(self, text="variable/column names:")
        self.variables_master_label.grid(row=0, column=0, columnspan=6, sticky=tk.W)
        
        # Create label for time:
        self.time_label = tk.Label(self, text="time:")
        self.time_label.grid(row=1, column=0, sticky=tk.E)
        
        # Create box for time:
        self.time_box = tk.Entry(self, width=4)
        self.time_box.grid(row=1, column=1, sticky='EW')
        
        # Create label for space:
        self.space_label = tk.Label(self, text="space:")
        self.space_label.grid(row=1, column=2, sticky=tk.E)
        
        # Create box for space:
        self.space_box = tk.Entry(self, width=4)
        self.space_box.grid(row=1, column=3, sticky='EW')
        
        # Create label for data:
        self.data_label = tk.Label(self, text="data:")
        self.data_label.grid(row=1, column=4, sticky=tk.E)
        
        # Create box for data:
        self.data_box = tk.Entry(self, width=4)
        self.data_box.grid(row=1, column=5, sticky='EW')
        
        # Create label and box for number of metadata lines:
        self.meta_label = tk.Label(self, text="metadata:")
        self.meta_label.grid(row=1, column=6, sticky='E')
        self.meta_box = tk.Entry(self, width=4)
        self.meta_box.grid(row=1, column=7, sticky='EW')
        
        # Configure boxes to grow:
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(3, weight=1)
        self.grid_columnconfigure(5, weight=1)
        self.grid_columnconfigure(7, weight=1)

class ShotFrame(tk.Frame):
    """Frame to hold specification of the shot number.
    """
    def __init__(self, *args, **kwargs):
        # Need to use old, hackish way since tkinter uses old-style classes:
        tk.Frame.__init__(self, *args, **kwargs)
        
        # Create label for shot:
        self.shot_label = tk.Label(self, text="shot:")
        self.shot_label.grid(row=0, column=0)
        
        # Create box for shot:
        self.shot_box = tk.Entry(self)
        self.shot_box.grid(row=0, column=1, sticky=tk.E + tk.W)
        
        # Allow shot entry to expand to fill:
        self.grid_columnconfigure(1, weight=1)

class SignalCoordinateFrame(tk.Frame):
    """Frame to hold the specification of which signal and coordinates to use.
    """
    def __init__(self, *args, **kwargs):
        # Need to use old, hackish way since tkinter uses old-style classes:
        tk.Frame.__init__(self, *args, **kwargs)
        
        # Create label for signal:
        self.signal_label = tk.Label(self, text="signal:")
        self.signal_label.grid(row=0, column=0, sticky='E')
        
        # Create option menu for signal:
        self.signal_var = tk.StringVar(self)
        self.signal_var.set(list(SYSTEM_OPTIONS.keys())[0])
        self.signal_menu = tk.OptionMenu(
            self,
            self.signal_var,
            *list(SYSTEM_OPTIONS.keys()),
            command=self.master.update_signal
        )
        self.signal_menu.grid(row=0, column=1, sticky='EW')
        
        # Create label for coordinate:
        self.coordinate_label = tk.Label(self, text="coordinate:")
        self.coordinate_label.grid(row=0, column=2, sticky='E')
        
        # Create option menu for coordinate:
        self.coordinate_var = tk.StringVar(self)
        self.coordinate_var.set(COORDINATE_OPTIONS[0])
        self.coordinate_menu = tk.OptionMenu(
            self,
            self.coordinate_var,
            *COORDINATE_OPTIONS
        )
        self.coordinate_menu.grid(row=0, column=3, sticky='EW')

class OptionBox(tk.Frame):
    """Frame to hold a Checkbutton corresponding to a given system.
    """
    def __init__(self, system, *args, **kwargs):
        # Need to use old, hackish way since tkinter uses old-style classes:
        tk.Frame.__init__(self, *args, **kwargs)
        
        self.system = system
        
        self.state_var = tk.IntVar(self)
        self.button = tk.Checkbutton(
            self,
            text=self.system,
            variable=self.state_var
        )
        self.button.grid(row=0, column=0)
        
        # Set default value:
        if self.system not in DEFAULT_EXCLUDE:
            self.button.select()

class SystemFrame(tk.Frame):
    """Frame to handle selection of systems to include.
    """
    def __init__(self, *args, **kwargs):
        # Need to use old, hackish way since tkinter uses old-style classes:
        tk.Frame.__init__(self, *args, **kwargs)
        self.signal = None
        self.buttons = []
        self.update_systems(self.master.signal_coordinate_frame.signal_var.get())
    
    def update_systems(self, signal):
        """Update the list of system options shown to correspond to `signal`.
        """
        # Only update the signal if necessary:
        if signal != self.signal:
            self.signal = signal
            # Delete all of the old buttons:
            for b in self.buttons:
                b.destroy()
            # Create the new buttons:
            self.buttons = [OptionBox(sys, self) for sys in SYSTEM_OPTIONS[signal]]
            for k in range(0, len(self.buttons)):
                self.buttons[k].grid(row=0, column=k)

class EFITFrame(tk.Frame):
    """Frame to handle selection of the EFIT tree to use:
    """
    def __init__(self, *args, **kwargs):
        # Need to use old, hackish way since tkinter uses old-style classes:
        tk.Frame.__init__(self, *args, **kwargs)
        
        self.EFIT_label = tk.Label(self, text="EFIT tree:")
        self.EFIT_label.grid(row=0, column=0, sticky='E')
        
        # Entry to put the tree to use in:
        self.EFIT_field = tk.Entry(self)
        self.EFIT_field.grid(row=0, column=1, sticky='EW')
        
        self.grid_columnconfigure(1, weight=1)

class DataSourceFrame(tk.Frame):
    """Frame to hold all of the components that dictate where the data come from.
    """
    def __init__(self, *args, **kwargs):
        # Need to use old, hackish way since tkinter uses old-style classes:
        tk.Frame.__init__(self, *args, **kwargs)
        
        # Create main label for frame:
        self.frame_label = tk.Label(self, text="Data Source", font=tkinter.font.Font(weight=tkinter.font.BOLD))
        self.frame_label.grid(row=0, sticky='W')
        
        # Create frame to hold tree/file selector row:
        self.tree_file_frame = TreeFileFrame(self)
        self.tree_file_frame.grid(row=1, sticky='EW')
        
        # Create frame to hold variable name selector row:
        self.variable_name_frame = VariableNameFrame(self)
        self.variable_name_frame.grid(row=2, sticky='EW')
        
        # Create frame to hold shot selector row:
        self.shot_frame = ShotFrame(self)
        self.shot_frame.grid(row=3, sticky='EW')
        
        # Create frame to hold signal/coordinate selection menus:
        self.signal_coordinate_frame = SignalCoordinateFrame(self)
        self.signal_coordinate_frame.grid(row=4, sticky='EW')
        
        # Create frame to hold signal selection check buttons:
        self.system_frame = SystemFrame(self)
        self.system_frame.grid(row=5, sticky='W')
        
        # Create frame to hold EFIT tree selection:
        self.EFIT_frame = EFITFrame(self)
        self.EFIT_frame.grid(row=6, sticky='EW')
        
        # Allow columns to grow:
        self.grid_columnconfigure(0, weight=1)
        
        # Set default conditions:
        self.tree_file_frame.tree_button.invoke()
    
    def update_source(self):
        """Update changes between tree and file mode.
        
        In tree mode:
            
            * File name, selection and variable name boxes are disabled.
            * Signal and system selectors are enabled.
        
        In file mode:
            
            * File name, selection and variable name boxes are enabled.
            * Signal and system selectors are disabled.
        """
        if self.tree_file_frame.source_state.get() == self.tree_file_frame.TREE_MODE:
            self.tree_file_frame.path_entry.config(state=tk.DISABLED)
            self.tree_file_frame.choose_file_button.config(state=tk.DISABLED)
            for w in self.variable_name_frame.winfo_children():
                w.config(state=tk.DISABLED)
            self.signal_coordinate_frame.signal_label.config(state=tk.NORMAL)
            self.signal_coordinate_frame.signal_menu.config(state=tk.NORMAL)
            for b in self.system_frame.buttons:
                b.button.config(state=tk.NORMAL)
        elif self.tree_file_frame.source_state.get() == self.tree_file_frame.FILE_MODE:
            self.tree_file_frame.path_entry.config(state=tk.NORMAL)
            self.tree_file_frame.choose_file_button.config(state=tk.NORMAL)
            for w in self.variable_name_frame.winfo_children():
                w.config(state=tk.NORMAL)
            self.signal_coordinate_frame.signal_label.config(state=tk.DISABLED)
            self.signal_coordinate_frame.signal_menu.config(state=tk.DISABLED)
            for b in self.system_frame.buttons:
                b.button.config(state=tk.DISABLED)
    
    def update_signal(self, signal):
        """Updates the available systems when the `signal` changes.
        """
        self.system_frame.update_systems(signal)

class TimeWindowFrame(tk.Frame):
    """Frame to specify time window/points.
    """
    
    WINDOW_MODE = 1
    POINT_MODE = 2
    
    def __init__(self, *args, **kwargs):
        # Need to use old, hackish way since tkinter uses old-style classes:
        tk.Frame.__init__(self, *args, **kwargs)
        
        # Create radio buttons to select between window and points:
        self.method_state = tk.IntVar(self)
        self.window_button = tk.Radiobutton(self,
                                            text="time window:",
                                            variable=self.method_state,
                                            value=self.WINDOW_MODE,
                                            command=self.update_method)
        self.point_button = tk.Radiobutton(self,
                                           text="time points:",
                                           variable=self.method_state,
                                           value=self.POINT_MODE,
                                           command=self.update_method)
        self.window_button.grid(row=0, column=0, sticky='W')
        self.point_button.grid(row=1, column=0, sticky='W')
        
        # Create labels and fields to hold time window:
        self.t_min_box = tk.Entry(self, width=6)
        self.t_min_box.grid(row=0, column=1, sticky='EW')
        self.t_max_box = tk.Entry(self, width=6)
        self.t_max_box.grid(row=0, column=3, sticky='EW')
        self.t_min_units = tk.Label(self, text="s to")
        self.t_min_units.grid(row=0, column=2)
        self.t_max_units = tk.Label(self, text="s")
        self.t_max_units.grid(row=0, column=4)
        
        # Create labels and fields to hold time points:
        self.times_box = tk.Entry(self)
        self.times_box.grid(row=1, column=1, columnspan=4, sticky='EW')
        
        # Allow elements to resize:
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(3, weight=1)
    
    def update_method(self):
        """Update whether the window or points boxes are enabled.
        """
        if self.method_state.get() == self.WINDOW_MODE:
            self.times_box.config(state=tk.DISABLED)
            self.t_min_box.config(state=tk.NORMAL)
            self.t_min_units.config(state=tk.NORMAL)
            self.t_max_box.config(state=tk.NORMAL)
            self.t_max_units.config(state=tk.NORMAL)
        else:
            self.times_box.config(state=tk.NORMAL)
            self.t_min_box.config(state=tk.DISABLED)
            self.t_min_units.config(state=tk.DISABLED)
            self.t_max_box.config(state=tk.DISABLED)
            self.t_max_units.config(state=tk.DISABLED)

class MethodFrame(tk.Frame):
    """Frame to select averaging/uncertainty methods.
    """
    def __init__(self, *args, **kwargs):
        # Need to use old, hackish way since tkinter uses old-style classes:
        tk.Frame.__init__(self, *args, **kwargs)
        
        # Create label for method:
        self.method_label = tk.Label(self, text="averaging method:")
        self.method_label.grid(row=0, column=0, sticky='E')
        
        # Create option menu for methods:
        self.method_var = tk.StringVar(self)
        self.method_var.set(METHOD_OPTIONS[0])
        self.method_menu = tk.OptionMenu(self, self.method_var, *METHOD_OPTIONS, command=self.update_method)
        self.method_menu.grid(row=0, column=1, sticky='W')
        
        # Create label for error method:
        self.error_method_label = tk.Label(self, text="uncertainty method:")
        self.error_method_label.grid(row=1, column=0, sticky='E')
        
        # Create option menu for error methods:
        self.error_method_var = tk.StringVar(self)
        self.error_method_var.set(ERROR_METHOD_OPTIONS[0])
        self.error_method_menu = tk.OptionMenu(self, self.error_method_var, *ERROR_METHOD_OPTIONS)
        self.error_method_menu.grid(row=1, column=1, sticky='W')
        
        # Create checkbox for weighted averaging:
        self.weighted_state = tk.IntVar(self)
        self.weighted_button = tk.Checkbutton(self, text="weighted", variable=self.weighted_state)
        self.weighted_button.select()
        self.weighted_button.grid(row=0, column=2, sticky='W')
    
    def update_method(self, new_meth):
        """Update averaging method.
        
        For 'all points', the ability to specify weighting and uncertainty
        method is disabled.
        """
        if new_meth == 'all points':
            self.error_method_menu.config(state=tk.DISABLED)
            self.error_method_label.config(state=tk.DISABLED)
            self.weighted_button.config(state=tk.DISABLED)
        else:
            self.error_method_menu.config(state=tk.NORMAL)
            self.error_method_label.config(state=tk.NORMAL)
            self.weighted_button.config(state=tk.NORMAL)

class AveragingFrame(tk.Frame):
    """Frame to hold the components specifying how averaging is performed.
    """
    def __init__(self, *args, **kwargs):
        # Need to use old, hackish way since tkinter uses old-style classes:
        tk.Frame.__init__(self, *args, **kwargs)
        
        # Create main label for frame:
        self.frame_label = tk.Label(self, text="Time Points/Averaging", font=tkinter.font.Font(weight=tkinter.font.BOLD))
        self.frame_label.grid(row=0, sticky='W')
        
        # Create frame to hold time window selection:
        self.time_window_frame = TimeWindowFrame(self)
        self.time_window_frame.grid(row=1, sticky='EW')
        
        # Create frame to hold averaging selection:
        self.method_frame = MethodFrame(self)
        self.method_frame.grid(row=2, sticky='W')
        
        # Allow elements to resize:
        self.grid_columnconfigure(0, weight=1)
        
        # Set default conditions:
        self.time_window_frame.window_button.invoke()

class OutlierFrame(tk.Frame):
    """Frame to control how outlier rejection is performed.
    """
    def __init__(self, *args, **kwargs):
        # Need to use old, hackish way since tkinter uses old-style classes:
        tk.Frame.__init__(self, *args, **kwargs)
        
        # Create main label for frame:
        self.frame_label = tk.Label(self, text="Outlier Rejection", font=tkinter.font.Font(weight=tkinter.font.BOLD))
        self.frame_label.grid(row=0, sticky='W')
        
        # Create checkbuttons to select types:
        self.extreme_state = tk.IntVar(self)
        self.extreme_button = tk.Checkbutton(self,
                                             text="extreme change",
                                             variable=self.extreme_state,
                                             command=self.update_extreme)
        self.extreme_button.grid(row=1, column=0, sticky='W')
        self.outlier_state = tk.IntVar(self)
        self.outlier_button = tk.Checkbutton(self,
                                             text="distance from fit",
                                             variable=self.outlier_state,
                                             command=self.update_outlier)
        self.outlier_button.grid(row=2, column=0, sticky='W')
        
        # Create boxes and labels to specify thresholds:
        self.extreme_thresh_label = tk.Label(self, text="threshold:")
        self.extreme_thresh_label.grid(row=1, column=1)
        self.extreme_thresh_box = tk.Entry(self, width=6)
        self.extreme_thresh_box.insert(tk.END, '9')
        self.extreme_thresh_box.grid(row=1, column=2, sticky='EW')
        self.extreme_thresh_unit_label = tk.Label(self, text=u"\u03C3")
        self.extreme_thresh_unit_label.grid(row=1, column=3, sticky='W')
        
        self.outlier_thresh_label = tk.Label(self, text="threshold:")
        self.outlier_thresh_label.grid(row=2, column=1)
        self.outlier_thresh_box = tk.Entry(self, width=6)
        self.outlier_thresh_box.insert(tk.END, '3')
        self.outlier_thresh_box.grid(row=2, column=2, sticky='EW')
        self.outlier_thresh_unit_label = tk.Label(self, text=u"\u03C3")
        self.outlier_thresh_unit_label.grid(row=2, column=3, sticky='W')
        
        # Create label, entry to remove specific points:
        self.specific_frame = tk.Frame(self)
        self.specific_label = tk.Label(self.specific_frame, text="remove points:")
        self.specific_label.grid(row=0, column=0, sticky='E')
        self.specific_box = tk.Entry(self.specific_frame)
        self.specific_box.grid(row=0, column=1, sticky='EW')
        
        # Create checkbutton to show/remove indices:
        self.show_idx_state = tk.IntVar(self.specific_frame)
        self.show_idx_button = tk.Checkbutton(
            self.specific_frame,
            text="plot indices",
            variable=self.show_idx_state,
            command=self.update_show_idx
        )
        self.show_idx_button.grid(row=0, column=2, sticky='W')
        
        self.specific_frame.grid_columnconfigure(1, weight=1)
        self.specific_frame.grid(row=3, column=0, columnspan=4, sticky='EW')
        
        self.grid_columnconfigure(3, weight=1)
        
        self.idx_plotted = None
        
        self.update_extreme()
        self.update_outlier()
    
    def update_extreme(self):
        """Update the state of extreme change rejection.
        """
        if self.extreme_state.get():
            self.extreme_thresh_label.config(state=tk.NORMAL)
            self.extreme_thresh_box.config(state=tk.NORMAL)
            self.extreme_thresh_unit_label.config(state=tk.NORMAL)
        else:
            self.extreme_thresh_label.config(state=tk.DISABLED)
            self.extreme_thresh_box.config(state=tk.DISABLED)
            self.extreme_thresh_unit_label.config(state=tk.DISABLED)
    
    def update_outlier(self):
        """Update the state of outlier rejection.
        """
        if self.outlier_state.get():
            self.outlier_thresh_label.config(state=tk.NORMAL)
            self.outlier_thresh_box.config(state=tk.NORMAL)
            self.outlier_thresh_unit_label.config(state=tk.NORMAL)
        else:
            self.outlier_thresh_label.config(state=tk.DISABLED)
            self.outlier_thresh_box.config(state=tk.DISABLED)
            self.outlier_thresh_unit_label.config(state=tk.DISABLED)
    
    def update_show_idx(self):
        """Update whether or not indices are shown.
        """
        # Remove previous labels, if present.
        if self.idx_plotted is not None:
            for l in self.idx_plotted:
                try:
                    l.remove()
                except ValueError:
                    pass
            self.idx_plotted = None
        if self.show_idx_state.get():
            # Only do anything if the data have been loaded.
            if self.master.master.master.combined_p is not None:
                self.idx_plotted = [
                    self.master.master.master.plot_frame.a_val.text(x, y, str(i))
                    for i, x, y in zip(
                        list(range(0, len(self.master.master.master.combined_p.y))),
                        self.master.master.master.combined_p.X[:, 0],
                        self.master.master.master.combined_p.y
                    )
                ]
        self.master.master.master.plot_frame.canvas.draw()

class KernelTypeFrame(tk.Frame):
    """Frame to handle specification of which kernel to use.
    """
    def __init__(self, *args, **kwargs):
        # Need to use old, hackish way since tkinter uses old-style classes:
        tk.Frame.__init__(self, *args, **kwargs)
        
        # Create label for type:
        self.k_label = tk.Label(self, text="kernel type:")
        self.k_label.grid(row=0, column=0, sticky='E')
        
        # Create option menu for type:
        self.k_var = tk.StringVar(self)
        self.k_var.set(list(HYPERPARAMETERS.keys())[0])
        self.k_menu = tk.OptionMenu(
            self,
            self.k_var,
            *list(HYPERPARAMETERS.keys()),
            command=self.master.update_kernel
        )
        self.k_menu.grid(row=0, column=1, sticky='W')
        
        # Create check button to select only core data:
        self.core_only_state = tk.IntVar(self)
        self.core_only_button = tk.Checkbutton(
            self,
            text="core only",
            variable=self.core_only_state
        )
        self.core_only_button.grid(row=0, column=2, sticky='W')

class KernelBoundsFrame(tk.Frame):
    """Frame to handle specification of bounds on the hyperparameters.
    
    Parameters
    ----------
    hyperparameters : list
        List of the hyperparameters to make boxes for.
    
    All other parameters/kwargs are passed to :py:class:`tk.Frame`.
    """
    def __init__(self, hyperparameters, *args, **kwargs):
        # Need to use old, hackish way since tkinter uses old-style classes:
        tk.Frame.__init__(self, *args, **kwargs)
        
        self.hyperparameters = hyperparameters
        
        self.labels = []
        self.lower_bounds = []
        self.to_labels = []
        self.upper_bounds = []
        
        for k, hp in zip(range(0, len(self.hyperparameters)), self.hyperparameters):
            self.labels.append(
                tk.Label(
                    self,
                    text="%s, %s:" % (self.hyperparameters[hp], hp,)
                )
            )
            self.lower_bounds.append(tk.Entry(self, width=6))
            self.to_labels.append(tk.Label(self, text="to"))
            self.upper_bounds.append(tk.Entry(self, width=6))
            
            self.labels[k].grid(row=k, column=0, sticky='E')
            self.lower_bounds[k].grid(row=k, column=1, sticky='EW')
            self.to_labels[k].grid(row=k, column=2)
            self.upper_bounds[k].grid(row=k, column=3, sticky='EW')
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(3, weight=1)

class ConstraintsFrame(tk.Frame):
    """Frame to handle selection of which constraints are applied where.
    """
    def __init__(self, *args, **kwargs):
        # Need to use old, hackish way since tkinter uses old-style classes:
        tk.Frame.__init__(self, *args, **kwargs)
        
        # Checkbox for core constraint:
        self.core_state = tk.IntVar(self)
        self.core_button = tk.Checkbutton(
            self,
            text="core constraint",
            variable=self.core_state,
            command=self.update_core
        )
        self.core_button.grid(row=0, column=0, sticky='W')
        
        # Checkbox for edge constraint:
        self.edge_state = tk.IntVar(self)
        self.edge_button = tk.Checkbutton(
            self,
            text="edge constraint",
            variable=self.edge_state,
            command=self.update_edge
        )
        self.edge_button.grid(row=1, column=0, sticky='W')
        
        # Label for core location:
        self.core_label = tk.Label(self, text="location:")
        self.core_label.grid(row=0, column=1, sticky='E')
        
        # Label for edge locations:
        self.edge_label = tk.Label(self, text="locations:")
        self.edge_label.grid(row=1, column=1, sticky='E')
        
        # Box for core location:
        self.core_loc = tk.Entry(self)
        self.core_loc.grid(row=0, column=2, sticky='EW')
        
        # Box for edge location:
        self.edge_loc = tk.Entry(self)
        self.edge_loc.grid(row=1, column=2, sticky='EW')
        
        # Allow boxes to expand:
        self.grid_columnconfigure(2, weight=1)
    
    def update_core(self):
        """Update the core constraint. Enable location box if constraint is on.
        """
        if self.core_state.get():
            self.core_label.config(state=tk.NORMAL)
            self.core_loc.config(state=tk.NORMAL)
        else:
            self.core_label.config(state=tk.DISABLED)
            self.core_loc.config(state=tk.DISABLED)
    
    def update_edge(self):
        """Update the edge constraint. Enable location box if constraint is on.
        """
        if self.edge_state.get():
            self.edge_label.config(state=tk.NORMAL)
            self.edge_loc.config(state=tk.NORMAL)
        else:
            self.edge_label.config(state=tk.DISABLED)
            self.edge_loc.config(state=tk.DISABLED)

class KernelFrame(tk.Frame):
    """Frame to hold components used to specify the covariance kernel.
    """
    def __init__(self, *args, **kwargs):
        # Need to use old, hackish way since tkinter uses old-style classes:
        tk.Frame.__init__(self, *args, **kwargs)
        
        # Create main label for frame:
        self.frame_label = tk.Label(self, text="Covariance Kernel", font=tkinter.font.Font(weight=tkinter.font.BOLD))
        self.frame_label.grid(row=0, sticky='W')
        
        # Create frame to hold kernel type:
        self.kernel_type_frame = KernelTypeFrame(self)
        self.kernel_type_frame.grid(row=1, sticky='W')
        self.k = self.kernel_type_frame.k_var.get()
        
        # Create frame to hold hyperparameter bounds:
        self.bounds_label = tk.Label(self, text="hyperparameter bounds:")
        self.bounds_label.grid(row=2, sticky='W')
        self.bounds_frame = KernelBoundsFrame(HYPERPARAMETERS[self.kernel_type_frame.k_var.get()], self)
        self.bounds_frame.grid(row=3, sticky='EW')
        
        # Create frame to hold constraint checkboxes:
        self.constraints_frame = ConstraintsFrame(self)
        self.constraints_frame.grid(row=4, sticky='EW')
        
        # Allow boxes to expand:
        self.grid_columnconfigure(0, weight=1)
        
        # Initial settings:
        self.constraints_frame.core_button.invoke()
        self.constraints_frame.edge_button.invoke()
    
    def update_kernel(self, k):
        """Update the covariance kernel, redraw the bounds selection.
        """
        # Only update if necessary:
        if k != self.k:
            self.bounds_frame.destroy()
            self.bounds_frame = KernelBoundsFrame(HYPERPARAMETERS[k], self)
            self.bounds_frame.grid(row=3, sticky='EW')
            self.k = k

class FittingMethodFrame(tk.Frame):
    """Frame to handle selection between MAP and MCMC.
    """
    
    USE_MAP = 1
    USE_MCMC = 2
    
    def __init__(self, *args, **kwargs):
        # Need to use old, hackish way since tkinter uses old-style classes:
        tk.Frame.__init__(self, *args, **kwargs)
        
        # Create radio buttons to select MAP versus MCMC:
        # When state changes, enable/disable MCMC settings.
        self.method_state = tk.IntVar(self)
        self.MAP_button = tk.Radiobutton(
            self,
            text="MAP",
            variable=self.method_state,
            value=self.USE_MAP,
            command=self.master.update_method
        )
        self.MCMC_button = tk.Radiobutton(
            self,
            text="MCMC",
            variable=self.method_state,
            value=self.USE_MCMC,
            command=self.master.update_method
        )
        self.MAP_button.grid(row=0, column=0)
        self.MCMC_button.grid(row=0, column=3)
        
        # Create label and box to set number of random starts:
        self.starts_label = tk.Label(self, text="random starts:")
        self.starts_label.grid(row=0, column=1, sticky='E')
        self.starts_box = tk.Entry(self, width=6)
        self.starts_box.grid(row=0, column=2, sticky='EW')

class MCMCFrame(tk.Frame):
    """Frame to hold selection of MCMC parameters.
    """
    def __init__(self, *args, **kwargs):
        # Need to use old, hackish way since tkinter uses old-style classes:
        tk.Frame.__init__(self, *args, **kwargs)
        
        self.walker_label = tk.Label(self, text="walkers:")
        self.walker_label.grid(row=0, column=0, sticky='E')
        self.walker_box = tk.Entry(self, width=4)
        self.walker_box.insert(tk.END, '200')
        self.walker_box.grid(row=0, column=1, sticky='EW')
        
        self.sample_label = tk.Label(self, text="samples:")
        self.sample_label.grid(row=0, column=2, sticky='E')
        self.sample_box = tk.Entry(self, width=4)
        self.sample_box.insert(tk.END, '200')
        self.sample_box.grid(row=0, column=3, sticky='EW')
        
        self.burn_label = tk.Label(self, text="burn:")
        self.burn_label.grid(row=0, column=4, sticky='E')
        self.burn_box = tk.Entry(self, width=4)
        self.burn_box.insert(tk.END, '100')
        self.burn_box.grid(row=0, column=5, sticky='EW')
        
        self.keep_label = tk.Label(self, text="keep:")
        self.keep_label.grid(row=0, column=6, sticky='E')
        self.keep_box = tk.Entry(self, width=4)
        self.keep_box.insert(tk.END, '200')
        self.keep_box.grid(row=0, column=7, sticky='EW')
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(3, weight=1)
        self.grid_columnconfigure(5, weight=1)
        self.grid_columnconfigure(7, weight=1)

class MCMCConstraintFrame(tk.Frame):
    """Frame to hold selection of properties of full Monte Carlo sampling.
    """
    def __init__(self, *args, **kwargs):
        # Need to use old, hackish way since tkinter uses old-style classes:
        tk.Frame.__init__(self, *args, **kwargs)
        
        # Create button to select full Monte Carlo:
        # Enable additional options when selected.
        self.full_MC_state = tk.IntVar(self)
        self.full_MC_button = tk.Checkbutton(
            self,
            text="use full Monte Carlo",
            variable=self.full_MC_state,
            command=self.update_full_MC
        )
        self.full_MC_button.grid(row=0, column=0, sticky='W')
        
        # Create label and box to specify the number of samples used when using
        # MAP estimation:
        self.samples_label = tk.Label(self, text="samples:")
        self.samples_label.grid(row=0, column=1, sticky='E')
        
        self.samples_box = tk.Entry(self, width=4)
        self.samples_box.grid(row=0, column=2, sticky='EW')
        
        # Create button to select positivity constraint:
        self.pos_state = tk.IntVar(self)
        self.pos_button = tk.Checkbutton(self,
                                         text="reject negative samples",
                                         variable=self.pos_state)
        self.pos_button.grid(row=1, column=0, sticky='W')
        
        # Create button to select monotonicity constraint:
        self.mono_state = tk.IntVar(self)
        self.mono_button = tk.Checkbutton(self,
                                          text="reject non-monotonic samples",
                                          variable=self.mono_state)
        self.mono_button.grid(row=2, column=0, sticky='W')
        
        self.grid_columnconfigure(2, weight=1)
    
    def update_full_MC(self):
        """Update state of full Monte Carlo.
        """
        if self.full_MC_state.get():
            self.pos_button.config(state=tk.NORMAL)
            if self.master.master.master.eval_frame.a_L_state.get():
                self.mono_button.config(state=tk.NORMAL)
            if self.master.method_frame.method_state.get() == self.master.method_frame.USE_MAP:
                self.samples_label.config(state=tk.NORMAL)
                self.samples_box.config(state=tk.NORMAL)
            else:
                self.samples_label.config(state=tk.DISABLED)
                self.samples_box.config(state=tk.DISABLED)
        else:
            self.samples_label.config(state=tk.DISABLED)
            self.samples_box.config(state=tk.DISABLED)
            self.pos_button.config(state=tk.DISABLED)
            self.mono_button.config(state=tk.DISABLED)

class FittingFrame(tk.Frame):
    """Frame to hold the components controlling the fit.
    """
    def __init__(self, *args, **kwargs):
        # Need to use old, hackish way since tkinter uses old-style classes:
        tk.Frame.__init__(self, *args, **kwargs)
        
        # Create main label for frame:
        self.frame_label = tk.Label(self, text="Fitting Method", font=tkinter.font.Font(weight=tkinter.font.BOLD))
        self.frame_label.grid(row=0, sticky='W')
        
        # Create frame to hold fitting method selection:
        self.method_frame = FittingMethodFrame(self)
        self.method_frame.grid(row=1, sticky='W')
        
        # Create frame to hold MCMC parameters:
        self.MCMC_frame = MCMCFrame(self)
        self.MCMC_frame.grid(row=2, sticky='EW')
        
        # Create frame to hold MCMC constraint options:
        self.MCMC_constraint_frame = MCMCConstraintFrame(self)
        self.MCMC_constraint_frame.grid(row=3, sticky='EW')
        
        self.grid_columnconfigure(0, weight=1)
        
        self.method_frame.MAP_button.invoke()
        self.MCMC_constraint_frame.update_full_MC()
    
    def update_method(self):
        """Update the fitting method used, enabling/disabling the MCMC options.
        """
        self.MCMC_constraint_frame.update_full_MC()
        if self.method_frame.method_state.get() == self.method_frame.USE_MAP:
            self.method_frame.starts_label.config(state=tk.NORMAL)
            self.method_frame.starts_box.config(state=tk.NORMAL)
            for w in self.MCMC_frame.winfo_children():
                w.config(state=tk.DISABLED)
        else:
            self.method_frame.starts_label.config(state=tk.DISABLED)
            self.method_frame.starts_box.config(state=tk.DISABLED)
            for w in self.MCMC_frame.winfo_children():
                w.config(state=tk.NORMAL)

class EvaluationFrame(tk.Frame):
    """Frame to control where/what is evaluated.
    """
    
    UNIFORM_GRID = 1
    POINTS = 2
    
    def __init__(self, *args, **kwargs):
        # Need to use old, hackish way since tkinter uses old-style classes:
        tk.Frame.__init__(self, *args, **kwargs)
        
        # Create main label for frame:
        self.frame_label = tk.Label(
            self,
            text="Evaluation",
            font=tkinter.font.Font(weight=tkinter.font.BOLD)
        )
        self.frame_label.grid(row=0, sticky='W')
        
        # Create radio buttons for uniform grid versus specific points:
        self.method_state = tk.IntVar(self)
        self.uniform_button = tk.Radiobutton(
            self,
            text="uniform grid:",
            variable=self.method_state,
            value=self.UNIFORM_GRID,
            command=self.update_method
        )
        self.points_button = tk.Radiobutton(
            self,
            text="specific points:",
            variable=self.method_state,
            value=self.POINTS,
            command=self.update_method
        )
        self.uniform_button.grid(row=1, column=0, sticky='W')
        self.points_button.grid(row=2, column=0, sticky='W')
        
        # Create labels and boxes for setting parameters:
        self.npts_box = tk.Entry(self, width=4)
        self.npts_box.grid(row=1, column=1, sticky='EW')
        self.npts_label = tk.Label(self, text="points from")
        self.npts_label.grid(row=1, column=2)
        self.x_min_box = tk.Entry(self, width=4)
        self.x_min_box.grid(row=1, column=3, sticky='EW')
        self.to_label = tk.Label(self, text="to")
        self.to_label.grid(row=1, column=4)
        self.x_max_box = tk.Entry(self, width=4)
        self.x_max_box.grid(row=1, column=5, sticky='EW')
        
        self.x_points_box = tk.Entry(self)
        self.x_points_box.grid(row=2, column=1, columnspan=5, sticky='EW')
        
        # Create frame to hold options of things to evaluate:
        self.eval_option_frame = tk.Frame(self)
        
        # Create label for compute options:
        self.compute_label = tk.Label(self.eval_option_frame, text="compute:")
        self.compute_label.grid(row=0, column=0, sticky='E')
        
        # Create checkbox to select whether or not a/L is computed:
        self.a_L_state = tk.IntVar(self)
        self.a_L_button = tk.Checkbutton(
            self.eval_option_frame,
            text="a/L",
            variable=self.a_L_state,
            command=self.update_a_L
        )
        self.a_L_button.grid(row=0, column=1, sticky='W')
        
        # Create checkbox to select whether or not volume average is computed:
        self.vol_avg_state = tk.IntVar(self)
        self.vol_avg_button = tk.Checkbutton(
            self.eval_option_frame,
            text="volume average",
            variable=self.vol_avg_state
        )
        self.vol_avg_button.grid(row=0, column=2, sticky='W')
        
        # Create checkbox to select whether or not peaking is computed:
        self.peaking_state = tk.IntVar(self)
        self.peaking_button = tk.Checkbutton(
            self.eval_option_frame,
            text="peaking",
            variable=self.peaking_state
        )
        self.peaking_button.grid(row=0, column=3, sticky='W')
        
        # Create checkbox to select whether or not TCI integrals are computed:
        self.TCI_state = tk.IntVar(self)
        self.TCI_button = tk.Checkbutton(
            self.eval_option_frame,
            text="TCI",
            variable=self.TCI_state
        )
        self.TCI_button.grid(row=0, column=4, sticky='W')
        
        self.eval_option_frame.grid(row=3, column=0, sticky='W', columnspan=6)
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(3, weight=1)
        self.grid_columnconfigure(5, weight=1)
        
        self.uniform_button.invoke()
        self.a_L_button.select()
    
    def update_method(self):
        """Update the method between being on a uniform grid versus specific points.
        """
        if self.method_state.get() == self.UNIFORM_GRID:
            self.npts_box.config(state=tk.NORMAL)
            self.npts_label.config(state=tk.NORMAL)
            self.x_min_box.config(state=tk.NORMAL)
            self.to_label.config(state=tk.NORMAL)
            self.x_max_box.config(state=tk.NORMAL)
            self.x_points_box.config(state=tk.DISABLED)
        else:
            self.npts_box.config(state=tk.DISABLED)
            self.npts_label.config(state=tk.DISABLED)
            self.x_min_box.config(state=tk.DISABLED)
            self.to_label.config(state=tk.DISABLED)
            self.x_max_box.config(state=tk.DISABLED)
            self.x_points_box.config(state=tk.NORMAL)
    
    def update_a_L(self):
        """Update the options available and plot shown based on whether or not a/L is computed.
        """
        if not self.a_L_state.get():
            self.master.master.master.plot_frame.a_grad.set_visible(False)
            self.master.master.master.plot_frame.a_a_L.set_visible(False)
            self.master.master.master.plot_frame.a_val.change_geometry(1, 1, 1)
        else:
            self.master.master.master.plot_frame.a_val.change_geometry(3, 1, 1)
            self.master.master.master.plot_frame.a_grad.set_visible(True)
            self.master.master.master.plot_frame.a_a_L.set_visible(True)
        self.master.master.master.plot_frame.canvas.draw()
        
        if self.a_L_state.get() and self.master.master.fitting_frame.MCMC_constraint_frame.full_MC_state.get():
            self.master.master.fitting_frame.MCMC_constraint_frame.mono_button.config(state=tk.NORMAL)
        else:
            self.master.master.fitting_frame.MCMC_constraint_frame.mono_button.config(state=tk.DISABLED)

class StatusBox(tk.Frame):
    """Frame to hold a box that conveys useful status information.
    """
    def __init__(self, *args, **kwargs):
        # Need to use old, hackish way since tkinter uses old-style classes:
        tk.Frame.__init__(self, *args, **kwargs)
        
        self.history_box = tk.Text(
            self,
            width=30,
            height=6,
            wrap='word'
        )
        self.history_box.grid(row=1, sticky='EWNS')
        self.add_line(
            'This is {progname} version {ver}, launched at {time}. {cores} '
            'cores detected.\n{progname} IS DEPRECATED. YOU SHOULD USE gpfit '
            'FOR FUTURE ANALYSIS. gpfit adds the ability to save/restore '
            'settings, supports more advanced specification of the priors for '
            'hyperparameters and has new default priors informed by detailed '
            'analysis of synthetic data. {progname} has been left in place so '
            'that old analysis codes will continue to function.'.format(
                progname=PROG_NAME,
                ver=__version__,
                time=time.strftime(DATE_FORMAT),
                cores=multiprocessing.cpu_count()
            )
        )
        self.history_scroll = tk.Scrollbar(self)
        self.history_scroll.grid(row=1, column=1, sticky='NS')
        self.history_scroll.config(command=self.history_box.yview)
        self.history_box.config(yscrollcommand=self.history_scroll.set)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self.history_box.bind("<1>", lambda event: self.history_box.focus_set())
    
    def add_line(self, s):
        """Add a line to the history box and print it to stdout.
        """
        self.history_box.config(state=tk.NORMAL)
        print(s)
        sys.stdout.flush()
        self.history_box.insert(tk.END, s + '\n')
        self.history_box.config(state=tk.DISABLED)
        self.history_box.yview(tk.END)
        self.history_box.update()

class ControlBox(tk.Frame):
    """Frame to hold the various buttons to control the program.
    """
    def __init__(self, *args, **kwargs):
        # Need to use old, hackish way since tkinter uses old-style classes:
        tk.Frame.__init__(self, *args, **kwargs)
        
        # Create buttons:
        self.load_button = tk.Button(self, text="load data", command=self.master.master.load_data)
        self.load_button.grid(row=1, column=0)
        self.avg_button = tk.Button(self, text="plot data", command=self.master.master.average_data)
        self.avg_button.grid(row=1, column=1)
        self.fit_button = tk.Button(self, text="fit data", command=self.master.master.fit_data)
        self.fit_button.grid(row=1, column=2)
        self.save_button = tk.Button(self, text="save fit", command=self.master.master.save_fit)
        self.save_button.grid(row=1, column=3)
        self.exit_button = tk.Button(self, text="exit", command=self.master.master.exit)
        self.exit_button.grid(row=1, column=4)

class PlotFrame(tk.Frame):
    """Frame to hold the plots.
    """
    def __init__(self, *args, **kwargs):
        # Need to use old, hackish way since tkinter uses old-style classes:
        tk.Frame.__init__(self, *args, **kwargs)
        
        self.f = Figure()
        self.suptitle = self.f.suptitle('')
        self.a_val = self.f.add_subplot(3, 1, 1)
        self.a_grad = self.f.add_subplot(3, 1, 2, sharex=self.a_val)
        self.a_a_L = self.f.add_subplot(3, 1, 3, sharex=self.a_val)
        self.canvas = FigureCanvasTkAgg(self.f, master=self)
        self.canvas.show()
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky='NESW')
        
        # Need to put the toolbar in its own frame, since it automatically calls
        # pack on itself, but I am using grid.
        self.toolbar_frame = tk.Frame(self)
        self.toolbar = NavigationToolbar2TkAgg(self.canvas, self.toolbar_frame)
        self.toolbar.update()
        self.toolbar_frame.grid(row=1, column=0, sticky='EW')
        
        self.canvas.mpl_connect('button_press_event', lambda event: self.canvas._tkcanvas.focus_set())
        self.canvas.mpl_connect('key_press_event', self.on_key_event)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
    def on_key_event(self, evt):
        """Tie keys to the toolbar.
        """
        key_press_handler(evt, self.canvas, self.toolbar)

class PlotParamFrame(tk.Frame):
    """Frame to let the user set parameters of the plotting.
    """
    def __init__(self, *args, **kwargs):
        # Need to use old, hackish way since tkinter uses old-style classes:
        tk.Frame.__init__(self, *args, **kwargs)
        
        self.limits_label = tk.Label(self, text="plot limits:")
        self.limits_label.grid(row=0, column=0, sticky='W', columnspan=4)
        
        self.x_lim_label = tk.Label(self, text="x:")
        self.x_lim_label.grid(row=1, column=0, sticky='E')
        self.x_lb_box = tk.Entry(self)
        self.x_lb_box.grid(row=1, column=1, sticky='EW')
        self.x_to_label = tk.Label(self, text="to")
        self.x_to_label.grid(row=1, column=2, sticky='EW')
        self.x_ub_box = tk.Entry(self)
        self.x_ub_box.grid(row=1, column=3, sticky='EW')
        
        self.y_lim_label = tk.Label(self, text="y:")
        self.y_lim_label.grid(row=2, column=0, sticky='E')
        self.y_lb_box = tk.Entry(self)
        self.y_lb_box.grid(row=2, column=1, sticky='EW')
        self.y_to_label = tk.Label(self, text="to")
        self.y_to_label.grid(row=2, column=2, sticky='EW')
        self.y_ub_box = tk.Entry(self)
        self.y_ub_box.grid(row=2, column=3, sticky='EW')
        
        self.dy_lim_label = tk.Label(self, text="dy/dx:")
        self.dy_lim_label.grid(row=3, column=0, sticky='E')
        self.dy_lb_box = tk.Entry(self)
        self.dy_lb_box.grid(row=3, column=1, sticky='EW')
        self.dy_to_label = tk.Label(self, text="to")
        self.dy_to_label.grid(row=3, column=2, sticky='EW')
        self.dy_ub_box = tk.Entry(self)
        self.dy_ub_box.grid(row=3, column=3, sticky='EW')
        
        self.aLy_lim_label = tk.Label(self, text="a/Ly:")
        self.aLy_lim_label.grid(row=4, column=0, sticky='E')
        self.aLy_lb_box = tk.Entry(self)
        self.aLy_lb_box.grid(row=4, column=1, sticky='EW')
        self.aLy_to_label = tk.Label(self, text="to")
        self.aLy_to_label.grid(row=4, column=2, sticky='EW')
        self.aLy_ub_box = tk.Entry(self)
        self.aLy_ub_box.grid(row=4, column=3, sticky='EW')
        
        self.update_button = tk.Button(self, text='apply', command=self.update_limits)
        self.update_button.grid(row=5, column=0, columnspan=4, sticky='W')
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(3, weight=1)
    
    def update_limits(self):
        """Apply the plot limits selected.
        """
        try:
            x_lb = float(self.x_lb_box.get())
        except ValueError:
            pass
        else:
            self.master.master.plot_frame.a_val.set_xlim(left=x_lb)
        try:
            x_ub = float(self.x_ub_box.get())
        except ValueError:
            pass
        else:
            self.master.master.plot_frame.a_val.set_xlim(right=x_ub)
        
        try:
            y_lb = float(self.y_lb_box.get())
        except ValueError:
            pass
        else:
            self.master.master.plot_frame.a_val.set_ylim(bottom=y_lb)
        try:
            y_ub = float(self.y_ub_box.get())
        except ValueError:
            pass
        else:
            self.master.master.plot_frame.a_val.set_ylim(top=y_ub)
        
        try:
            dy_lb = float(self.dy_lb_box.get())
        except ValueError:
            pass
        else:
            self.master.master.plot_frame.a_grad.set_ylim(bottom=dy_lb)
        try:
            dy_ub = float(self.dy_ub_box.get())
        except ValueError:
            pass
        else:
            self.master.master.plot_frame.a_grad.set_ylim(top=dy_ub)
        
        try:
            aLy_lb = float(self.aLy_lb_box.get())
        except ValueError:
            pass
        else:
            self.master.master.plot_frame.a_a_L.set_ylim(bottom=aLy_lb)
        try:
            aLy_ub = float(self.aLy_ub_box.get())
        except ValueError:
            pass
        else:
            self.master.master.plot_frame.a_a_L.set_ylim(top=aLy_ub)
        
        self.master.master.plot_frame.canvas.draw()

class ControlFrame(tk.Frame):
    """Frame to hold all of the controls.
    """
    def __init__(self, *args, **kwargs):
        # Need to use old, hackish way since tkinter uses old-style classes:
        tk.Frame.__init__(self, *args, **kwargs)
        
        # Use Notebook to get tabs.
        self.note = tkinter.ttk.Notebook(self)
        # self.note.enable_traversal()
        
        self.data_time_frame = tk.Frame(self)
        self.fit_eval_frame = tk.Frame(self)
        
        self.data_source_frame = DataSourceFrame(self.data_time_frame, **FRAME_PARAMS)
        self.data_source_frame.grid(row=0, sticky='EW')
        
        self.averaging_frame = AveragingFrame(self.data_time_frame, **FRAME_PARAMS)
        self.averaging_frame.grid(row=1, sticky='NSEW')
        
        self.data_time_frame.grid_columnconfigure(0, weight=1)
        self.data_time_frame.grid_rowconfigure(1, weight=1)
        
        self.kernel_frame = KernelFrame(self, **FRAME_PARAMS)
        
        self.fitting_frame = FittingFrame(self.fit_eval_frame, **FRAME_PARAMS)
        self.fitting_frame.grid(row=0, sticky='EW')
        
        self.eval_frame = EvaluationFrame(self.fit_eval_frame, **FRAME_PARAMS)
        self.eval_frame.grid(row=1, sticky='EW')
        
        self.outlier_frame = OutlierFrame(self.fit_eval_frame, **FRAME_PARAMS)
        self.outlier_frame.grid(row=2, sticky='NSEW')
        
        self.fit_eval_frame.grid_columnconfigure(0, weight=1)
        self.fit_eval_frame.grid_rowconfigure(2, weight=1)
        
        self.plot_param_frame = PlotParamFrame(self, **FRAME_PARAMS)
        
        self.note.add(
            self.data_time_frame,
            text="Data",
            # underline=0
        )
        self.note.add(
            self.kernel_frame,
            text="Kernel",
            # underline=0
        )
        self.note.add(
            self.fit_eval_frame,
            text="Fit",
            # underline=0
        )
        self.note.add(
            self.plot_param_frame,
            text="Plot",
            # underline=0
        )
        
        self.note.grid(row=0, sticky='EWNS')
        
        self.status_frame = StatusBox(self, **FRAME_PARAMS)
        self.status_frame.grid(row=1, sticky='EWNS')
        
        self.control_frame = ControlBox(self)
        self.control_frame.grid(row=2, sticky='EW')
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

class FitWindow(tk.Tk):
    """Base window class to hold plot and controls.
    """
    def __init__(self, *args, **kwargs):
        # Need to use old, hackish way since tkinter uses old-style classes:
        tk.Tk.__init__(self, *args, **kwargs)
        
        self.wm_title("%s %s" % (PROG_NAME, __version__,))
        
        self.control_frame = ControlFrame(self)
        self.control_frame.grid(row=0, column=1, sticky='NESW')
        
        self.plot_frame = PlotFrame(self)
        self.plot_frame.grid(row=0, column=0, sticky='NESW')
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.master_p = None
        self.p = None
        self.combined_p = None
        
        # l, e store the plotted lines, envelopes so they can be removed as
        # needed.
        self.l = []
        self.e = []
        
        self.X = None
        self.res = None
        
        self.flagged_plt = None
        
        self.bind("<%s-d>" % (COMMAND_KEY,), self.set_tab)
        self.bind("<%s-k>" % (COMMAND_KEY,), self.set_tab)
        self.bind("<%s-f>" % (COMMAND_KEY,), self.set_tab)
        self.bind("<%s-p>" % (COMMAND_KEY,), self.set_tab)
        self.bind("<F1>", self.set_tab)
        self.bind("<F2>", self.set_tab)
        self.bind("<F3>", self.set_tab)
        self.bind("<F4>", self.set_tab)
    
    def set_tab(self, event):
        """Set the tab as indicated by the keysym in the event.
        """
        if event.keysym.lower() in ('d', 'f1'):
            self.control_frame.note.select(0)
        elif event.keysym.lower() in ('k', 'f2'):
            self.control_frame.note.select(1)
        elif event.keysym.lower() in ('f', 'f3'):
            self.control_frame.note.select(2)
        elif event.keysym.lower() in ('p', 'f4'):
            self.control_frame.note.select(3)
    
    def load_data(self):
        """Load the data from the relevant source.
        """
        self.efit_tree = None
        
        if (self.control_frame.data_source_frame.tree_file_frame.source_state.get() ==
                self.control_frame.data_source_frame.tree_file_frame.TREE_MODE):
            # Fetch data from the tree:
            signal = self.control_frame.data_source_frame.signal_coordinate_frame.signal_var.get()
            
            # Put empty lists in each field so that the order/position is
            # preserved.
            self.master_p = collections.OrderedDict(
                list(zip(SYSTEM_OPTIONS[signal], [[]] * len(SYSTEM_OPTIONS[signal])))
            )
            try:
                shot = int(self.control_frame.data_source_frame.shot_frame.shot_box.get())
                self.control_frame.status_frame.add_line(
                    "Loading data from shot number %d..." % (shot,)
                )
                # Load the EFIT tree:
                EFIT_tree_name = self.control_frame.data_source_frame.EFIT_frame.EFIT_field.get()
                if EFIT_tree_name == '':
                    EFIT_tree_name = 'ANALYSIS'
                try:
                    self.efit_tree = eqtools.CModEFITTree(
                        shot,
                        tree=EFIT_tree_name
                    )
                except MDSplus.TreeException as e:
                    self.control_frame.status_frame.add_line(
                        "Could not load EFIT data from tree %s! Loading of data "
                        "from tree failed." % (EFIT_tree_name,)
                    )
                    if args.no_interaction:
                        raise e
                    return
            except ValueError:
                self.control_frame.status_frame.add_line(
                    "Invalid shot number! Loading of data from tree failed."
                )
                return
            # Make list of systems to include:
            include = [
                b.system for b in self.control_frame.data_source_frame.system_frame.buttons
                if b.state_var.get()
            ]
            for system in include:
                self.control_frame.status_frame.add_line(
                    "Loading data from %s..." % (system,)
                )
                try:
                    if signal == 'ne':
                        self.master_p[system] = profiletools.ne(
                            shot,
                            include=[system],
                            efit_tree=self.efit_tree
                        )
                    elif signal == 'Te':
                        # Don't remove the ECE edge here, since it still has ALL
                        # the points left in.
                        self.master_p[system] = profiletools.Te(
                            shot,
                            include=[system],
                            remove_ECE_edge=False,
                            efit_tree=self.efit_tree
                        )
                    elif signal == 'emiss':
                        self.master_p[system] = profiletools.emiss(
                            shot,
                            include=[system],
                            efit_tree=self.efit_tree
                        )
                    else:
                        self.control_frame.status_frame.add_line(
                            "Unsupported signal %s!" % (signal,)
                        )
                        return
                except MDSplus.TreeException as e:
                    self.control_frame.status_frame.add_line(
                        "Could not fetch data from the tree for system %s. "
                        "Exception was: %s" % (system, e,)
                    )
        else:
            # Load data from file:
            self.master_p = collections.OrderedDict()
            path = self.control_frame.data_source_frame.tree_file_frame.path_entry.get()
            root, ext = os.path.splitext(path)
            path = os.path.abspath(os.path.expanduser(path))
            base = os.path.basename(path)
            if not os.path.isfile(path):
                self.control_frame.status_frame.add_line(
                    "File %s does not exist or is not a file! Loading of data "
                    "from file failed." % (path,)
                )
                return
            time_name = self.control_frame.data_source_frame.variable_name_frame.time_box.get()
            space_name = self.control_frame.data_source_frame.variable_name_frame.space_box.get()
            data_name = self.control_frame.data_source_frame.variable_name_frame.data_box.get()
            if space_name:
                if time_name:
                    X_names = [time_name, space_name]
                else:
                    X_names = [space_name]
            else:
                X_names = None
            if not data_name:
                data_name = None
            if ext.lower() == '.csv':
                metadata_lines = self.control_frame.data_source_frame.variable_name_frame.meta_box.get()
                try:
                    metadata_lines = int(metadata_lines)
                except ValueError:
                    if metadata_lines == '':
                        metadata_lines = None
                    else:
                        self.control_frame.status_frame.add_line(
                            "Invalid number of metadata lines! Loading of data from "
                            "file failed."
                        )
                        return
                self.control_frame.status_frame.add_line("Loading data from CSV file %s..." % (path,))
                self.master_p[base] = profiletools.read_plasma_csv(
                    path,
                    X_names=X_names,
                    y_name=data_name,
                    metadata_lines=metadata_lines
                )
            else:
                if X_names is None or data_name is None:
                    self.control_frame.status_frame.add_line(
                        "Must specify variable names when reading from a NetCDF "
                        "file! Loading of data from file failed."
                    )
                    return
                self.control_frame.status_frame.add_line(
                    "Loading data from NetCDF file %s..." % (path,)
                )
                self.master_p[base] = profiletools.read_plasma_NetCDF(
                    path,
                    X_names,
                    data_name
                )
            if hasattr(self.master_p[base], 'shot'):
                self.control_frame.data_source_frame.shot_frame.shot_box.delete(0, tk.END)
                self.control_frame.data_source_frame.shot_frame.shot_box.insert(
                    0, str(self.master_p[base].shot)
                )
                self.efit_tree = self.master_p[base].efit_tree
            if hasattr(self.master_p[base], 't_min'):
                self.control_frame.averaging_frame.time_window_frame.window_button.invoke()
                self.control_frame.averaging_frame.time_window_frame.t_min_box.delete(0, tk.END)
                self.control_frame.averaging_frame.time_window_frame.t_min_box.insert(
                    0, str(self.master_p[base].t_min)
                )
            if hasattr(self.master_p[base], 't_max'):
                self.control_frame.averaging_frame.time_window_frame.window_button.invoke()
                self.control_frame.averaging_frame.time_window_frame.t_max_box.delete(0, tk.END)
                self.control_frame.averaging_frame.time_window_frame.t_max_box.insert(
                    0, str(self.master_p[base].t_max)
                )
            if hasattr(self.master_p[base], 'times'):
                self.control_frame.averaging_frame.time_window_frame.point_button.invoke()
                self.control_frame.averaging_frame.time_window_frame.times_box.delete(0, tk.END)
                self.control_frame.averaging_frame.time_window_frame.times_box.insert(
                    0, str(self.master_p[base].times)[1:-1]
                )
            # Set the coordinate selector
            self.control_frame.data_source_frame.signal_coordinate_frame.coordinate_var.set(
                self.master_p[base].abscissa
            )
            
        self.control_frame.status_frame.add_line("Loading of data complete.")
    
    def average_data(self):
        """Average and plot the data.
        """
        # Set of markers to cycle through for the datapoints:
        # Make it new every time so the results are predictable upon reloading.
        markercycle = itertools.cycle('o^sDH*')
        
        self.control_frame.status_frame.add_line("Averaging and plotting data...")
        if not self.master_p:
            self.load_data()
        
        # Clear the plots completely:
        self.plot_frame.a_val.clear()
        self.plot_frame.a_grad.clear()
        self.plot_frame.a_a_L.clear()
        
        method = self.control_frame.averaging_frame.method_frame.method_var.get()
        weighted = self.control_frame.averaging_frame.method_frame.weighted_state.get()
        y_method = self.control_frame.averaging_frame.method_frame.error_method_var.get()
        abscissa = self.control_frame.data_source_frame.signal_coordinate_frame.coordinate_var.get()
        window_mode = (self.control_frame.averaging_frame.time_window_frame.method_state.get() ==
                       self.control_frame.averaging_frame.time_window_frame.WINDOW_MODE)
        core_only = self.control_frame.kernel_frame.kernel_type_frame.core_only_state.get()
        
        times = []
        
        if window_mode:
            try:
                t_min = float(self.control_frame.averaging_frame.time_window_frame.t_min_box.get())
            except ValueError:
                t_min = None
                self.control_frame.status_frame.add_line(
                    "Invalid value for t_min. No lower bound applied."
                )
            try:
                t_max = float(self.control_frame.averaging_frame.time_window_frame.t_max_box.get())
            except ValueError:
                t_max = None
                self.control_frame.status_frame.add_line(
                    "Invalid value for t_max. No upper bound applied."
                )
        else:
            s_times = re.findall(
                LIST_REGEX,
                self.control_frame.averaging_frame.time_window_frame.times_box.get()
            )
            for t in s_times:
                try:
                    times.append(float(t))
                except ValueError:
                    self.control_frame.status_frame.add_line(
                        "Invalid value %s in time points, will be ignored." % (t,)
                    )
            if not times:
                self.control_frame.status_frame.add_line(
                    "No valid points in time points. No bounding applied."
                )
        
        # Keep a deepcopy so we don't mutate the master data that have been
        # pulled from the tree.
        self.p = copy.deepcopy(self.master_p)
        
        for k, p in self.p.items():
            # Data that haven't been loaded are stored as an empty list.
            if p != []:
                self.control_frame.status_frame.add_line(
                    "Processing data from %s..." % (k,)
                )
                # Restore the master tree so they can all share data:
                p.efit_tree = self.efit_tree
                # Restrict data to desired time points:
                if p.X_dim > 1:
                    if window_mode:
                        if t_min is not None:
                            if p.X is not None:
                                p.remove_points(p.X[:, 0] < t_min)
                            for pt in p.transformed:
                                good_idxs = (pt.X[:, :, 0] >= t_min).all(axis=1)
                                pt.X = pt.X[good_idxs]
                                pt.err_X = pt.err_X[good_idxs]
                                pt.y = pt.y[good_idxs]
                                pt.err_y = pt.err_y[good_idxs]
                                pt.T = pt.T[good_idxs]
                        if t_max is not None:
                            if p.X is not None:
                                p.remove_points(p.X[:, 0] > t_max)
                            for pt in p.transformed:
                                good_idxs = (pt.X[:, :, 0] <= t_max).all(axis=1)
                                pt.X = pt.X[good_idxs]
                                pt.err_X = pt.err_X[good_idxs]
                                pt.y = pt.y[good_idxs]
                                pt.err_y = pt.err_y[good_idxs]
                                pt.T = pt.T[good_idxs]
                    else:
                        if times:
                            p.keep_times(times)
                # Convert abscissa if needed:
                try:
                    p.convert_abscissa(abscissa)
                except Exception as e:
                    self.control_frame.status_frame.add_line(
                        "Conversion to coordinate %s from %s failed for system %s."
                        % (abscissa, p.abscissa, k)
                    )
                    print(e)
                if len(times) == 1 or method == "all points":
                    p.drop_axis(0)
                else:
                    p.time_average(
                        robust=(method == "robust"),
                        y_method=y_method,
                        weighted=weighted
                    )
                # Remove the edge ECE points here, after the conversion is
                # complete:
                if 'GPC' in k or 'ECE' in k or core_only:
                    p.remove_edge_points()
                
                # Plot the data channel-by-channel so it gets color-coded right:
                p.plot_data(ax=self.plot_frame.a_val, fmt=next(markercycle))
        
        # Now that the profiles are loaded, stitch them together:
        self.control_frame.status_frame.add_line("Combining profiles...")
        
        p_list = []
        # Get list of profiles to actually include -- this lets the user elect
        # to drop a profile from the fit even if they loaded it.
        p_include = [
            b.state_var.get()
            for b in self.control_frame.data_source_frame.system_frame.buttons
        ]
        for p, i in zip(list(self.p.values()), p_include):
            if i:
                p_list.append(p)
        if len(p_list) == 0:
            self.control_frame.status_frame.add_line("No profiles to combine!")
        else:
            self.combined_p = copy.deepcopy(p_list.pop(0))
            for p_other in p_list:
                self.combined_p.add_profile(p_other)
            
            # Remove extreme change points, keeping track of the bad indices.
            if self.control_frame.outlier_frame.extreme_state.get():
                self.control_frame.status_frame.add_line(
                    "Removing points that exhibit extreme changes..."
                )
                try:
                    self.extreme_flagged = self.combined_p.remove_extreme_changes(
                        thresh=float(self.control_frame.outlier_frame.extreme_thresh_box.get()),
                        mask_only=True
                    )
                    y_bad_c = self.combined_p.y[self.extreme_flagged]
                    X_bad_c = self.combined_p.X[self.extreme_flagged, :].ravel()
                    self.control_frame.status_frame.add_line(
                        "Removed %d points with extreme changes." % (len(y_bad_c),)
                    )
                    if len(y_bad_c) > 0:
                        self.plot_frame.a_val.plot(
                            X_bad_c, y_bad_c, 'mx', label='extreme change', ms=14
                        )
                except ValueError:
                    self.control_frame.status_frame.add_line(
                        "Invalid threshold for extreme change rejection!"
                    )
                    self.extreme_flagged = scipy.zeros_like(self.combined_p.y, dtype=bool)
            else:
                self.extreme_flagged = scipy.zeros_like(self.combined_p.y, dtype=bool)
            
            self.plot_frame.a_val.set_ylabel(
                "%s [%s]" % (self.combined_p.y_label, self.combined_p.y_units,)
                if self.combined_p.y_units
                else self.combined_p.y_label
            )
            
            # self.control_frame.plot_param_frame.update_limits()
            
            # Only update the value axis:
            try:
                x_min = float(self.control_frame.plot_param_frame.x_lb_box.get())
            except ValueError:
                x_min = self.combined_p.X.min()
            try:
                x_max = float(self.control_frame.plot_param_frame.x_ub_box.get())
            except ValueError:
                x_max = self.combined_p.X.max()
            self.plot_frame.a_val.set_xlim(left=x_min, right=x_max)
            try:
                y_min = float(self.control_frame.plot_param_frame.y_lb_box.get())
            except ValueError:
                y_min = 0
            try:
                y_max = float(self.control_frame.plot_param_frame.y_ub_box.get())
            except ValueError:
                y_max = None
            self.plot_frame.a_val.set_ylim(bottom=y_min, top=y_max)
        
        self.plot_frame.a_val.legend(loc='best', fontsize=12, ncol=2)
        
        # Produce a descriptive title for the plot:
        title = ''
        try:
            title += "shot %d" % (self.combined_p.shot)
        except AttributeError:
            pass
        try:
            title += " t_min %f" % (self.combined_p.t_min)
        except AttributeError:
            pass
        try:
            title += " t_max %f" % (self.combined_p.t_max)
        except AttributeError:
            pass
        if hasattr(self.combined_p, 'times'):
            times = list(self.combined_p.times)
            title += " times %f" % (times.pop())
            for t in times:
                title += ",%f" % (t,)
        
        self.plot_frame.suptitle.set_text(title)
        
        self.control_frame.outlier_frame.update_show_idx()
        # update_show_idx always calls draw, so we don't need to here.
        # self.plot_frame.canvas.draw()
        self.plot_frame.canvas._tkcanvas.focus_set()
        
        self.outlier_flagged = scipy.zeros_like(self.combined_p.y, dtype=bool)
        
        self.control_frame.status_frame.add_line(
            "Averaging and plotting of data complete."
        )
    
    def process_bounds(self):
        """Process the hyperparameter bounds.
        
        If a field is blank, take the bound from the GP's hyperprior. If a field
        is populated, put that into the GP's hyperprior.
        """
        for k, l, u in zip(list(range(0, len(self.combined_p.gp.free_param_bounds))),
                           self.control_frame.kernel_frame.bounds_frame.lower_bounds,
                           self.control_frame.kernel_frame.bounds_frame.upper_bounds):
            old_bounds = self.combined_p.gp.free_param_bounds[k]
            new_bounds = list(old_bounds)
            
            new_lb = l.get()
            try:
                new_bounds[0] = float(new_lb)
            except ValueError:
                if new_lb == '':
                    l.insert(0, str(old_bounds[0]))
                else:
                    self.control_frame.status_frame.add_line(
                        "Invalid lower bound %s for %s, will use default value "
                        "instead." % (new_lb, k,)
                    )
                
            new_ub = u.get()
            try:
                new_bounds[1] = float(new_ub)
            except ValueError:
                if new_ub == '':
                    u.insert(0, str(old_bounds[1]))
                else:
                    self.control_frame.status_frame.add_line(
                        "Invalid upper bound %s for %s, will use default value "
                        "instead." % (new_ub, k,)
                    )
            
            self.combined_p.gp.free_param_bounds[k] = new_bounds
    
    def fit_data(self):
        """Perform the actual fit and evaluation.
        """
        if not self.combined_p:
            self.average_data()
        
        # Form X grid to evaluate on:
        if (self.control_frame.eval_frame.method_state.get() ==
                self.control_frame.eval_frame.UNIFORM_GRID):
            try:
                X_min = float(self.control_frame.eval_frame.x_min_box.get())
            except ValueError:
                self.control_frame.status_frame.add_line(
                    "Invalid lower bound for uniform grid!"
                )
                return
            try:
                X_max = float(self.control_frame.eval_frame.x_max_box.get())
            except ValueError:
                self.control_frame.status_frame.add_line(
                    "Invalid upper bound for uniform grid!"
                )
                return
            try:
                npts = int(self.control_frame.eval_frame.npts_box.get())
            except ValueError:
                self.control_frame.status_frame.add_line(
                    "Invalid number of points for uniform grid!"
                )
                return
            X = scipy.linspace(X_min, X_max, npts)
        else:
            X = []
            s_points = re.findall(
                LIST_REGEX,
                self.control_frame.eval_frame.x_points_box.get()
            )
            for p in s_points:
                try:
                    X.append(float(p))
                except ValueError:
                    self.control_frame.status_frame.add_line(
                        "Invalid value %s in evaluation points, will be ignored." % (p,)
                    )
            if not X:
                self.control_frame.status_frame.add_line(
                    "No valid points in evaluation points!"
                )
                return
        
        self.control_frame.status_frame.add_line("Creating Gaussian process...")
        self.create_gp()
        self.control_frame.status_frame.add_line("Gaussian process created.")
        
        # Process outliers:
        remove_outliers = self.control_frame.outlier_frame.outlier_state.get()
        if remove_outliers:
            self.control_frame.status_frame.add_line("Finding outliers...")
            self.control_frame.status_frame.add_line("Finding initial MAP estimate...")
            self.find_MAP()
            thresh = float(self.control_frame.outlier_frame.outlier_thresh_box.get())
            self.outlier_flagged, bad_transformed = self.combined_p.remove_outliers(
                    thresh=thresh,
                    check_transformed=True,
                    mask_only=True
                )
            X_bad_o = self.combined_p.X[self.outlier_flagged, :].ravel()
            err_X_bad_o = self.combined_p.err_X[self.outlier_flagged, :].ravel()
            y_bad_o = self.combined_p.y[self.outlier_flagged]
            err_y_bad_o = self.combined_p.err_y[self.outlier_flagged]
            
            self.control_frame.status_frame.add_line(
                "Found %d candidate outliers." % (len(y_bad_o),)
            )
            truly_bad_transformed = [pt for pt in bad_transformed if len(pt.y) > 0]
            if len(truly_bad_transformed) > 0:
                self.control_frame.status_frame.add_line(
                    "Removed the following %d transformed quantities:" % (len(truly_bad_transformed),)
                )
                for pt in truly_bad_transformed:
                    self.control_frame.status_frame.add_line(pt.y_label)
                # TODO: Put a test to put transformed quantities back in!
            
            # Perform a second MAP estimation to put back IN the outliers that
            # now don't look so outlying:
            if len(y_bad_o) > 1:
                self.control_frame.status_frame.add_line(
                    "Finding second MAP estimate..."
                )
                
                self.create_gp()
                self.find_MAP()
                
                idxs = scipy.where(self.outlier_flagged)[0]
                
                # Handle single points:
                mean = self.combined_p.gp.predict(
                    X_bad_o,
                    n=0,
                    noise=False,
                    return_std=False
                )
                deltas = scipy.absolute(mean - y_bad_o) / err_y_bad_o
                deltas[err_y_bad_o == 0] = 0
                bad_idxs = (deltas >= thresh)
                good_idxs = ~bad_idxs
                
                self.outlier_flagged[idxs[good_idxs]] = False
                
                self.create_gp()
                
                self.control_frame.status_frame.add_line(
                    "Removed %d outliers."
                    % (len(y_bad_o[bad_idxs]),)
                )
            elif len(y_bad_o) == 1:
                bad_idxs = scipy.ones_like(y_bad_o, dtype=bool)
                self.control_frame.status_frame.add_line("Removed 1 outlier.")
            else:
                bad_idxs = scipy.zeros_like(y_bad_o, dtype=bool)
            # Plot the points that were removed:
            if len(y_bad_o[bad_idxs]) > 0:
                self.plot_frame.a_val.plot(
                    X_bad_o[bad_idxs],
                    y_bad_o[bad_idxs],
                    'rx',
                    label='outlier', ms=14
                )
        
        # Do the voodoo:
        use_MCMC = (
            self.control_frame.fitting_frame.method_frame.method_state.get() ==
            self.control_frame.fitting_frame.method_frame.USE_MCMC
        )
        # Only redo the MAP estimate if there were points removed:
        if not use_MCMC and (not remove_outliers or not bad_idxs.all()):
            self.control_frame.status_frame.add_line("Finding MAP estimate...")
            self.find_MAP()
        
        # Evaluate:
        self.control_frame.status_frame.add_line("Evaluating fit...")
        
        full_MC = self.control_frame.fitting_frame.MCMC_constraint_frame.full_MC_state.get()
        compute_a_L = self.control_frame.eval_frame.a_L_state.get()
        if full_MC:
            positivity_constraint = self.control_frame.fitting_frame.MCMC_constraint_frame.pos_state.get()
            monotonicity_constraint = (
                compute_a_L and
                self.control_frame.fitting_frame.MCMC_constraint_frame.mono_state.get()
            )
            
            rejection_func = profiletools.RejectionFunc(
                X <= self.combined_p.X.max(),
                positivity=positivity_constraint,
                monotonicity=monotonicity_constraint
            )
            try:
                if not use_MCMC:
                    num_samples = int(
                        self.control_frame.fitting_frame.MCMC_constraint_frame.samples_box.get()
                    )
                else:
                    num_samples = 1
            except ValueError:
                self.control_frame.status_frame.add_line(
                    "Invalid number of Monte Carlo samples! Disabling use of "
                    "full Monte Carlo."
                )
                full_MC = False
                num_samples = 1
        else:
            num_samples = 1
            rejection_func = None
        
        self.sampler = None
        
        if use_MCMC:
            self.control_frame.status_frame.add_line(
                "Running MCMC sampler..."
            )
            self.run_MCMC_sampler()
            
            MCMC_results_window = MCMCWindow(self)
            MCMC_results_window.grab_set()
            self.wait_window(MCMC_results_window)
            if self.sampler:
                try:
                    self.sampler.pool.close()
                except AttributeError:
                    pass
                try:
                    burn = int(self.control_frame.fitting_frame.MCMC_frame.burn_box.get())
                except ValueError:
                    self.control_frame.status_frame.add_line(
                        "Invalid value for burn! Evaluation failed."
                    )
                    return
                if burn >= self.sampler.chain.shape[1]:
                    burn = 0
                    self.control_frame.status_frame.add_line(
                        "Not enough points, setting burn to 0!"
                    )
                try:
                    thin = max(
                        self.sampler.chain.shape[0] * 
                            (self.sampler.chain.shape[1] - burn) //
                            int(self.control_frame.fitting_frame.MCMC_frame.keep_box.get()),
                        1
                    )
                    print("thin=%d" % (thin,))
                except ValueError:
                    self.control_frame.status_frame.add_line(
                        "Invalid value for keep! Evaluation failed."
                    )
                    return
                self.control_frame.status_frame.add_line(
                    "MCMC sampling complete.\nComputing profile from samples..."
                )
            else:
                self.control_frame.status_frame.add_line(
                    "MCMC evaluation aborted."
                )
                return
        else:
            burn = None
            thin = None
        try:
            compute_vol_avg = self.control_frame.eval_frame.vol_avg_state.get()
            compute_peaking = self.control_frame.eval_frame.peaking_state.get()
            if compute_vol_avg or compute_peaking:
                dum, weights = self.combined_p._make_volume_averaging_matrix(rho_grid=X)
                if compute_a_L:
                    weights = scipy.hstack((weights, scipy.zeros_like(weights)))
                    output_transform = scipy.vstack((weights, scipy.eye(2 * len(X))))
                else:
                    output_transform = scipy.vstack((weights, scipy.eye(len(X))))
                # This will put the volume average as the first element.
                if compute_peaking:
                    if 'psinorm' in self.combined_p.abscissa:
                        if self.combined_p.abscissa.startswith('sqrt'):
                            core_loc = scipy.sqrt(0.2)
                        else:
                            core_loc = 0.2
                    else:
                        times = self.combined_p._get_efit_times_to_average()
                        
                        core_loc = self.combined_p.efit_tree.psinorm2rho(
                            self.combined_p.abscissa,
                            0.2,
                            times,
                            each_t=True
                        )
                        core_loc = scipy.stats.nanmean(core_loc.ravel())
                    X = scipy.insert(X, 0, core_loc)
                    output_transform = scipy.insert(output_transform, 0, 0, axis=1)
                    core_select = scipy.zeros(output_transform.shape[1])
                    core_select[0] = 1
                    output_transform = scipy.insert(output_transform, 1, core_select, axis=0)
                    # This will put w(psinorm=0.2) as the second element and the
                    # volume average as the first element.
            else:
                output_transform = None
            
            if compute_peaking:
                special_vals = 2
            elif compute_vol_avg:
                special_vals = 1
            else:
                special_vals = 0
            
            if compute_a_L:
                res = self.combined_p.compute_a_over_L(
                    X,
                    use_MCMC=use_MCMC,
                    sampler=self.sampler,
                    return_prediction=True,
                    full_MC=full_MC,
                    rejection_func=rejection_func,
                    num_samples=num_samples,
                    burn=burn,
                    thin=thin,
                    output_transform=output_transform,
                    special_vals=special_vals,
                    special_X_vals=int(compute_peaking)
                )
                # Print summary of fit:
                self.control_frame.status_frame.add_line(
                    "Median relative uncertainty in value: %.2f%%\n"
                    "Median relative uncertainty in gradient: %.2f%%\n"
                    "Median relative uncertainty in a/L: %.2f%%" %
                    (
                        100 * scipy.median(scipy.absolute(res['std_val'] / res['mean_val'])),
                        100 * scipy.median(scipy.absolute(res['std_grad'] / res['mean_grad'])),
                        100 * scipy.median(scipy.absolute(res['std_a_L'] / res['mean_a_L']))
                    )
                )
            else:
                res = self.combined_p.smooth(
                    X,
                    n=0,
                    use_MCMC=use_MCMC,
                    sampler=self.sampler,
                    full_output=True,
                    full_MC=full_MC,
                    rejection_func=rejection_func,
                    num_samples=num_samples,
                    burn=burn,
                    thin=thin,
                    output_transform=output_transform
                )
                # Repackage the results to match the form returned by MCMC:
                res['special_mean'] = res['mean'][:special_vals]
                res['special_cov'] = res['cov'][:special_vals, :special_vals]
                res['mean_val'] = res.pop('mean')[special_vals:]
                res['std_val'] = res.pop('std')[special_vals:]
                
                # Print summary of fit:
                self.control_frame.status_frame.add_line(
                    "Median relative uncertainty in value: %.2f%%" %
                    (100 * scipy.median(scipy.absolute(res['std_val'] / res['mean_val'])),)
                )
            
            if (self.control_frame.data_source_frame.signal_coordinate_frame.signal_var.get() == 'ne' and
                    self.control_frame.eval_frame.TCI_state.get()):
                # TODO: Make this load TCI chords if not present!
                # TODO: This breaks with full Monte Carlo!
                if 'TCI' not in self.p:
                    self.control_frame.status_frame.add_line(
                        "Must have loaded TCI first! TCI integrals will not be computed."
                    )
                else:
                    p_TCI = self.p['TCI']
                    self.control_frame.status_frame.add_line(
                        "Computing TCI line integrals..."
                    )
                    for pt in p_TCI.transformed:
                        self.control_frame.status_frame.add_line(pt.y_label)
                        res_nl = self.combined_p.smooth(
                            scipy.vstack(pt.X),
                            use_MCMC=use_MCMC,
                            sampler=self.sampler,
                            full_output=True,
                            full_MC=full_MC,
                            rejection_func=rejection_func,
                            num_samples=num_samples,
                            burn=burn,
                            thin=thin,
                            output_transform=scipy.linalg.block_diag(*pt.T)
                        )
                        if pt.y_units:
                            y_units = pt.y_units.translate(None, '\\${}')
                            self.control_frame.status_frame.add_line(
                                u"  measured: (%6.4g\u00B1%6.4g) %s\n"
                                u"  fit:      (%6.4g\u00B1%6.4g) %s"
                                % (pt.y[0], pt.err_y[0], y_units,
                                   res_nl['mean'][0], res_nl['std'][0], y_units)
                            )
                        else:
                            self.control_frame.status_frame.add_line(
                                u"  measured: %6.4g\u00B1%6.4g\n"
                                u"  fit:      %6.4g\u00B1%6.4g"
                                % (pt.y[0], pt.err_y[0],
                                   res_nl['mean'][0], res_nl['std'][0])
                            )
        
        except numpy.linalg.LinAlgError as e:
            self.control_frame.status_frame.add_line(
                "Evaluation failed! Try re-running and/or adjusting bounds/number "
                "of samples. Exception was: %s" % (e,)
            )
            if args.no_interaction:
                raise e
            return
        
        # Compute volume average, peaking if requested:
        self.mean_peaking = None
        self.std_peaking = None
        self.mean_vol_avg = None
        self.std_vol_avg = None
        
        if compute_vol_avg or compute_peaking:
            self.mean_vol_avg = res['special_mean'][0]
            self.std_vol_avg = scipy.sqrt(res['special_cov'][0, 0])
            if compute_vol_avg:
                if self.combined_p.y_units:
                    self.control_frame.status_frame.add_line(
                        u"Volume average is (%g\u00b1%g) %s"
                        % (self.mean_vol_avg, self.std_vol_avg,
                           self.combined_p.y_units.translate(None, '\\${}'),)
                    )
                else:
                    self.control_frame.status_frame.add_line(
                        u"Volume average is %g\u00b1%g"
                        % (self.mean_vol_avg, self.std_vol_avg,)
                    )
            if compute_peaking:
                mean_w2 = res['special_mean'][1]
                std_w2 = scipy.sqrt(res['special_cov'][1, 1])
                cov_w2_vol_avg = res['special_cov'][0, 1]
                self.mean_peaking = mean_w2 / self.mean_vol_avg
                self.std_peaking = scipy.sqrt(
                    std_w2 / self.mean_vol_avg**2 +
                    self.std_vol_avg * mean_w2**2 / self.mean_vol_avg**4 -
                    cov_w2_vol_avg * mean_w2 / self.mean_vol_avg**3
                )
                self.control_frame.status_frame.add_line(
                    u"Peaking is %g\u00b1%g"
                    % (self.mean_peaking, self.std_peaking,)
                )
                # Delete the extra points so they don't confuse the plot/file output:
                X = X[1:]
        
        if full_MC:
            self.control_frame.status_frame.add_line(
                "Got %d samples that met the constraints."
                % (res['samp'].shape[1],)
            )
        
        self.res = res
        self.X = X
        
        # Delete old lines, envelopes:
        for line in self.l:
            try:
                line.remove()
            except ValueError:
                pass
        for env in self.e:
            try:
                env.remove()
            except ValueError:
                pass
        
        # Plot the fits:
        self.l, self.e = gptools.univariate_envelope_plot(
            X,
            res['mean_val'],
            res['std_val'],
            ax=self.plot_frame.a_val,
            color='b'
        )
        
        if self.control_frame.eval_frame.a_L_state.get():
            color = plt.getp(self.l[0], 'color')
            core_mask = X <= 1
            l, e = gptools.univariate_envelope_plot(
                X,
                res['mean_grad'],
                res['std_grad'],
                ax=self.plot_frame.a_grad,
                color=color
            )
            self.plot_frame.a_grad.set_ylim(
                bottom=(res['mean_grad'][core_mask] - 3 * res['std_grad'][core_mask]).min(),
                top=(res['mean_grad'][core_mask] + 3 * res['std_grad'][core_mask]).max()
            )
            self.l.extend(l)
            self.e.extend(e)
            
            l, e = gptools.univariate_envelope_plot(
                X,
                res['mean_a_L'],
                res['std_a_L'],
                ax=self.plot_frame.a_a_L,
                color=color
            )
            
            # Avoid bug in MPL v. 1.4.2:
            if matplotlib.__version__ != '1.4.2':
                self.plot_frame.a_a_L.set_ylim(
                    bottom=(res['mean_a_L'][core_mask] - 3 * res['std_a_L'][core_mask]).min(),
                    top=(res['mean_a_L'][core_mask] + 3 * res['std_a_L'][core_mask]).max()
                )
            self.l.extend(l)
            self.e.extend(e)
        
        self.plot_frame.a_grad.set_xlabel(self.plot_frame.a_val.get_xlabel())
        self.plot_frame.a_a_L.set_xlabel(self.plot_frame.a_val.get_xlabel())
        
        y_units = self.combined_p.y_units
        if not y_units:
            y_units = '1'
        X_units = self.combined_p.X_units[0]
        if X_units:
            X_units = '/' + X_units
        combined_units = y_units + X_units
        if combined_units != '1':
            label = "$d%s/d%s$ [%s]" % (
                self.combined_p.y_label.strip('$'),
                self.combined_p.X_labels[0].strip('$'),
                combined_units
            )
        else:
            label = "$d%s/d%s$" % (
                self.combined_p.y_label.strip('$'),
                self.combined_p.X_labels[0]
            )
        self.plot_frame.a_grad.set_ylabel(label)
        
        self.plot_frame.a_a_L.set_ylabel(
            "$a/L_{%s}$" % (self.combined_p.y_label.strip('$'),)
        )
        
        self.control_frame.plot_param_frame.update_limits()
        
        self.plot_frame.a_val.legend(loc='best', fontsize=12, ncol=2)
        self.plot_frame.canvas.draw()
        self.plot_frame.canvas._tkcanvas.focus_set()
        self.control_frame.status_frame.add_line("Fitting complete.")
    
    def create_gp(self):
        """Create the Gaussian process from the combined profile.
        """
        # Remove points that were flagged by the user:
        s_flagged_idxs = re.findall(
            LIST_REGEX,
            self.control_frame.outlier_frame.specific_box.get()
        )
        flagged_idxs = set()
        for s in s_flagged_idxs:
            try:
                i = float(s)
                if i >= len(self.combined_p.y):
                    self.control_frame.status_frame.add_line(
                        "Value %d out of range, will be ignored." % (i,)
                    )
                else:
                    flagged_idxs.add(i)
            except ValueError:
                self.control_frame.status_frame.add_line(
                    "Invalid index to remove '%s', will be ignored." % (s,)
                )
        flagged_idxs = list(flagged_idxs)
        if self.flagged_plt is not None:
            for p in self.flagged_plt:
                try:
                    p.remove()
                except ValueError:
                    pass
        if len(flagged_idxs) > 0:
            self.flagged_plt = self.plot_frame.a_val.plot(
                self.combined_p.X[flagged_idxs, :].ravel(),
                self.combined_p.y[flagged_idxs],
                'x',
                color='orange',
                label='flagged',
                ms=14
            )
        mask = scipy.ones_like(self.combined_p.y, dtype=bool)
        mask[flagged_idxs] = False
        # Mask out outliers and extreme changes:
        mask = mask & (~self.extreme_flagged) & (~self.outlier_flagged)
        k = self.control_frame.kernel_frame.kernel_type_frame.k_var.get()
        if k == 'gibbstanh':
            k = 'gibbstanhlegacy'
        self.combined_p.create_gp(
            k=k,
            constrain_slope_on_axis=False,
            constrain_at_limiter=False,
            upper_factor=args.upper_factor,
            lower_factor=args.lower_factor,
            mask=mask
        )
        # Process core constraint:
        if self.control_frame.kernel_frame.constraints_frame.core_state.get():
            s_core_loc = self.control_frame.kernel_frame.constraints_frame.core_loc.get()
            if s_core_loc == '':
                self.combined_p.constrain_slope_on_axis()
            else:
                s_core_loc = re.findall(LIST_REGEX, s_core_loc)
                core_locs = []
                for loc in s_core_loc:
                    try:
                        core_locs.append(float(loc))
                    except ValueError:
                        self.control_frame.status_frame.add_line(
                            "Invalid core constraint location %s in core "
                            "locations, will be ignored." % (loc,)
                        )
                if len(core_locs) == 0:
                    self.control_frame.status_frame.add_line(
                        "No valid core constraint locations, constraint will not "
                        "be applied!"
                    )
                else:
                    self.combined_p.gp.add_data(
                        core_locs,
                        scipy.zeros_like(core_locs),
                        n=1
                    )
        # Process edge constraint:
        if self.control_frame.kernel_frame.constraints_frame.edge_state.get():
            s_edge_locs = self.control_frame.kernel_frame.constraints_frame.edge_loc.get()
            if s_edge_locs == '':
                self.combined_p.constrain_at_limiter()
            else:
                s_edge_locs = re.findall(LIST_REGEX, s_edge_locs)
                edge_locs = []
                for loc in s_edge_locs:
                    try:
                        edge_locs.append(float(loc))
                    except ValueError:
                        self.control_frame.status_frame.add_line(
                            "Invalid edge constraint location %s in edge "
                            "locations, will be ignored." % (loc,)
                        )
                if len(edge_locs) == 0:
                    self.control_frame.status_frame.add_line(
                        "No valid edge constraint locations, constraint will not "
                        "be applied!"
                    )
                else:
                    self.combined_p.gp.add_data(
                        edge_locs,
                        scipy.zeros_like(edge_locs),
                        err_y=0.01,
                        n=0
                    )
                    self.combined_p.gp.add_data(
                        edge_locs,
                        scipy.zeros_like(edge_locs),
                        err_y=0.1,
                        n=1
                    )
        # Process bounds:
        self.process_bounds()
    
    def find_MAP(self):
        """Find the MAP estimate for the hyperparameters.
        """
        try:
            res_min, complete = self.combined_p.find_gp_MAP_estimate(
                random_starts=int(self.control_frame.fitting_frame.method_frame.starts_box.get()),
                verbose=True,
                method='SLSQP'
            )
        except ValueError as e:
            self.control_frame.status_frame.add_line(
                "MAP estimate failed. Hyperparameters should not be trusted! Try "
                "re-running the fit with more random starts. Exception was: '%s'."
                % (e,)
            )
            if args.no_interaction:
                raise e
        else:
            self.control_frame.status_frame.add_line(
                "MAP estimate complete. Result is:"
            )
            for v, l in zip(self.combined_p.gp.free_params, self.combined_p.gp.free_param_names):
                self.control_frame.status_frame.add_line("%s\t%.3e" % (l.translate(None, '\\'), v))
            if complete < 4:
                self.control_frame.status_frame.add_line(
                    "Less than 4 completed starts were obtained. Try increasing "
                    "the number of random starts, or adjusting the hyperparameter "
                    "bounds."
                )
            if not res_min.success:
                self.control_frame.status_frame.add_line(
                    "Optimizer reports failure, selected hyperparameters "
                    "are likely NOT optimal. Status: %d, Message: '%s'. "
                    "Try adjusting bounds, initial guesses or the number "
                    "of random starts used."
                    % (res_min.status, res_min.message)
                )
            bounds = scipy.asarray(self.combined_p.gp.free_param_bounds)
            if ((res_min.x <= 1.001 * bounds[:, 0]).any() or
                (res_min.x >= 0.999 * bounds[:, 1]).any()):
                self.control_frame.status_frame.add_line(
                    "Optimizer appears to have hit/exceeded the bounds. Try "
                    "adjusting bounds, initial guesses or the number of random "
                    "starts used."
                )
    
    def run_MCMC_sampler(self):
        """Run the MCMC sampler, save the resulting sampler object internally.
        """
        try:
            walkers = int(self.control_frame.fitting_frame.MCMC_frame.walker_box.get())
        except ValueError:
            self.control_frame.status_frame.add_line(
                "Invalid number of MCMC walkers! Evaluation failed."
            )
            self.sampler = None
            return
        try:
            samples = int(self.control_frame.fitting_frame.MCMC_frame.sample_box.get())
        except ValueError:
            self.control_frame.status_frame.add_line(
                "Invalid number of MCMC samples! Evaluation failed."
            )
            self.sampler = None
            return
        self.sampler = self.combined_p.gp.sample_hyperparameter_posterior(
            nsamp=samples,
            nwalkers=walkers,
            sampler=self.sampler
        )
    
    def save_fit(self, save_plot=False):
        """Save the fit to an output file.
        """
        if self.res is None:
            self.fit_data()
        if not args.output_filename:
            path = tkinter.filedialog.asksaveasfilename()
        else:
            path = args.output_filename
        if path:
            root, ext = os.path.splitext(path)
            if save_plot:
                # Produce a descriptive title for the plot:
                title = PROG_NAME + ' ' + __version__
                try:
                    title += " shot %d" % (self.combined_p.shot)
                except AttributeError:
                    pass
                try:
                    title += " t_min %f" % (self.combined_p.t_min)
                except AttributeError:
                    pass
                try:
                    title += " t_max %f" % (self.combined_p.t_max)
                except AttributeError:
                    pass
                if hasattr(self.combined_p, 'times'):
                    times = list(self.combined_p.times)
                    title += " times %f" % (times.pop())
                    for t in times:
                        title += ",%f" % (t,)
                try:
                    title += " coordinate %s" % (self.combined_p.abscissa)
                except AttributeError:
                    pass
                
                self.plot_frame.suptitle.set_text(title)
                
                self.plot_frame.f.savefig(
                    os.path.expanduser(root) + '.pdf',
                    format='pdf'
                )
            history = (
                "Created by user {user} on {host} with {module} version {ver} on {time}.\n".format(
                    host=socket.gethostname(),
                    user=getpass.getuser(),
                    module=inspect.stack()[0][1],
                    ver=__version__,
                    time=time.asctime()
                )
            )
            if ext.lower() == '.csv':
                # Write output to CSV file:
                self.control_frame.status_frame.add_line(
                    "Writing results to CSV file %s..." % os.path.basename(path)
                )
                X_name = (
                    self.combined_p.X_labels[0] + ' [' + self.combined_p.X_units[0] + ']'
                    if self.combined_p.X_units[0]
                    else self.combined_p.X_labels[0]
                )
                y_name = (
                    self.combined_p.y_label + ' [' + self.combined_p.y_units + ']'
                    if self.combined_p.y_units
                    else self.combined_p.y_label
                )
                with open(os.path.expanduser(path), 'wb') as outfile:
                    # Write metadata:
                    metadata = history
                    try:
                        metadata += "shot %d\n" % (self.combined_p.shot)
                    except AttributeError:
                        pass
                    try:
                        metadata += "t_min %f\n" % (self.combined_p.t_min)
                    except AttributeError:
                        pass
                    try:
                        metadata += "t_max %f\n" % (self.combined_p.t_max)
                    except AttributeError:
                        pass
                    if hasattr(self.combined_p, 'times'):
                        times = list(self.combined_p.times)
                        metadata += "times %f" % (times.pop())
                        for t in times:
                            metadata += ",%f" % (t,)
                        metadata += "\n"
                    try:
                        metadata += "coordinate %s\n" % (self.combined_p.abscissa)
                    except AttributeError:
                        pass
                    
                    if self.mean_vol_avg:
                        metadata += "vol_avg %f\nerr_vol_avg %f\n" % (self.mean_vol_avg, self.std_vol_avg,)
                    if self.mean_peaking:
                        metadata += "peaking %f\nerr_peaking %f\n" % (self.mean_peaking, self.std_peaking,)
                    
                    outfile.write(
                        "metadata %d\n" % (len(metadata.splitlines()) + 1,) + metadata
                    )
                    
                    writer = csv.writer(outfile)
                    if 'mean_a_L' in self.res:
                        writer.writerow(
                            [X_name,
                             y_name, 'err_' + y_name,
                             'D' + self.combined_p.y_label, 'err_D' + self.combined_p.y_label,
                             'a_L' + self.combined_p.y_label, 'err_a_L' + self.combined_p.y_label]
                        )
                        writer.writerows(
                            list(zip(
                                self.X,
                                self.res['mean_val'], self.res['std_val'],
                                self.res['mean_grad'], self.res['std_grad'],
                                self.res['mean_a_L'], self.res['std_a_L']
                            ))
                        )
                    else:
                        writer.writerow([X_name, y_name, 'err_' + y_name])
                        writer.writerows(list(zip(self.X, self.res['mean_val'], self.res['std_val'])))
            elif ext.lower() == '.pkl':
                # Write output to dictionary in pickle file:
                self.control_frame.status_frame.add_line(
                    "Writing results to pickle file %s..." % os.path.basename(path)
                )
                res_dict = {
                    'X': self.X,
                    'y': self.res['mean_val'],
                    'err_y': self.res['std_val'],
                    'X_label': self.combined_p.X_labels[0],
                    'X_units': self.combined_p.X_units[0],
                    'y_label': self.combined_p.y_label,
                    'y_units': self.combined_p.y_units
                }
                if 'mean_a_L' in self.res:
                    res_dict["dy/dX"] = self.res['mean_grad']
                    res_dict["err_dy/dX"] = self.res['std_grad']
                    res_dict["a_Ly"] = self.res['mean_a_L']
                    res_dict["err_a_Ly"] = self.res['std_a_L']
                
                # Add metadata:
                res_dict['history'] = history
                try:
                    res_dict['shot'] = self.combined_p.shot
                except AttributeError:
                    pass
                try:
                    res_dict['t_min'] = self.combined_p.t_min
                except AttributeError:
                    pass
                try:
                    res_dict['t_max']  = self.combined_p.t_max
                except AttributeError:
                    pass
                try:
                    res_dict['times'] = list(self.combined_p.times)
                except AttributeError:
                    pass
                try:
                    res_dict['coordinate'] = self.combined_p.abscissa
                except AttributeError:
                    pass
                
                if self.mean_vol_avg:
                    res_dict['vol_avg'] = self.mean_vol_avg
                    res_dict['err_vol_avg'] = self.std_vol_avg
                if self.mean_peaking:
                    res_dict['peaking'] = self.mean_peaking
                    res_dict['err_peaking'] = self.std_peaking
                
                with open(os.path.expanduser(path), 'wb') as f:
                    pickle.dump(res_dict, f)
            else:
                # Write output to NetCDF file:
                self.control_frame.status_frame.add_line(
                    "Writing results to NetCDF file %s..." % os.path.basename(path)
                )
                X_name = self.combined_p.X_labels[0].translate(None, '\\$')
                X_units = self.combined_p.X_units[0]
                y_name = self.combined_p.y_label.translate(None, '\\$')
                y_units = self.combined_p.y_units
                
                with scipy.io.netcdf.netcdf_file(os.path.expanduser(path), mode='w') as f:
                    f.history = history
                    try:
                        f.shot = self.combined_p.shot
                    except AttributeError:
                        pass
                    try:
                        f.t_min = self.combined_p.t_min
                    except AttributeError:
                        pass
                    try:
                        f.t_max  = self.combined_p.t_max
                    except AttributeError:
                        pass
                    try:
                        f.times = list(self.combined_p.times)
                    except AttributeError:
                        pass
                    try:
                        f.coordinate = self.combined_p.abscissa
                    except AttributeError:
                        pass
                    
                    if self.mean_vol_avg:
                        f.vol_avg = self.mean_vol_avg
                        f.err_vol_avg = self.std_vol_avg
                    if self.mean_peaking:
                        f.peaking = self.mean_peaking
                        f.err_peaking = self.std_peaking
                    
                    f.x_name = X_name
                    f.createDimension(X_name, len(self.X))
                    v_X = f.createVariable(X_name, float, (X_name,))
                    v_X[:] = self.X
                    v_X.units = X_units
                    v_y = f.createVariable(y_name, float, (X_name,))
                    v_y[:] = self.res['mean_val']
                    v_y.units = y_units
                    v_err_y = f.createVariable('err_'+y_name, float, (X_name,))
                    v_err_y[:] = self.res['std_val']
                    v_err_y.units = y_units
                    if 'mean_a_L' in self.res:
                        v_grad = f.createVariable("d%s/d%s" % (y_name, X_name), float, (X_name,))
                        v_grad[:] = self.res['mean_grad']
                        v_grad.units = y_units + '/' + X_units
                        v_err_grad = f.createVariable("err_d%s/d%s" % (y_name, X_name), float, (X_name,))
                        v_err_grad[:] = self.res['std_grad']
                        v_err_grad.units = y_units + '/' + X_units
                        
                        v_a_L = f.createVariable("a_L%s" % (y_name,), float, (X_name,))
                        v_a_L[:] = self.res['mean_a_L']
                        v_a_L.units = ''
                        v_err_a_L = f.createVariable("err_a_L%s" % (y_name,), float, (X_name,))
                        v_err_a_L[:] = self.res['std_a_L']
                        v_err_a_L.units = ''
            
            self.control_frame.status_frame.add_line(
                "Done writing results."
            )
    
    def exit(self):
        """Quit the program, cleaning up as needed.
        """
        self.destroy()

class MCMCResultsFrame(tk.Frame):
    """Frame to plot the results of the MCMC sampler.
    """
    def __init__(self, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)
        
        sampler = self.master.master.sampler
        k = sampler.flatchain.shape[1]
        
        self.f = Figure()
        gs1 = mplgs.GridSpec(k, k)
        gs2 = mplgs.GridSpec(1, k)
        gs1.update(bottom=0.275, top=0.98)
        gs2.update(bottom=0.1, top=0.2)
        self.axes = []
        # j is the row, i is the column.
        for j in range(0, k + 1):
            row = []
            for i in range(0, k):
                if i > j:
                    row.append(None)
                else:
                    sharey = row[-1] if i > 0 and i < j and j < k else None
                    sharex = self.axes[-1][i] if j > i and j < k else \
                        (row[-1] if i > 0 and j == k else None)
                    gs = gs1[j, i] if j < k else gs2[:, i]
                    row.append(self.f.add_subplot(gs, sharey=sharey, sharex=sharex))
            self.axes.append(row)
        self.axes = scipy.asarray(self.axes)
        
        self.canvas = FigureCanvasTkAgg(self.f, master=self)
        self.canvas.show()
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky='NESW')
        
        self.toolbar_frame = tk.Frame(self)
        self.toolbar = NavigationToolbar2TkAgg(self.canvas, self.toolbar_frame)
        self.toolbar.update()
        # self.canvas._tkcanvas.grid(row=1, column=0, sticky='EW')
        self.toolbar_frame.grid(row=1, column=0, sticky='EW')
        
        self.canvas.mpl_connect('button_press_event', lambda event: self.canvas._tkcanvas.focus_set())
        self.canvas.mpl_connect('key_press_event', self.on_key_event)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.refresh()
    
    def on_key_event(self, evt):
        """Respond to key presses.
        """
        key_press_handler(evt, self.canvas, self.toolbar)
    
    def print_stats(self, box):
        """Print the statistics of the sampler to the given `box`.
        
        `box` can be anything with a :py:meth:`add_line` method.
        """
        sampler = self.master.master.sampler
        try:
            box.add_line("MCMC sampler autocorrelation times:\n%s" % (sampler.acor,))
        except RuntimeError:
            box.add_line("Could not compute MCMC sampler autocorrelation times.")
        box.add_line("MCMC sampler mean acceptance fraction: %.2f%%" % (100 * scipy.mean(sampler.acceptance_fraction),))
        box.add_line("Parameter summary:")
        box.add_line("param\tmean\t95% posterior interval")
        try:
            burn = int(self.master.master.control_frame.fitting_frame.MCMC_frame.burn_box.get())
        except ValueError:
            self.master.MCMC_control_frame.help_box.add_line("Invalid value for burn! Defaulting to 0.")
            burn = 0
        if burn >= sampler.chain.shape[1]:
            burn = 0
        mean, ci_l, ci_u = gptools.summarize_sampler(sampler, burn=burn)
        names = HYPERPARAMETERS[self.master.master.control_frame.kernel_frame.kernel_type_frame.k_var.get()]
        for n, m, l, u in zip(names, mean, ci_l, ci_u):
            box.add_line("%s\t%4.4g\t[%4.4g, %4.4g]" % (n, m, l, u))
    
    def refresh(self, print_stats=True):
        """Refresh the plot.
        """
        sampler = self.master.master.sampler
        
        if sampler:
            if print_stats:
                self.print_stats(self.master.MCMC_control_frame.help_box)
            labels = ['$%s$' % (l,) for l in self.master.master.combined_p.gp.free_param_names]
            k = sampler.flatchain.shape[1]
            
            try:
                burn = int(self.master.master.control_frame.fitting_frame.MCMC_frame.burn_box.get())
            except ValueError:
                self.master.MCMC_control_frame.help_box.add_line("Invalid value for burn! Defaulting to 0.")
                burn = 0
            if burn >= sampler.chain.shape[1]:
                burn = 0
            
            flat_trace = sampler.chain[:, burn:, :]
            flat_trace = flat_trace.reshape((-1, k))
            
            # j is the row, i is the column.
            # Loosely based on triangle.py
            for i in range(0, k):
                self.axes[i, i].clear()
                self.axes[i, i].hist(flat_trace[:, i], bins=50)
                if i == k - 1:
                    self.axes[i, i].set_xlabel(labels[i])
                if i < k - 1:
                    plt.setp(self.axes[i, i].get_xticklabels(), visible=False)
                plt.setp(self.axes[i, i].get_yticklabels(), visible=False)
                # for j in xrange(0, i):
                #     self.axes[j, i].set_visible(False)
                #     self.axes[j, i].set_frame_on(False)
                for j in range(i + 1, k):
                    self.axes[j, i].clear()
                    ct, x, y, im = self.axes[j, i].hist2d(flat_trace[:, i], flat_trace[:, j], bins=50)
                    # xmid = 0.5 * (x[1:] + x[:-1])
                    # ymid = 0.5 * (y[1:] + y[:-1])
                    # self.axes[j, i].contour(xmid, ymid, ct.T, colors='k')
                    if j < k - 1:
                        plt.setp(self.axes[j, i].get_xticklabels(), visible=False)
                    if i != 0:
                        plt.setp(self.axes[j, i].get_yticklabels(), visible=False)
                    if i == 0:
                        self.axes[j, i].set_ylabel(labels[j])
                    if j == k - 1:
                        self.axes[j, i].set_xlabel(labels[i])
                self.axes[-1, i].clear()
                self.axes[-1, i].plot(sampler.chain[:, :, i].T)
                self.axes[-1, i].axvline(burn, color='r', linewidth=3)
                self.axes[-1, i].set_ylabel(labels[i])
                self.axes[-1, i].set_xlabel('step')
        
            self.canvas.draw()
        else:
            self.master.MCMC_control_frame.help_box.add_line(
                "Sampler is invalid, please set valid parameter values and resample!"
            )

class MCMCControlFrame(tk.Frame):
    """Frame to hold results of the MCMC sampler.
    """
    def __init__(self, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)
        
        self.help_box = StatusBox(self, **FRAME_PARAMS)
        self.help_box.grid(row=0, column=0, sticky='EWNS')
        self.help_box.add_line(
"""\nCheck to make sure the output of the MCMC sampler
looks correct.

1.) The chains (bottom plots) should be well mixed:
    they should all overlap and not spend too much
    time in any given spot. Set burn to the
    iteration number at which they appear to
    become mixed and the initial transients have
    died down.

2.) The univariate marginals (diagonal of the
    matrix) should be peaked and go to zero near
    the edges. It is also preferable that they be
    unimodal. If they look wrong, try adjusting
    the bounds to exclude any unphysical modes.

3.) The bivariate marginals should also be unimodal.
"""
        )
        
        self.control_frame = tk.Frame(self)
        
        self.resample_button = tk.Button(
            self.control_frame,
            text="resample",
            command=self.resample
        )
        self.resample_button.grid(row=0, column=0, sticky='W')
        
        self.add_sample_button = tk.Button(
            self.control_frame,
            text="add samples",
            command=self.add_samples
        )
        self.add_sample_button.grid(row=0, column=1)
        
        self.burn_button = tk.Button(
            self.control_frame,
            text="apply burn",
            command=self.apply_burn
        )
        self.burn_button.grid(row=0, column=2)
        
        self.reject_button = tk.Button(
            self.control_frame,
            text="abort",
            command=self.abort
        )
        self.reject_button.grid(row=0, column=3, sticky='W')
        
        self.accept_button = tk.Button(
            self.control_frame,
            text="continue",
            command=self.continue_
        )
        self.accept_button.grid(row=0, column=4, sticky='W')
        
        self.control_frame.grid(row=3, column=0, sticky='EW')
        
        self.entry_frame = MCMCFrame(self, **FRAME_PARAMS)
        self.entry_frame.grid(row=1, column=0, columnspan=5, sticky='EW')
        
        # Update from master frame:
        self.entry_frame.walker_box.delete(0, tk.END)
        self.entry_frame.walker_box.insert(
            0,
            self.master.master.control_frame.fitting_frame.MCMC_frame.walker_box.get()
        )
        self.entry_frame.sample_box.delete(0, tk.END)
        self.entry_frame.sample_box.insert(
            0,
            self.master.master.control_frame.fitting_frame.MCMC_frame.sample_box.get()
        )
        self.entry_frame.burn_box.delete(0, tk.END)
        self.entry_frame.burn_box.insert(
            0,
            self.master.master.control_frame.fitting_frame.MCMC_frame.burn_box.get()
        )
        self.entry_frame.keep_box.delete(0, tk.END)
        self.entry_frame.keep_box.insert(
            0,
            self.master.master.control_frame.fitting_frame.MCMC_frame.keep_box.get()
        )
        
        # Input hyperparameter bounds:
        self.bounds_meta_frame = tk.Frame(self, **FRAME_PARAMS)
        self.bounds_label = tk.Label(
            self.bounds_meta_frame,
            text="hyperparameter bounds:"
        )
        self.bounds_label.grid(row=0, column=0, sticky='W')
        
        self.bounds_frame = KernelBoundsFrame(
            HYPERPARAMETERS[self.master.master.control_frame.kernel_frame.kernel_type_frame.k_var.get()],
            self.bounds_meta_frame
        )
        self.bounds_frame.grid(row=1, column=0, sticky='EW')
        
        self.bounds_meta_frame.grid(row=2, column=0, sticky='EW')
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.process_bounds()
    
    def process_bounds(self):
        """Process the hyperparameter bounds and propagate back to the parent Frame.
        """
        for k, l, u in zip(list(range(0, len(self.master.master.combined_p.gp.free_param_bounds))),
                           self.bounds_frame.lower_bounds,
                           self.bounds_frame.upper_bounds):
            # We know that by the point this gets called, the hyperprior has the right bounds as set in the main window:
            old_bounds = self.master.master.combined_p.gp.free_param_bounds[k]
            new_bounds = list(old_bounds)
            
            new_lb = l.get()
            try:
                new_bounds[0] = float(new_lb)
            except ValueError:
                if new_lb == '':
                    l.insert(0, str(old_bounds[0]))
                else:
                    self.help_box.add_line(
                        "Invalid lower bound %s for %s, will use default value "
                        "instead." % (new_lb, k,)
                    )
                
            new_ub = u.get()
            try:
                new_bounds[1] = float(new_ub)
            except ValueError:
                if new_ub == '':
                    u.insert(0, str(old_bounds[1]))
                else:
                    self.help_box.add_line(
                        "Invalid upper bound %s for %s, will use default value "
                        "instead." % (new_ub, k,)
                    )
            
            self.master.master.combined_p.gp.free_param_bounds[k] = new_bounds
        
        # Propagate the bounds back to the main window:
        for l, u in zip(self.master.master.control_frame.kernel_frame.bounds_frame.lower_bounds,
                        self.master.master.control_frame.kernel_frame.bounds_frame.upper_bounds):
            l.delete(0, tk.END)
            u.delete(0, tk.END)
        self.master.master.process_bounds()
    
    def update_MCMC_params(self, walkers=True, sample=True, burn=True, thin=True):
        """Update the MCMC parameters and propagate back to the parent Frame.
        """
        if walkers:
            self.master.master.control_frame.fitting_frame.MCMC_frame.walker_box.delete(0, tk.END)
            self.master.master.control_frame.fitting_frame.MCMC_frame.walker_box.insert(
                0,
                self.entry_frame.walker_box.get()
            )
        if sample:
            self.master.master.control_frame.fitting_frame.MCMC_frame.sample_box.delete(0, tk.END)
            self.master.master.control_frame.fitting_frame.MCMC_frame.sample_box.insert(
                0,
                self.entry_frame.sample_box.get()
            )
        if burn:
            self.master.master.control_frame.fitting_frame.MCMC_frame.burn_box.delete(0, tk.END)
            self.master.master.control_frame.fitting_frame.MCMC_frame.burn_box.insert(
                0,
                self.entry_frame.burn_box.get()
            )
        if thin:
            self.master.master.control_frame.fitting_frame.MCMC_frame.keep_box.delete(0, tk.END)
            self.master.master.control_frame.fitting_frame.MCMC_frame.keep_box.insert(
                0,
                self.entry_frame.keep_box.get()
            )
    
    def continue_(self):
        """Accept the samples and evaluate.
        """
        self.help_box.add_line("Continuing...")
        self.process_bounds()
        self.update_MCMC_params()
        self.master.destroy()
    
    def abort(self):
        """Reject the samples and return to the parent window.
        """
        self.help_box.add_line("Aborting evaluation...")
        self.process_bounds()
        self.master.master.sampler.pool.close()
        self.master.master.sampler = None
        self.master.destroy()
    
    def resample(self):
        """Re-run the sampler with new hyperparameters.
        """
        self.help_box.add_line("Re-running MCMC sampler...")
        self.process_bounds()
        self.update_MCMC_params()
        try:
            self.master.master.sampler.pool.close()
        except AttributeError:
            pass
        self.master.master.sampler = None
        self.master.master.run_MCMC_sampler()
        self.master.MCMC_frame.refresh()
        self.help_box.add_line("Done resampling.")
    
    def add_samples(self):
        """Add samples without changing the hyperparameter bounds.
        """
        self.help_box.add_line("Adding new samples...")
        self.update_MCMC_params(walkers=False)
        self.master.master.run_MCMC_sampler()
        self.master.MCMC_frame.refresh()
        self.help_box.add_line("Done sampling.")
    
    def apply_burn(self):
        """Replot with new burn.
        """
        self.update_MCMC_params(walkers=False, sample=False, thin=False)
        self.master.MCMC_frame.refresh(print_stats=False)

class MCMCWindow(tk.Toplevel):
    """Window to display and interact with results of MCMC sampler.
    """
    def __init__(self, *args, **kwargs):
        tk.Toplevel.__init__(self, *args, **kwargs)
        
        self.wm_title("%s %s: MCMC results" % (PROG_NAME, __version__,))
        
        self.MCMC_control_frame = MCMCControlFrame(self)
        
        self.MCMC_frame = MCMCResultsFrame(self)
        
        self.MCMC_frame.grid(row=0, column=0, sticky='NSEW')
        self.MCMC_control_frame.grid(row=0, column=1, sticky='NSEW')
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)


if __name__ == "__main__":
    root = FitWindow()
    
    # Populate the GUI with parameters from args:
    if not args.kernel:
        if args.core_only:
            args.kernel = 'SE'
        else:
            args.kernel = 'gibbstanh'
    elif args.kernel == 'SEsym1d':
        args.no_core_constraint = True
    
    # Turn off edge constraint for --core-only:
    if args.core_only:
        args.no_edge_constraint = True

    # Bump random starts up to 4 for low processor count machines:
    if not args.random_starts:
        num_proc = multiprocessing.cpu_count()
        if num_proc < 4:
            args.random_starts = 4
        else:
            args.random_starts = min(num_proc, 20)
    
    if args.signal:
        root.control_frame.data_source_frame.signal_coordinate_frame.signal_var.set(args.signal)
        root.control_frame.data_source_frame.update_signal(args.signal)
    if args.shot is not None:
        root.control_frame.data_source_frame.shot_frame.shot_box.delete(0, tk.END)
        root.control_frame.data_source_frame.shot_frame.shot_box.insert(0, str(args.shot))
    if args.t_min is not None:
        root.control_frame.averaging_frame.time_window_frame.t_min_box.delete(0, tk.END)
        root.control_frame.averaging_frame.time_window_frame.t_min_box.insert(0, str(args.t_min))
    if args.t_max is not None:
        root.control_frame.averaging_frame.time_window_frame.t_max_box.delete(0, tk.END)
        root.control_frame.averaging_frame.time_window_frame.t_max_box.insert(0, str(args.t_max))
    if args.t_points:
        root.control_frame.averaging_frame.time_window_frame.point_button.invoke()
        root.control_frame.averaging_frame.time_window_frame.times_box.delete(0, tk.END)
        root.control_frame.averaging_frame.time_window_frame.times_box.insert(0, str(args.t_points)[1:-1])
    if args.npts is not None:
        root.control_frame.eval_frame.npts_box.delete(0, tk.END)
        root.control_frame.eval_frame.npts_box.insert(0, str(args.npts))
    if args.x_min is not None:
        root.control_frame.eval_frame.x_min_box.delete(0, tk.END)
        root.control_frame.eval_frame.x_min_box.insert(0, str(args.x_min))
    if args.x_max is not None:
        root.control_frame.eval_frame.x_max_box.delete(0, tk.END)
        root.control_frame.eval_frame.x_max_box.insert(0, str(args.x_max))
    if args.x_pts:
        root.control_frame.eval_frame.points_button.invoke()
        root.control_frame.eval_frame.x_points_box.delete(0, tk.END)
        root.control_frame.eval_frame.x_points_box.insert(0, str(args.x_pts)[1:-1])
    if args.system:
        systems = set(args.system)
        if 'TS' in systems:
            systems.remove('TS')
            systems.add('ETS')
            systems.add('CTS')
        for b in root.control_frame.data_source_frame.system_frame.buttons:
            if b.system in systems:
                b.button.select()
            else:
                b.button.deselect()
    if args.kernel:
        root.control_frame.kernel_frame.kernel_type_frame.k_var.set(args.kernel)
        root.control_frame.kernel_frame.update_kernel(args.kernel)
    if args.coordinate:
        root.control_frame.data_source_frame.signal_coordinate_frame.coordinate_var.set(args.coordinate)
    if args.core_constraint_location is not None:
        root.control_frame.kernel_frame.constraints_frame.core_loc.delete(0, tk.END)
        root.control_frame.kernel_frame.constraints_frame.core_loc.insert(0, str(args.core_constraint_location)[1:-1])
    if args.edge_constraint_locations:
        root.control_frame.kernel_frame.constraints_frame.edge_loc.delete(0, tk.END)
        root.control_frame.kernel_frame.constraints_frame.edge_loc.insert(0, str(args.edge_constraint_locations)[1:-1])
    if args.no_core_constraint:
        root.control_frame.kernel_frame.constraints_frame.core_button.deselect()
        root.control_frame.kernel_frame.constraints_frame.update_core()
    if args.no_edge_constraint:
        root.control_frame.kernel_frame.constraints_frame.edge_button.deselect()
        root.control_frame.kernel_frame.constraints_frame.update_edge()
    if args.core_only:
        root.control_frame.kernel_frame.kernel_type_frame.core_only_button.select()
    if args.unweighted:
        root.control_frame.averaging_frame.method_frame.weighted_button.deselect()
    if args.robust:
        root.control_frame.averaging_frame.method_frame.method_var.set('robust')
    if args.all_points:
        root.control_frame.averaging_frame.method_frame.method_var.set('all points')
    root.control_frame.averaging_frame.method_frame.error_method_var.set(args.uncertainty_method.replace('_', ' '))
    root.control_frame.averaging_frame.method_frame.update_method(
        root.control_frame.averaging_frame.method_frame.method_var.get()
    )
    if args.change_threshold is not None:
        root.control_frame.outlier_frame.extreme_button.invoke()
        root.control_frame.outlier_frame.extreme_thresh_box.delete(0, tk.END)
        root.control_frame.outlier_frame.extreme_thresh_box.insert(0, str(args.change_threshold))
    if args.outlier_threshold is not None:
        root.control_frame.outlier_frame.outlier_button.invoke()
        root.control_frame.outlier_frame.outlier_thresh_box.delete(0, tk.END)
        root.control_frame.outlier_frame.outlier_thresh_box.insert(0, str(args.outlier_threshold))
    if args.random_starts is not None:
        root.control_frame.fitting_frame.method_frame.starts_box.delete(0, tk.END)
        root.control_frame.fitting_frame.method_frame.starts_box.insert(0, str(args.random_starts))
    if args.bounds:
        for k in range(0, len(root.control_frame.kernel_frame.bounds_frame.lower_bounds)):
            root.control_frame.kernel_frame.bounds_frame.lower_bounds[k].delete(0, tk.END)
            root.control_frame.kernel_frame.bounds_frame.lower_bounds[k].insert(0, str(args.bounds[2*k]))
            root.control_frame.kernel_frame.bounds_frame.upper_bounds[k].delete(0, tk.END)
            root.control_frame.kernel_frame.bounds_frame.upper_bounds[k].insert(0, str(args.bounds[2*k+1]))
    if args.input_filename:
        root.control_frame.data_source_frame.tree_file_frame.file_button.invoke()
        root.control_frame.data_source_frame.tree_file_frame.path_entry.delete(0, tk.END)
        root.control_frame.data_source_frame.tree_file_frame.path_entry.insert(0, args.input_filename)
    if args.abscissa_name:
        root.control_frame.data_source_frame.tree_file_frame.file_button.invoke()
        if len(args.abscissa_name) == 2:
            root.control_frame.data_source_frame.variable_name_frame.time_box.delete(0, tk.END)
            root.control_frame.data_source_frame.variable_name_frame.time_box.insert(0, str(args.abscissa_name[0]))
        root.control_frame.data_source_frame.variable_name_frame.space_box.delete(0, tk.END)
        root.control_frame.data_source_frame.variable_name_frame.space_box.insert(0, str(args.abscissa_name[-1]))
    if args.ordinate_name:
        root.control_frame.data_source_frame.tree_file_frame.file_button.invoke()
        root.control_frame.data_source_frame.variable_name_frame.data_box.delete(0, tk.END)
        root.control_frame.data_source_frame.variable_name_frame.data_box.insert(0, str(args.ordinate_name))
    if args.metadata_lines is not None:
        root.control_frame.data_source_frame.variable_name_frame.meta_box.delete(0, tk.END)
        root.control_frame.data_source_frame.variable_name_frame.meta_box.insert(0, str(args.metadata_lines))
    if args.use_MCMC:
        root.control_frame.fitting_frame.method_frame.MCMC_button.invoke()
    if args.walkers is not None:
        root.control_frame.fitting_frame.MCMC_frame.walker_box.delete(0, tk.END)
        root.control_frame.fitting_frame.MCMC_frame.walker_box.insert(0, str(args.walkers))
    if args.MCMC_samp is not None:
        root.control_frame.fitting_frame.MCMC_frame.sample_box.delete(0, tk.END)
        root.control_frame.fitting_frame.MCMC_frame.sample_box.insert(0, str(args.MCMC_samp))
    if args.burn is not None:
        root.control_frame.fitting_frame.MCMC_frame.burn_box.delete(0, tk.END)
        root.control_frame.fitting_frame.MCMC_frame.burn_box.insert(0, str(args.burn))
    if args.keep is not None:
        root.control_frame.fitting_frame.MCMC_frame.keep_box.delete(0, tk.END)
        root.control_frame.fitting_frame.MCMC_frame.keep_box.insert(0, str(args.keep))
    if args.full_monte_carlo:
        root.control_frame.fitting_frame.MCMC_constraint_frame.full_MC_button.select()
        root.control_frame.fitting_frame.MCMC_constraint_frame.update_full_MC()
    if args.monte_carlo_samples:
        state = root.control_frame.fitting_frame.MCMC_constraint_frame.samples_box['state']
        root.control_frame.fitting_frame.MCMC_constraint_frame.samples_box.config(state=tk.NORMAL)
        root.control_frame.fitting_frame.MCMC_constraint_frame.samples_box.delete(0, tk.END)
        root.control_frame.fitting_frame.MCMC_constraint_frame.samples_box.insert(0, str(args.monte_carlo_samples))
        root.control_frame.fitting_frame.MCMC_constraint_frame.samples_box.config(state=state)
    if args.reject_negative:
        root.control_frame.fitting_frame.MCMC_constraint_frame.pos_button.select()
    if args.reject_non_monotonic:
        root.control_frame.fitting_frame.MCMC_constraint_frame.mono_button.select()
    if args.no_a_over_L:
        root.control_frame.eval_frame.a_L_button.deselect()
    root.control_frame.eval_frame.update_a_L()
    if args.compute_vol_avg:
        root.control_frame.eval_frame.vol_avg_button.select()
    if args.compute_peaking:
        root.control_frame.eval_frame.peaking_button.select()
    if args.compute_TCI:
        root.control_frame.eval_frame.TCI_button.select()
    if args.x_lim:
        root.control_frame.plot_param_frame.x_lb_box.delete(0, tk.END)
        root.control_frame.plot_param_frame.x_lb_box.insert(0, str(args.x_lim[0]))
        root.control_frame.plot_param_frame.x_ub_box.delete(0, tk.END)
        root.control_frame.plot_param_frame.x_ub_box.insert(0, str(args.x_lim[1]))
    if args.y_lim:
        root.control_frame.plot_param_frame.y_lb_box.delete(0, tk.END)
        root.control_frame.plot_param_frame.y_lb_box.insert(0, str(args.y_lim[0]))
        root.control_frame.plot_param_frame.y_ub_box.delete(0, tk.END)
        root.control_frame.plot_param_frame.y_ub_box.insert(0, str(args.y_lim[1]))
    if args.EFIT_tree:
        root.control_frame.data_source_frame.EFIT_frame.EFIT_field.delete(0, tk.END)
        root.control_frame.data_source_frame.EFIT_frame.EFIT_field.insert(0, args.EFIT_tree)
    if args.plot_idxs:
        root.control_frame.outlier_frame.show_idx_button.select()
    if args.remove_points:
        root.control_frame.outlier_frame.specific_box.insert(0, str(args.remove_points)[1:-1])
    
    if args.full_auto or args.no_interaction:
        root.load_data()
        root.average_data()
        root.fit_data()
        if args.no_interaction:
            root.save_fit(save_plot=True)
            root.exit()
        
    if not args.no_interaction and not args.no_mainloop:
        root.mainloop()

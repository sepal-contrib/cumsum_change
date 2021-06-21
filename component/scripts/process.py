import os
import time
from datetime import timedelta
from pathlib import Path
import concurrent.futures

import gdal
import pandas as pd
import numpy as np
import rasterio as rio

import tensorflow as tf 
import tensorflow_probability as tfp

from component import parameter as cp
from component.message import cm


def cumsum(residuals, threshold=None):
    
    # do cumsum calculation
    cumsum = tf.math.cumsum(residuals, axis=0)
    s_max = tf.math.reduce_max(cumsum, axis=0)
    s_min = tf.math.reduce_min(cumsum, axis=0)
    s_diff = tf.subtract(s_max, s_min)
    
    # get podition of max value
    argmax = tf.math.argmax(cumsum, axis=0)
    
    # filter out based on expected change
    if threshold:
        
        # we might have all zeros within s_diff tile. the bollenamask is empty and throws an error
        # therefore we simply set the full output to zeros in that case
        try:
            n = tf.cast(tfp.stats.percentile(tf.boolean_mask(s_diff, tf.math.not_equal(s_diff, 0)), 95), 'float32')
            argmax = tf.where(tf.greater(n, s_diff), tf.zeros_like(argmax), argmax)
            s_diff = tf.where(tf.greater(n, s_diff), tf.zeros_like(s_diff), s_diff)
        except:  
            argmax = tf.zeros_like(argmax)
            s_diff = tf.zeros_like(s_diff)
            
    return s_diff, argmax


def bootstrap(stack, s_diff, nr_bootstraps):
    
    # intialize iteration variables
    i, comparison_array, change_sum = 0, tf.zeros(s_diff.shape), tf.zeros(s_diff.shape)
    while i < nr_bootstraps:
        
        # shuffle first axis 
        shuffled_index = tf.random.shuffle(range(stack.shape[0]))
        
        # run cumsum on re-shuffled stack
        s_diff_bs, _ = cumsum(tf.gather(stack, shuffled_index, axis=0))
        
        # compare if s_diff_bs is greater and sum up
        comparison_array += tf.cast(tf.greater(s_diff, s_diff_bs), 'float32') 
        
        # sum up random change magnitude s_diff_bs 
        change_sum += s_diff_bs
        
        # set counter
        i+=1
    
    # calculate final confidence and significance
    confidences = tf.math.divide_no_nan(comparison_array, nr_bootstraps)
    signficance = tf.math.subtract(1, tf.math.divide_no_nan(tf.math.divide_no_nan(change_sum, nr_bootstraps), s_diff))
    
    # calculate final confidence level
    change_point_confidence = tf.math.multiply(confidences, signficance)
    
    return change_point_confidence


def main(args_list):
   
    
    infile, outfile, params = args_list
    nr_bootstraps, date_index_subset, dates_float, threshold_area, threshold_change = params.values()

    with rio.open(infile) as src:
        
        # get dates from descriptions 
        dates = list(src.descriptions)

        # sort them ascedning
        dates_sorted = sorted(dates)

        # get band number index
        idx = [dates.index(date) for date in dates_sorted]

        # update metadata
        outmeta = src.meta
        outmeta.update(count=3, driver='GTiff', dtype='float32')
        outmeta.update(blockxsize=256, blockysize=256, tiled=True)
        
        with rio.open(outfile, "w", **outmeta) as dst:
            
            for ij, window in dst.block_windows():
                
                # read array
                stack = src.read(window=window)[idx]
                
                # subset stack by start and enddate
                stack_tf = tf.convert_to_tensor(np.nan_to_num(stack[date_index_subset]), dtype='float32')
                mask = tf.convert_to_tensor(np.isfinite(stack[date_index_subset]).astype('float32'), dtype='float32')

                # calculate mean
                mean_tf = tf.math.divide_no_nan(tf.math.reduce_sum(stack_tf, axis=0), tf.math.reduce_sum(mask, axis=0))

                # calculate residuals (broadcasting here)
                residuals = tf.math.subtract(stack_tf, mean_tf)

                # mask original nans of stack and treat them as zeros
                residuals = tf.where(tf.math.equal(stack_tf, 0), tf.zeros_like(stack_tf), residuals)

                # get original cumsum caluclation and dates
                s_diff, argmax = cumsum(residuals, threshold_area)

                # get dates into change array
                change = np.array(dates_float)[argmax.numpy()]
                s_diff = s_diff.numpy()
                # get s_diff into shape of residuals and mask residuals by it
                #residuals_masked = tf.broadcast_to(tf.math.divide_no_nan(s_diff, s_diff), residuals.shape) * residuals

                # get confidence from bootstrap procedure
                confidences = bootstrap(residuals, s_diff, nr_bootstraps).numpy()
                confidences[s_diff==0] = 0
                # set change pixels with 0 confidence to 0
                change[confidences<threshold_change] = 0
                s_diff[confidences<threshold_change] = 0
                change[s_diff==0] = 0
                
                # write to output
                out_stack = np.stack((change, confidences, s_diff)).astype(np.float32)
                dst.write(out_stack, window=window)
                

def run_cumsum(ts_folder, outdir, tiles, period, bstraps, area_thld, conf_thld, out):
    
    out.add_live_msg('Preparing processing')
    # create output folder and file
    outdir = cp.result_dir/outdir
    outdir.mkdir(exist_ok=True, parents=True)
    result_file = outdir.joinpath(f'cumsum_results.tif')
    
    # create list of args for parallel processing
    args_list, outfiles = [], [] 
    for tile in tiles:
        
        # get the dates files
        dates_file = list(ts_folder.glob(f'{tile}/dates.csv'))[0]

        # get the tiles
        sub_stack_files = list(ts_folder.glob(f'{tile}/tile*/stack.vrt'))

        with open(dates_file) as f:
            dates = f.readlines()

        # create time index and subset
        date_index = pd.DatetimeIndex(dates)
        date_index_subset = np.where((date_index>period[0]) & (date_index<period[1]))
        
        # create float representation of dates for output array
        dates = date_index[date_index_subset]
        dates_float = [date.year + np.round(date.dayofyear/365, 3)for date in dates]
        
        # create 
        params = {
                'nr_bootstraps': bstraps,
                'date_index_subset': date_index_subset, 
                'dates_float': dates_float,
                'threshold_area': area_thld,
                'threshold_change_confidence': conf_thld
                }

        # fill in lists for processing
        for sub_stack in sub_stack_files:
            outname = Path(sub_stack).parent.stem
            outfile = outdir.joinpath(f'{tile}_{outname}.tiff')
            args_list.append([sub_stack, outfile, params])
            outfiles.append(str(outfile))

    
    out.add_live_msg('Processing in parallel.')
    # parallel execution
    with concurrent.futures.ThreadPoolExecutor(
            max_workers=os.cpu_count()
        ) as executor:
            executor.map(main, args_list)
    #for args in args_list:
        
    #    main(args)
        
    out.add_live_msg('Merging tiles to final result file.')
    # merge tiles as vrt 
    tmpvrt = outdir.joinpath('merged_tiles.vrt')
    opts = gdal.BuildVRTOptions(srcNodata=0, VRTNodata=0)
    vrt = gdal.BuildVRT(str(tmpvrt), outfiles, options=opts)
    vrt.FlushCache()

    # merge tiles as vrt 
    #tmpvrt = outdir.joinpath('merged_tiles.vrt')
    #cmd = f'gdalbuildvrt -srcnodata 0 {str(tmpvrt)} {" ".join(outfiles)}'
    #os.system(cmd)

    # and translate to a single geotiff
    with rio.open(tmpvrt) as src:

        meta = src.meta
        meta.update(driver='GTiff')
        
        with rio.open(result_file, 'w', **meta) as dst:
            dst.write(src.read())
            # add band tags and descriptions
            dst.update_tags(1, 'Change date')
            dst.set_band_description(1, 'Change Date')
            dst.update_tags(2, 'Confidence')
            dst.set_band_description(2, 'Confidence')
            dst.update_tags(3, 'Magnitude')
            dst.set_band_description(3, 'Magnitude')

    # remove temporary files
    tmpvrt.unlink()
    for file in outfiles:
        Path(file).unlink()


def write_logs(log_file, start, end):

    with log_file.open('w') as f: 
        f.write("Computation finished!\n")
        f.write("\n")
        f.write(f"Computation started on: {start} \n")
        f.write(f"Computation finished on: {end}\n")
        f.write("\n")
        f.write(f"Elapsed time: {end-start}")

    return




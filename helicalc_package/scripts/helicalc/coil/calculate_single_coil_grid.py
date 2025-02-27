import sys
from time import time
from datetime import datetime
import numpy as np
import pandas as pd
import argparse
from tqdm import tqdm
from helicalc import helicalc_dir, helicalc_data
from helicalc.coil import CoilIntegrator
from helicalc.geometry import read_solenoid_geom_combined
from helicalc.tools import (
    generate_cartesian_grid_df,
    generate_cylindrical_grid_df,
    add_points_for_J
)
from helicalc.constants import dxyz_dict, TSd_grid, DS_grid, DS_FMS_cyl_grid, DS_FMS_cyl_grid_SP, DS_cyl_grid_fine, DSCartVal_grid

# data
datadir = helicalc_data+'Bmaps/helicalc_partial/'

# load coils
paramdir = helicalc_dir + 'dev/params/'
paramname = 'Mu2e_V13'
#paramname = 'Mu2e_V13_altDS11'

geom_df = read_solenoid_geom_combined(paramdir,paramname).iloc[55:].copy()
# load chunk data
chunk_file = helicalc_data+'Bmaps/aux/batch_N_helicalc_03-16-22.txt'
df_chunks = pd.read_csv(chunk_file)

regions = {'TSd': TSd_grid, 'DS': DS_grid, 'DSCylFMS': DS_FMS_cyl_grid,
           'DSCylFMSAll': [DS_FMS_cyl_grid, DS_FMS_cyl_grid_SP], 'DSCylFine': DS_cyl_grid_fine,
           'DSCartVal': DSCartVal_grid}

if __name__=='__main__':
    # parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--Region',
                        help='Which region of Mu2e to calculate? '+
                        '["DS"(default), "TSd", "DSCylFMS", "DSCylFMSAll", "DSCylFine"]')
    parser.add_argument('-C', '--Coil',
                        help='Coil number [56-66], default is 56 (DS-1).')
    parser.add_argument('-L', '--Layer',
                        help='Coil layer [1 (default), 2,...]. Do not enter layer number > total number of layers in that coil.')
    parser.add_argument('-D', '--Device',
                        help='Which GPU to use? [0 (default), 1, 2, 3].')
    parser.add_argument('-j', '--Jacobian',
                        help='Include points for calculating '+
                        'the Jacobian of the field? "n"(default)/"y"')
    parser.add_argument('-d', '--dxyz_Jacobian',
                        help='What step size (in m) to use for points used in '+
                        'the Jacobian calculation? e.g. "0.001" (default)')
    parser.add_argument('-t', '--Testing',
                        help='Calculate using small subset of field points (N=1000)?'+
                        '"y"/"n"(default). If yes (y), region defaults to DS.')
    parser.add_argument('-i', '--infile', help='pickle file with coordinate grid')
    args = parser.parse_args()
    # fill defaults where needed
    if args.Region is None:
        args.Region = 'DS'
    else:
        args.Region = args.Region.strip()
    reg = args.Region
    if args.Coil is None:
        args.Coil = 56
    else:
        args.Coil = int(args.Coil.strip())
    if args.Layer is None:
        args.Layer = 1
    else:
        args.Layer = int(args.Layer.strip())
    df_coil = geom_df.query(f'Coil_Num=={args.Coil}').iloc[0]
    N_layers = df_coil.N_layers
    if args.Layer > N_layers:
        raise ValueError(f'(Layer={args.Layer}) > (N_layers={N_layers}). Please enter a valid layer.')
    if args.Device is None:
        args.Device = 0
    else:
        args.Device = int(args.Device.strip())
    if args.Jacobian is None:
        args.Jacobian = False
    else:
        if args.Jacobian.strip() == 'y':
            args.Jacobian = True
        else:
            args.Jacobian = False
    if args.dxyz_Jacobian is None:
        args.dxyz_Jacobian = 0.001
    else:
        args.dxyz_Jacobian = float(args.dxyz_Jacobian)
    if args.Testing is None:
        args.Testing = False
    else:
        args.Testing = args.Testing.strip() == 'y'
    # set up base directory/name
    # if args.Testing:
    #     #reg = 'DS'
    #     base_name = f'Bmaps/helicalc_partial/tests/{paramname}.{reg}_region.test-helicalc.'
    # else:
    #     base_name = f'Bmaps/helicalc_partial/{paramname}.{reg}_region.standard-helicalc.'
    # print configs
    print(f'Region: {reg}')
    # redirect stdout to log file
    dt = datetime.strftime(datetime.now(), '%Y-%m-%d_%H%M%S')
    log_file = open(datadir+f"logs/{dt}_calculate_{reg}_region.log", "w")
    old_stdout = sys.stdout
    sys.stdout = log_file
    # find correct chunk size
    N_calc = df_chunks.query(f'Nt_Ri == {df_coil.Nt_Ri}').iloc[0].N_field_points
    # create grid
    if reg in ['DSCylFMS', 'DSCylFMSAll', 'DSCylFine']:
        df = generate_cylindrical_grid_df(regions[reg], dec_round=9)
    elif 'Unc' in reg:
        if args.infile is None:
            print("For Unc type region, provide pickle with shifted measurement grid")
            exit()
        df = pd.read_pickle(args.infile)
        df = df[['X','Y','Z','HP']]
    else:
        df = generate_cartesian_grid_df(regions[reg])
    if args.Testing:
        df = df.iloc[:1000].copy()
    # add extra points for Jacobian?
    if args.Jacobian:
        df = add_points_for_J(df, dxyz=args.dxyz_Jacobian)
        suff = '_Jacobian'
    else:
        suff = ''
    if args.Testing:
        #reg = 'DS'
        base_name = f'Bmaps/helicalc_partial/tests/{paramname}.{reg}_region.test-helicalc{suff}.'
    else:
        base_name = f'Bmaps/helicalc_partial/{paramname}.{reg}_region.standard-helicalc{suff}.'
    # initialize coil
    myCoil = CoilIntegrator(df_coil, dxyz=dxyz_dict[df_coil.dxyz],
                            layer=args.Layer, dev=args.Device,
                            interlayer_connect=True)
    # integrate!
    myCoil.integrate_grid(df, N_batch=N_calc, tqdm=tqdm)
    #myCoil.integrate_grid(df_, N_batch=N_calc, tqdm=tqdm)
    # save!
    myCoil.save_grid_calc(savetype='pkl', savename=base_name+
                          f'coil_{args.Coil}_layer_{args.Layer}',
                          all_helicalc_cols=False)

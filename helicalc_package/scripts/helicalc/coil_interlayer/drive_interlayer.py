import subprocess
import argparse
from math import ceil
from helicalc.constants import dxyz_arc_bar_dict, TSd_grid, DS_grid
from helicalc.solenoid_geom_funcs import load_all_geoms

# load straight bus bars, dump all other geometries
paramname = 'Mu2e_V13'
version = paramname.replace('Mu2e_V', '')
df_dict = load_all_geoms(version=version, return_dict=True)
df_interlayer = df_dict['interlayers']
N_cond = len(df_interlayer)
# last GPU will get any extra conductors
N_cond_per_GPU = ceil(N_cond / 4)

# evenly split, with remaining bars to GPU 3
interlayer_GPU_dict = {0: range(0, N_cond_per_GPU),
                       1: range(N_cond_per_GPU, 2*N_cond_per_GPU),
                       2: range(2*N_cond_per_GPU, 3*N_cond_per_GPU),
                       3: range(3*N_cond_per_GPU, N_cond)}

if __name__=='__main__':
    # parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--Region',
                        help='Which region of Mu2e to calculate? '+
                        '["DS"(default), "TSd", "DSCylFMS", "DSCylFMSAll"]')
    parser.add_argument('-D', '--Device',
                        help='Which GPU (i.e. which coils/layers) to use? '+
                        '[0 (default), 1, 2, 3].')
    parser.add_argument('-j', '--Jacobian',
                        help='Include points for calculating '+
                        'the Jacobian of the field? "n"(default)/"y"')
    parser.add_argument('-d', '--dxyz_Jacobian',
                        help='What step size (in m) to use for points used in '+
                        'the Jacobian calculation? e.g. "0.001" (default)')
    parser.add_argument('-t', '--Testing',
                        help='Calculate using small subset of field points '+
                        '(N=100000)? "y"/"n"(default).')
    parser.add_argument('-i', '--infile', help='pickle file with coordinate grid')
    args = parser.parse_args()
    # fill defaults if necessary
    if args.Region is None:
        args.Region = 'DS'
    else:
        args.Region = args.Region.strip()
    reg = args.Region
    if args.Device is None:
        args.Device = 0
    else:
        args.Device = int(args.Device.strip())
    Dev = args.Device
    if args.Jacobian is None:
        args.Jacobian = 'n'
    else:
        args.Jacobian = args.Jacobian.strip()
    Jac = args.Jacobian
    if args.dxyz_Jacobian is None:
        args.dxyz_Jacobian = '0.001'
    else:
        args.dxyz_Jacobian = args.dxyz_Jacobian.strip()
    dxyz = args.dxyz_Jacobian
    if args.Testing is None:
        args.Testing = 'n'
    else:
        args.Testing = args.Testing.strip()
    Test = args.Testing

    print(f'Running on GPU: {Dev}')
    for i in interlayer_GPU_dict[Dev]:
        df_cn = df_interlayer.iloc[i]
        # not sure why int conversion is necessary here
        cn = int(df_cn['cond N'])
        append = '' if args.infile is None else f' -i {args.infile}'
        print(f'Calculating {i}: cond N (i.e. Coil_Num)={cn}')
        _ = subprocess.run(f'python calculate_single_interlayer_grid.py'+
                           f' -r {reg} -C {cn} -D {Dev} -j {Jac} -d {dxyz} -t {Test}'+append, shell=True,
                           capture_output=False)

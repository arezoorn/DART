import argparse
import datetime
import f90nml
import multiprocessing
import os
import pathlib
import pickle
import shlex
import subprocess
import sys

from wrfhydropy.core.ensemble_tools import mute
from hydrodartpy.core.setup_experiment_tools import establish_config, get_top_level_dir_from_config

def parallel_process_day(arg_dict):

    # arg_dict = {
    #     the_date: datetime.datetime
    #     link_files_list: list
    #     input_dir: pathlib.Path,
    #     output_dir: pathlib.Path,
    #     the_converter: pathlib.Path
    #     exe_cmd: str
    # }

    the_date = arg_dict['the_date']
    link_files_list = arg_dict['link_files_list']
    input_dir = arg_dict['input_dir']
    output_dir = arg_dict['output_dir']
    the_converter = arg_dict['the_converter']
    exe_cmd = arg_dict['exe_cmd']

    print("Converting obs for date: ", the_date)

    # Every day creates files in its own dir.
    datedir = output_dir / the_date.strftime('day_proc.%Y%m%d')

    os.mkdir(datedir)
    os.chdir(datedir)

    # Symlink these files into the datedir.
    for file in link_files_list:
        local_file = datedir / file.name
        local_file.symlink_to(file)

    obs_files = sorted(input_dir.glob(the_date.strftime('%Y%m%d.nc')))

    with open('list_of_obs_files.txt', 'w') as f:
        for file in obs_files:
            _ = f.write("%s\n" % file)

    the_cmd = exe_cmd.format(
        **{
            'cmd': './' + the_converter.name,
            'nproc': 1
        }
    )
    proc = subprocess.run(shlex.split(the_cmd))

    if proc.returncode != 0:
        return proc.returncode

    the_obs_seq = pathlib.Path(datedir) / the_date.strftime('obs_seq.%Y%m%d')
    pathlib.Path('obs_seq.out').rename(the_obs_seq)

    os.chdir(output_dir)

    pathlib.Path(the_obs_seq.name).symlink_to(the_obs_seq)

    return 0


def create_nysm_snow_daily_obs_seq(config):

    # Global information...

    input_dir = config['observation_preparation']['NYSM_snow_daily']['input_dir']
    output_dir = config['observation_preparation']['NYSM_snow_daily']['output_dir']

    end_day = config['observation_preparation']['NYSM_snow_daily']['end_date']
    start_day = config['observation_preparation']['NYSM_snow_daily']['start_date']
    delta = end_day - start_day
    dates_all = [start_day + datetime.timedelta(days=dd) for dd in range(delta.days+1)]

    exp_dir = config['experiment']['experiment_dir']
    dart_build_dir = config['dart']['build_dir']
    dart_compile = pickle.load(open(exp_dir / dart_build_dir / 'DartCompile.pkl', 'rb'))

    run_dir = config['experiment']['run_dir']

    # Get some fields from the input.nml
    input_nml_file = output_dir / 'input.nml'
    input_nml = f90nml.read(input_nml_file)
#    gages_list_file = output_dir / input_nml['create_identity_nysm_snow_obs_nml']['gages_list_file']
#    link_files_list = [input_nml_file, hydro_nlst, gages_list_file]
    link_files_list = [input_nml_file]

    # Identify obs or not...
    if config['observation_preparation']['NYSM_snow_daily']['identity_obs']:
        print('AT THIS TINE IDENTITY OBS IS NOT SUPPORTED')

    else:

        converter = dart_compile.observations__obs_converters__NYSM__work.exes['convert_NYSM_snow']
        link_files_list = link_files_list + [converter]

    # Transform these to the output_dir location.
    link_files_list = [output_dir / pathlib.Path(file).name for file in link_files_list]
    the_converter = output_dir / pathlib.Path(converter)

    exe_cmd = config['observation_preparation']['NYSM_snow_daily']['exe_cmd']
    ncores = config['observation_preparation']['NYSM_snow_daily']['scheduler']['mpiprocs']

    if ncores > 1:

        with multiprocessing.Pool(processes=ncores, initializer=mute) as pool:
            exit_codes = pool.map(
                parallel_process_day,
                (
                    {
                        'the_date': the_date,
                        'link_files_list': link_files_list,
                        'input_dir': input_dir,
                        'output_dir': output_dir,
                        'the_converter': the_converter,
                        'exe_cmd': exe_cmd
                    } for the_date in dates_all
                )
            )

    else:
        # Keep the following for debugging: Run it without pool.map
        exit_codes = [
            parallel_process_day(
                {
                    'the_date': the_date,
                    'link_files_list': link_files_list,
                    'input_dir': input_dir,
                    'output_dir': output_dir,
                    'the_converter': the_converter,
                    'exe_cmd': exe_cmd
                }
            ) for the_date in dates_all
        ]

    # Not translates logical to system return code
    return int(not all([ee == 0 for ee in exit_codes]))


if __name__ == "__main__":

    # Arguments to this script.
    # python setup_experiment.py --help
    the_desc = "Convert WRF-Hydro-DART observations in parallel."
    the_epilog = """
    Additional Examples:
    regular: python create_nysm_snow_daily_obs_seq.py obs_config_files/test_obs.yaml
    debug:  ipython --pdb -c "%run create_nysm_snow_daily_obs_seq.py obs_config_files/test_obs.yaml"
    """
    parser = argparse.ArgumentParser(
        description=the_desc,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=the_epilog
    )

    # Single positional argument is config_file
    parser.add_argument(
        '--config_file',
        metavar='config_file.yaml',
        default=pathlib.Path('config_file.yaml'),
        help='The YAML experiment configuration file of arbitrary name.'
    )
    args = parser.parse_args()

    config_file=args.config_file
    if config_file is list:
        config_file = config_file[0]

    config = establish_config(config_file)
    return_code = create_nysm_snow_daily_obs_seq(config)

    sys.exit(return_code)

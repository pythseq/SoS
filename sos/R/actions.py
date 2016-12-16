#!/usr/bin/env python3
#
# This file is part of Script of Scripts (sos), a workflow system
# for the execution of commands and scripts in different languages.
# Please visit https://github.com/bpeng2000/SOS
#
# Copyright (C) 2016 Bo Peng (bpeng@mdanderson.org)
##
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
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import os
import sys
import subprocess
import shutil
import tempfile
from collections.abc import Sequence

from sos.actions import SoS_Action, SoS_ExecuteScript
from sos.utils import env
from sos.sos_eval import interpolate


@SoS_Action(run_mode=['prepare', 'run', 'interactive'])
def R(script, args='', **kwargs):
    # > getOption('defaultPackages')
    # [1] "datasets"  "utils"     "grDevices" "graphics"  "stats"     "methods"
    return SoS_ExecuteScript(
        script, 'Rscript --default-packages=datasets,methods,utils,stats,grDevices,graphics ', '.R', args).run(**kwargs)

@SoS_Action(run_mode=['run', 'interactive'])
def Rmarkdown(script=None, input=None, output=None, args='${input!r}, output_file=${output!ar}', **kwargs):
    '''Convert input file to output using Rmarkdown

    The input can be specified in three ways:
    
    1. instant script, which is assumed to be in md format

    Rmarkdown:   output='report.html'
      script

    2. one or more input files. The format is determined by extension of input file

    Rmarkdown(input, output='report.html')

    3. input file specified by command line option `-r` .
    Rmarkdown(output='report.html')

    If no output is specified, it is assumed to be in html format
    and is written to standard output.
    
    You can specify more options using the args parameter of the action. The default value
    of args is `${input!r} --output ${output!ar}'
    '''
    if input is not None:
        if isinstance(input, str):
            input_file = input
        elif isinstance(input, Sequence):
            if len(input) == 0:
                return
            input_file = tempfile.NamedTemporaryFile(mode='w+t', suffix=os.path.splitext(input[0])[-1], delete=False).name
            with open(input_file, 'w') as tmp:
                for ifile in input:
                    try:
                        with open(ifile) as itmp:
                            tmp.write(itmp.read())
                    except Exception as e:
                        raise ValueError('Failed to read input file {}: {}'.format(ifile, e))
    elif isinstance(script, str) and script.strip():
        input_file = tempfile.NamedTemporaryFile(mode='w+t', suffix='.md', delete=False).name
        with open(input_file, 'w') as tmp:
            tmp.write(script)
    elif '__report_output__' in env.sos_dict:
        input_file = interpolate(env.sos_dict['__report_output__'], '${ }')
    else:
        raise ValueError('Unknown input file for acion Rmarkdown')
        
    write_to_stdout = False
    if output is None:
        write_to_stdout = True
        output_file = tempfile.NamedTemporaryFile(mode='w+t', suffix='.html', delete=False).name
    elif isinstance(output, str):
        output_file = output
    else:
        raise RuntimeError('A filename is expected, {} provided'.format(output))
    #
    ret = 1
    try:
        #   render(input, output_format = NULL, output_file = NULL, output_dir = NULL,
        #        output_options = NULL, intermediates_dir = NULL,
        #        runtime = c("auto", "static", "shiny"),
        #        clean = TRUE, params = NULL, knit_meta = NULL, envir = parent.frame(),
        #        run_Rmarkdown = TRUE, quiet = FALSE, encoding = getOption("encoding"))
        cmd = interpolate('Rscript -e "rmarkdown::render({})"'.format(args), '${ }',
            {'input': input_file, 'output': output_file})
        env.logger.trace('Running command "{}"'.format(cmd))
        if env.run_mode == 'interactive':
            # need to catch output and send to python output, which will in trun be hijacked by SoS notebook
            p = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            pid = p.pid
            env.register_process(p.pid, 'Runing {}'.format(input_file))
            out, err = p.communicate()
            sys.stdout.write(out.decode())
            sys.stderr.write(err.decode())
            ret = p.returncode
        else:
            p = subprocess.Popen(cmd, shell=True)
            pid = p.pid
            env.register_process(pid, 'Runing {}'.format(input_file))
            ret = p.wait()
    except Exception as e:
        env.logger.error(e)
    finally:
        env.deregister_process(p.pid)
    if ret != 0:
        temp_file = os.path.join('.sos', '{}_{}.md'.format('Rmarkdown', os.getpid()))
        shutil.copyfile(input_file, temp_file)
        cmd = interpolate('Rscript -e "rmarkdown::render({})"'.format(args), '${ }',
            {'input': input_file, 'output': output_file})
        raise RuntimeError('Failed to execute script. The script is saved to {}. Please use command "{}" to test it.'
            .format(temp_file, cmd))
    if write_to_stdout:
        with open(output_file) as out:
            sys.stdout.write(out.read())
    else:
        env.logger.info('Report saved to {}'.format(output_file))



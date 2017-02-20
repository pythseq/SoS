#!/usr/bin/env python3
#
# This file is part of Script of Scripts (SoS), a workflow system
# for the execution of commands and scripts in different languages.
# Please visit https://github.com/vatlab/SOS for more information.
#
# Copyright (C) 2016 Bo Peng (bpeng@mdanderson.org)
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
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import os
import time
import unittest
import shutil

from sos.sos_script import SoS_Script
from sos.utils import env
from sos.sos_executor import Base_Executor, MP_Executor
from sos.target import FileTarget
import subprocess

class TestExecute(unittest.TestCase):
    def setUp(self):
        env.reset()
        subprocess.call('sos remove -s', shell=True)
        #self.resetDir('~/.sos')
        self.temp_files = []

    def tearDown(self):
        for f in self.temp_files:
            FileTarget(f).remove('both')

    def touch(self, files):
        '''create temporary files'''
        if isinstance(files, str):
            files = [files]
        #
        for f in files:
            with open(f, 'w') as tmp:
                tmp.write('test')
        #
        self.temp_files.extend(files)

    def resetDir(self, dirname):
        if os.path.isdir(os.path.expanduser(dirname)):
            shutil.rmtree(os.path.expanduser(dirname))
        os.mkdir(os.path.expanduser(dirname))


    def testSignature(self):
        self._testSignature(r"""
import time
[*_0]
output: 'temp/a.txt', 'temp/b.txt'
task:
if run_mode == 'run':
   time.sleep(1)
   run('''echo "a.txt" > 'temp/a.txt' ''')
   run('''echo "b.txt" > 'temp/b.txt' ''')

[1: shared={'oa':'output'}]
dest = ['temp/c.txt', 'temp/d.txt']
input: group_by='single', paired_with='dest'
output: _dest

task:
if run_mode == 'run':
    time.sleep(0.5)
    run(" cp ${_input} ${_dest} ")
""")
        #
        env.max_jobs = 4
        self._testSignature(r"""
import time
[*_0]
output: 'temp/a.txt', 'temp/b.txt'

task:
if run_mode == 'run':
    time.sleep(1)
    run('''echo "a.txt" > 'temp/a.txt' ''')
    run('''echo "b.txt" > 'temp/b.txt' ''')

[1: shared={'oa':'output'}]
dest = ['temp/c.txt', 'temp/d.txt']
input: group_by='single', paired_with='dest'
output: _dest

task:
if run_mode == 'run':
   time.sleep(0.5)
   run(" cp ${_input} ${_dest} ")
""")
        # script format
        env.max_jobs = 4
        self._testSignature(r"""
import time
[*_0]
output: 'temp/a.txt', 'temp/b.txt'

run:
sleep 1
echo "a.txt" > 'temp/a.txt'

run:

echo "b.txt" > 'temp/b.txt'

[1: shared={'oa':'output'}]
dest = ['temp/c.txt', 'temp/d.txt']
input: group_by='single', paired_with='dest'
output: _dest

task:
if run_mode == 'run':
    time.sleep(0.5)
run:
cp ${_input} ${_dest}
""")
        # reset env mode
        env.sig_mode = 'default'
        shutil.rmtree('temp')

    def testSignatureWithSharedVariable(self):
        '''Test restoration of signature from variables.'''
        FileTarget('a.txt').remove('both')
        # shared 
        script = SoS_Script(r"""
import time
[0: shared='a']
output: 'a.txt'
run:
   sleep 3
   touch a.txt

a= 5

[1]
print(a)

""")
        # alias should also be recovered.
        wf = script.workflow('default')
        st = time.time()
        Base_Executor(wf).run()
        self.assertGreater(time.time() - st, 3)
        # rerun
        st = time.time()
        Base_Executor(wf).run()
        self.assertLess(time.time() - st, 1)
        FileTarget('a.txt').remove('both')

    def testSignatureWithoutOutput(self):
        # signature without output file
        self._testSignature(r"""
import time
[*_0]
output: []

run:
sleep 1
[ -d temp ] || mkdir temp
echo "a.txt" > 'temp/a.txt'

run:

echo "b.txt" > 'temp/b.txt'

[1: shared={'oa':'output'}]
dest = ['temp/c.txt', 'temp/d.txt']
input: 'temp/a.txt', 'temp/b.txt', group_by='single', paired_with='dest'
output: _dest

run:
sleep 0.5
cp ${_input} ${_dest}
""")
        # reset env mode
        env.sig_mode = 'default'
        shutil.rmtree('temp')

    def _testSignature(self, text):
        '''Test recognizing the format of SoS script'''
        script = SoS_Script(text)
        for f in ['temp/a.txt', 'temp/b.txt']:
            FileTarget(f).remove('both')
        #
        # only the first step
        wf = script.workflow('default:0')
        start = time.time()
        env.sig_mode = 'force'
        if env.max_jobs == 1:
            Base_Executor(wf).run()
        else:
            MP_Executor(wf).run()
        self.assertGreater(time.time() - start, 1)
        self.assertTrue(os.path.isfile('temp/a.txt'))
        self.assertTrue(os.path.isfile('temp/b.txt'))
        with open('temp/a.txt') as ta:
            self.assertTrue(ta.read(), 'a.txt')
        with open('temp/b.txt') as tb:
            self.assertTrue(tb.read(), 'b.txt')
        env.sig_mode = 'assert'
        if env.max_jobs == 1:
            Base_Executor(wf).run()
        else:
            MP_Executor(wf).run()
        #
        wf = script.workflow()
        start = time.time()
        env.sig_mode = 'build'
        if env.max_jobs == 1:
            Base_Executor(wf).run()
        else:
            MP_Executor(wf).run()

        self.assertLess(time.time() - start, 1.5)
        #
        self.assertTrue(os.path.isfile('temp/c.txt'))
        self.assertTrue(os.path.isfile('temp/d.txt'))
        with open('temp/c.txt') as tc:
            self.assertTrue(tc.read(), 'a.txt')
        with open('temp/d.txt') as td:
            self.assertTrue(td.read(), 'b.txt')
        self.assertEqual(env.sos_dict['oa'], ['temp/c.txt', 'temp/d.txt'])
        #
        # now in assert mode, the signature should be there
        env.sig_mode = 'assert'
        if env.max_jobs == 1:
            Base_Executor(wf).run()
        else:
            MP_Executor(wf).run()

        #
        start = time.time()
        env.sig_mode = 'default'
        if env.max_jobs == 1:
            Base_Executor(wf).run()
        else:
            MP_Executor(wf).run()
        
        self.assertLess(time.time() - start, 1.5)
        #
        # change script a little bit
        script = SoS_Script('# comment\n' + text)
        wf = script.workflow()
        env.sig_mode = 'assert'
        if env.max_jobs == 1:
            Base_Executor(wf).run()
        else:
            MP_Executor(wf).run()

        # add some other variable?
        #script = SoS_Script('comment = 1\n' + text)
        #wf = script.workflow()
        #env.sig_mode = 'assert'
        #self.assertRaises(ExecuteError, Base_Executor(wf).run)

    def testReexecution(self):
        '''Test -f option of sos run'''
        script = SoS_Script('''
import time

[0]
output: 'a.txt'
task:
time.sleep(3)
run("touch ${output}")
''')
        wf = script.workflow()
        try:
            # remove existing output if exists
            FileTarget('a.txt').remove('both')
        except:
            pass
        start = time.time()
        Base_Executor(wf).run()
        # regularly take more than 5 seconds to execute
        self.assertGreater(time.time() - start, 2)
        # now, rerun should be much faster
        start = time.time()
        Base_Executor(wf).run()
        # rerun takes less than 1 second
        self.assertLess(time.time() - start, 1)
        #
        # force rerun mode
        start = time.time()
        env.sig_mode = 'ignore'
        Base_Executor(wf).run()
        # regularly take more than 5 seconds to execute
        self.assertGreater(time.time() - start, 2)
        try:
            # remove existing output if exists
            os.remove('a.txt')
        except:
            pass

    def testSignatureAfterRemovalOfFiles(self):
        '''test action shrink'''
        if os.path.isfile('largefile.txt'):
            os.remove('largefile.txt')
        script = SoS_Script(r'''
[10]

# generate a file
output: 'largefile.txt'

python:
    import time
    time.sleep(3)
    with open("${output}", 'w') as out:
        for i in range(1000):
            out.write('{}\n'.format(i))

''')
        wf = script.workflow()
        st = time.time()
        Base_Executor(wf).run()
        self.assertGreater(time.time() - st, 3)
        # rerun, because this is the final target, it has to be
        # re-generated
        os.remove('largefile.txt')
        st = time.time()
        Base_Executor(wf).run()
        self.assertGreater(time.time() - st, 3)
        # 
        self.assertTrue(os.path.isfile('largefile.txt'))
        # we discard just the signature, the step will be ignored
        # as long as the file is not touched.
        st = time.time()
        FileTarget('largefile.txt').remove('signature')
        Base_Executor(wf).run()
        self.assertLess(time.time() - st, 0.5)
        #
        # now if we touch the file, it needs to be regenerated
        st = time.time()
        with open('largefile.txt', 'a') as lf:
            lf.write('something')
        Base_Executor(wf).run()
        self.assertGreater(time.time() - st, 3)
        FileTarget('largefile.txt').remove('both')

    def testSignatureWithParameter(self):
        '''Test signature'''
        FileTarget('myfile.txt').remove('both')
        #
        script = SoS_Script(r'''
parameter: gvar = 10

[10]
# generate a file
output: 'myfile.txt'
# additional comment
python:
    import time
    time.sleep(3)
    with open(${output!r}, 'w') as tmp:
        tmp.write('${gvar}')

''')
        st = time.time()
        wf = script.workflow()
        Base_Executor(wf).run()
        self.assertGreater(time.time() - st, 2.5)
        with open('myfile.txt') as tmp:
            self.assertEqual(tmp.read(), '10')
        #
        # now if we change parameter, the step should be rerun
        st = time.time()
        wf = script.workflow()
        Base_Executor(wf, args=['--gvar', '20']).run()
        with open('myfile.txt') as tmp:
            self.assertEqual(tmp.read(), '20')
        self.assertGreater(time.time() - st, 2.5)
        #
        # do it again, signature should be effective
        st = time.time()
        wf = script.workflow()
        Base_Executor(wf, args=['--gvar', '20']).run()
        with open('myfile.txt') as tmp:
            self.assertEqual(tmp.read(), '20')
        self.assertLess(time.time() - st, 2.5)

        #
        script = SoS_Script(r'''
parameter: gvar = 10

[10]
# generate a file
output: 'myfile.txt'
# additional comment
task:
python:
    import time
    time.sleep(3)
    with open(${output!r}, 'w') as tmp:
        tmp.write('${gvar}')

''')
        st = time.time()
        wf = script.workflow()
        Base_Executor(wf).run()
        self.assertGreater(time.time() - st, 2.5)
        with open('myfile.txt') as tmp:
            self.assertEqual(tmp.read(), '10')
        #
        # now if we change parameter, the step should be rerun
        st = time.time()
        wf = script.workflow()
        Base_Executor(wf, args=['--gvar', '20']).run()
        with open('myfile.txt') as tmp:
            self.assertEqual(tmp.read(), '20')
        self.assertGreater(time.time() - st, 2.5)
        #
        # do it again, signature should be effective
        st = time.time()
        wf = script.workflow()
        Base_Executor(wf, args=['--gvar', '20']).run()
        with open('myfile.txt') as tmp:
            self.assertEqual(tmp.read(), '20')
        self.assertLess(time.time() - st, 2.5)
        FileTarget('myfile.txt').remove('both')



    def testLoopWiseSignature(self):
        '''Test partial signature'''
        for i in range(10, 12):
            FileTarget('myfile_{}.txt'.format(i)).remove('both')
        #
        script = SoS_Script(r'''
parameter: gvar = 10

[10]
tt = [gvar]
input: for_each='tt'
output: "myfile_${_tt}.txt"
python:
    import time
    time.sleep(3)
    print("DO ${_tt}")
    with open(${_output!r}, 'w') as tmp:
        tmp.write('${_tt}')
''')
        st = time.time()
        wf = script.workflow()
        Base_Executor(wf).run()
        self.assertGreater(time.time() - st, 2.5)
        # now we modify the script 
        script = SoS_Script(r'''
parameter: gvar = 10

[10]
tt = [gvar, gvar + 1]
input: for_each='tt'
output: "myfile_${_tt}.txt"
python:
    import time
    time.sleep(3)
    print("DO ${_tt}")
    with open(${_output!r}, 'w') as tmp:
        tmp.write('${_tt}')
''')
        st = time.time()
        wf = script.workflow()
        Base_Executor(wf).run()
        self.assertGreater(time.time() - st, 2.5)
        self.assertLess(time.time() - st, 5)
        #
        # run it again, neither needs to be rerun
        st = time.time()
        Base_Executor(wf).run()
        self.assertLess(time.time() - st, 2)
        #
        # change again, the second one is already there.
        script = SoS_Script(r'''
parameter: gvar = 10

[10]
tt = [gvar + 1]
input: for_each='tt'
output: "myfile_${_tt}.txt"
python:
    import time
    time.sleep(3)
    print("DO ${_tt}")
    with open(${_output!r}, 'w') as tmp:
        tmp.write('${_tt}')
''')
        st = time.time()
        wf = script.workflow()
        Base_Executor(wf).run()
        self.assertLess(time.time() - st, 2)
        #
        for t in range(10, 12):
            with open('myfile_{}.txt'.format(t)) as tmp:
                self.assertEqual(tmp.read(), str(t))
            FileTarget('myfile_{}.txt'.format(t)).remove('both')



    def testOutputFromSignature(self):
        'Test restoration of output from signature'''
        self.touch(['1.txt', '2.txt'])
        script = SoS_Script('''
parameter: K = [2,3]

[work_1]
input: "1.txt", "2.txt", group_by = 'single', pattern = '{name}.{ext}'
output: expand_pattern('{_name}.out')
run:
  touch ${_output}

[work_2]

input: group_by = 'single', pattern = '{name}.{ext}', paired_with = ['K']
output: expand_pattern('{_name}.{_K}.out')
run: 
  touch ${_output}
    ''')
        wf = script.workflow()
        Base_Executor(wf).run()
        # for the second run, output should be correctly constructed
        Base_Executor(wf).run()
        for file in ['1.out', '2.out', '1.2.out', '2.3.out']:
            FileTarget(file).remove('both')



    def testReexecutionOfAuxiliaryStep(self):
        '''Test re-execution of auxiliary step if the step has been changed.'''
        script = SoS_Script('''
[process: provides='a.txt']
sh:
    echo 'a.txt' > a.txt

[default]
depends: 'a.txt'
output: 'a.txt.bak'
sh:
    cp a.txt ${output}
''')
        wf = script.workflow()
        #
        Base_Executor(wf).run()
        for f in ['a.txt', 'a.txt.bak']:
            self.assertTrue(FileTarget(f).exists())
            with open(f) as ifile:
                self.assertEqual(ifile.read(), 'a.txt\n')
        # now let us change how a.txt should be generated
        script = SoS_Script('''
[process: provides='a.txt']
sh:
    echo 'aa.txt' > a.txt

[default]
depends: 'a.txt'
output: 'a.txt.bak'
sh:
    cp a.txt ${output}
''')
        wf = script.workflow()
        #
        Base_Executor(wf).run()
        for f in ['a.txt', 'a.txt.bak']:
            self.assertTrue(FileTarget(f).exists())
            with open(f) as ifile:
                self.assertEqual(ifile.read(), 'aa.txt\n')


    def testSignatureWithVars(self):
        '''Test revaluation with variable change'''
        self.touch(('a1.out', 'a2.out'))
        st = time.time()
        script = SoS_Script('''
parameter: DB = {'input': ['a1.out'], 'output': ['b2.out']}
parameter: input_file = DB['input']
parameter: output_file =  DB['output']

[2]
input: input_file, group_by = 1 
output: output_file[_index]
run:
  sleep 2
  touch ${_output}
  ''')
        wf = script.workflow()
        Base_Executor(wf).run()
        self.assertGreater(time.time() - st, 2)
        #
        st = time.time()
        script = SoS_Script('''
parameter: DB = {'input': ['a1.out', 'a2.out'], 'output': ['b2.out', 'b1.out']}
parameter: input_file = DB['input']
parameter: output_file =  DB['output']

[2]
input: input_file, group_by = 1
output: output_file[_index]
run:
  sleep 2
  touch ${_output}
  ''')
        wf = script.workflow()
        Base_Executor(wf).run()
        self.assertLess(time.time() - st, 4)
        self.assertGreater(time.time() - st, 2)

if __name__ == '__main__':
    unittest.main()
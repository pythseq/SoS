#!/usr/bin/env python
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
import unittest
import shutil

from sos.parser import SoS_Script
from sos.utils import env
from sos.workflow_executor import Base_Executor
from sos.targets import file_target


class TestActions(unittest.TestCase):
    def setUp(self):
        env.reset()
        self.temp_files = []

    def tearDown(self):
        for f in self.temp_files:
            file_target(f).remove('both')


    @unittest.skipIf(not shutil.which('julia'), "julia not available")
    def testJulia(self):
        '''Test action Julia'''
        if os.path.isfile('julia_example.txt'):
            os.remove('julia_example.txt')
        script = SoS_Script(r'''
[0]
julia:
    open("julia_example.txt", "w") do f
        write(f, "A, B, C, D\n")
     end
''')
        wf = script.workflow()
        Base_Executor(wf).run()
        self.assertTrue(os.path.isfile('julia_example.txt'))


if __name__ == '__main__':
    unittest.main()


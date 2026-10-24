# Third-party notices

## Wind turbine power curves

`src/resize_energy/data/turbines.json` is derived from the **NREL turbine-models** archive
(onshore and distributed wind turbines, power curves and key data):
<https://github.com/NREL/turbine-models>, DOI 10.11578/dc.20210112.1.
It is redistributed under the BSD 3-Clause License reproduced below. Most curves are
"theoretical" (manufacturer or model based); the names of manufacturers and models are used
only to identify the data. The conversion script is `tools/build_turbine_library.py`.

BSD 3-Clause License

Copyright (c) 2020, Alliance for Sustainable Energy, LLC
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

## Poppins font

`src/resize_energy/data/fonts/` contains the Poppins typeface (Regular, Medium, Bold),
copyright 2020 The Poppins Project Authors (<https://github.com/itfoundry/Poppins>),
licensed under the SIL Open Font License 1.1. The licence text is in
`src/resize_energy/data/fonts/OFL.txt`.

## DejaVu Sans (Greek letters in formulas)

The outlines of the Greek letters used in the formula pictures
(`src/resize_energy/report/_poppins_widths.py`) come from DejaVu Sans, derived from Bitstream
Vera, which is free to use, copy, modify and distribute (<https://dejavu-fonts.github.io/License.html>).
Copyright (c) 2003 Bitstream, Inc.; DejaVu changes are in the public domain.

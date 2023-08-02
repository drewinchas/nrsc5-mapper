# nrsc5-mapper
"Headless" frontend for nrsc5. It Downloads and assembles maps; based on nrsc5-dui.

To Install and use this tool (in Termux):

1. Install Python:
   
   `pkg install python`
2. Install Dependencies:
   
   `pip install python-dateutil`
   
   `pkg install python-pillow`
3. Get this code:
   
   `git clone https://github.com/drewinchas/nrsc5-mapper.git`

4. Then, run it:

   `python3 ./nrsc5-mapper.py     # This will display help and usage information`

5. To actually run the code (and save downloaded maps to ./maps), run:

   `python3 ./nrsc-mapper.py <frequency> <program>`

   

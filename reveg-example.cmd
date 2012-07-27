@echo off
"%SystemDrive%\Python32\python.exe" reveg-db.py ^
ca "%USERPROFILE%\My Documents\plant lists\Cmn plantlist\PLANT_ca.txt" ^
freqs "%USERPROFILE%\My Documents\evcs\GoldfieldsBrgnlEVCSppFreq.xls.csv" ^
thold 0.3 ^
grid 020 ^
area AX7 ^
evc "Grassy Woodland" ^
evc "Creekline Grassy Woodland" ^
evc "Granitic Hills Woodland" ^
quad "%USERPROFILE%\My Documents\plant lists\viridans\Viridans Faraday NE.CSV" ^
quad "%USERPROFILE%\My Documents\plant lists\viridans\Viridans Faraday NW.CSV" ^
quad "%USERPROFILE%\My Documents\plant lists\viridans\Viridans Faraday SE.CSV" ^
quad "%USERPROFILE%\My Documents\plant lists\viridans\Viridans Faraday SW.CSV"
pause

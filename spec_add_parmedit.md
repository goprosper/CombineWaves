
Preliminaries:

1) Parmedit file is added to control file format:

study_name,study_date,parms_file_name,pip_file_name,parmedit_file_name

2) the parmedit file (column 5 in control file), has the following format:
The parmedit file is a CSV format file.  The first column is parms_question_number.  This is the only column we will need. The row number of the record (1-based) represents the question_number in the survey.

An example can be found at WaveFiles/CJanuary2026_parms.csv.

Note that this file is generally small and kind be easily loaded and kept in memory.

3) Change to interpretation of the parms file: Column 1 is the parms_question_number (not the question_number).

4) Change to the algorithm: the question_number is derived by looking it up from the parmedit file (i.e., the row number where column 1 contains the parms_question_number).



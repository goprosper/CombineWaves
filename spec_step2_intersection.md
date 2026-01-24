
Step2 - Compute Intersection:

Preliminaries:

We will be creating a new file called CommonQuestions. The file is a CSV file with the following layout:

Column 1: common_question_id
Column 2: master_question_text
Column 3: common_answer_ids

The file will contain all and only those questions_ids that are common to all of the appended files generated in the previous step.

For each question_id included, we want to construct a ^-delimited list of the superset of answer_ids for the question_id in each of the appended files. That is, for each appended file, we want to check the answer_ids for that question_id and add them to the common_answer_ids if they are not already present. The common_answer_ids should be sorted in answer_id order.

The master_question_text should be retrieved from the ptdb database referenced previously. It can be obtained by selecting the question_text column from the br_question_master table where study_name = study name from the control file and question id.


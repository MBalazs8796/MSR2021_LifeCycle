import json
import subprocess
import os
import arrow
import csv
import numpy

from tqdm import tqdm

from blamer import clean_checkout
from blame_source import get_status
from blame_source import Data

def main():
    BASEDIR = os.getcwd()

    # store the time difference
    diffs = list()

    # store if the same person fixed the stub, who wrote it
    same_fixer = list()

    # store if the same person wrote the block
    same_auth = list()

    # store if the entire block was written in 1 commit or not
    same_commit = list()

    # how many times does does it happen that multiple possible sources exist
    multiple_fix_counter = 0

    # how many stubs did not make it
    error_counter = 0

    # store the lengths of stubs that include more then 1 line
    lengths = list()

    git_date_format = 'ddd MMM D HH:mm:ss YYYY Z'
    with open('checkpoint.json', 'r') as fp:
        bugData = json.load(fp)

    for bug in tqdm(bugData):
        try:
            repo_name = bug['projectName'].split('.')[-1]

            if len(bug['blameData']) >= 1:
                if len(bug['blameData']) > 1:
                    multiple_fix_counter += 1
                for blameData in set(bug['blameData']):
                    if ' ' in blameData:
                        error_counter += 1
                        os.chdir(BASEDIR)
                        continue
                    try:
                        os.chdir(f'./repos/{repo_name}')
                    except FileNotFoundError:
                        error_counter += 1
                        os.chdir(BASEDIR)
                        continue
                    
                    current_head = subprocess.getoutput('git rev-parse --short HEAD')
                    if not (current_head in blameData or blameData in current_head):
                        clean_checkout(blameData)

                    with open('./'+bug['bugFilePath'], 'r', errors='ignore') as fp:
                        data = fp.read()

                    line_count = data[bug['bugNodeStartChar']:bug['bugNodeStartChar']+bug['bugNodeLength']].count('\n')

                    dLines =  [line.strip() for line in data.split('\n')]

                    lines = dLines[bug['bugLineNum']-1:bug['bugLineNum']+line_count]

                    # store the unique author names
                    authors = set()

                    # store unique hashes
                    source_hash = set()

                    lineNum = bug['bugLineNum']

                    stub_author = ''

                    if len(lines) > 1:
                        lengths.append(len(lines))

                    # check if the stub was fixed by one of the people who interacted with the other parts of the marked block
                    # the stub is identified by the line that has been changed in the given commit
                    for i, line in enumerate(lines):
                        blame = subprocess.check_output(['git', 'blame', bug['bugFilePath'], '-L', str(lineNum+i)+','+str(lineNum+i)]).decode("utf8", 'ignore')
                        current = blame.split(' ')[1]
                        source_hash.add(blame.split(' ')[0])
                        if get_status(Data(
                            project=bug['projectName'].split('.')[1],
                            path=bug['bugFilePath'],
                            blame=[blameData + ' ' + line]
                        ), False).status[0] != 'not_found':
                            stub_author = current
                        else:
                            authors.add(
                                current
                            )
                    # if the stub's author has interacted with other marked lines or there was only 1 line marked, the result is true
                    same_auth.append(stub_author in authors or len(authors) == 0)

                    same_commit.append(len(source_hash)==1)
                    
                    # get the date of the stub's addition and deletion
                    addDate = subprocess.getoutput('git log -n -1 --format=%ad ' + blameData)
                    fixData = subprocess.getoutput('git log -n -1 --format=%ad ' + bug['fixCommitSHA1'])
                    try:
                        # get the author who added the stub and the author who fixed it
                        addAuth = subprocess.check_output(['git', 'log', '-n', '1', '--format=short', blameData]).decode('utf8', 'ignore').split('\n')[1]
                        fixAuth = subprocess.check_output(['git', 'log', '-n', '1', '--format=short', bug['fixCommitSHA1']]).decode('utf8', 'ignore').split('\n')[1]
                        same_fixer.append(addAuth == fixAuth)
                    except subprocess.CalledProcessError:
                        os.chdir(BASEDIR)
                        continue

                    try:
                        diffs.append((arrow.get(fixData, git_date_format).timestamp - arrow.get(addDate, git_date_format).timestamp))
                    except arrow.parser.ParserMatchError:
                        os.chdir(BASEDIR)
                        continue
                    
                    os.chdir(BASEDIR)
            else:
                error_counter += 1
                os.chdir(BASEDIR)
        except Exception:
            os.chdir(BASEDIR)
            continue
    avg_time = arrow.get(numpy.average(diffs)) - arrow.get(0)
    std_time = arrow.get(numpy.std(diffs)) - arrow.get(0)
    med_time = arrow.get(numpy.median(diffs)) - arrow.get(0)
    print(diffs)
    print(same_fixer)
    with open('stub_stats.csv', 'w') as fp:
        field_names = ['statName', 'statVal']
        writer = csv.DictWriter(fp, fieldnames=field_names)

        writer.writeheader()
        writer.writerow({
            'statName' : 'AVG_time',
            'statVal' : avg_time
        })
        writer.writerow({
            'statName' : 'STD_time',
            'statVal' : std_time
        })
        writer.writerow({
            'statName' : 'MED_time',
            'statVal' : med_time
        })
        writer.writerow({
            'statName' : 'Same_fixer_perc',
            'statVal' : print_percent(same_fixer, 'fixer')
        })

        writer.writerow({
            'statName': 'AVG_time_same_fixer',
            'statVal': stats_per_group(diffs, same_fixer, True, numpy.average)
        })
        writer.writerow({
            'statName': 'STD_time_same_fixer',
            'statVal': stats_per_group(diffs, same_fixer, True, numpy.std)
        })
        writer.writerow({
            'statName': 'MED_time_same_fixer',
            'statVal': stats_per_group(diffs, same_fixer, True, numpy.median)
        })
        writer.writerow({
            'statName': 'AVG_time_diff_fixer',
            'statVal': stats_per_group(diffs, same_fixer, False, numpy.average)
        })
        writer.writerow({
            'statName': 'STD_time_diff_fixer',
            'statVal': stats_per_group(diffs, same_fixer, False, numpy.std)
        })
        writer.writerow({
            'statName': 'MED_time_diff_fixer',
            'statVal': stats_per_group(diffs, same_fixer, False, numpy.median)
        })
        
        writer.writerow({
            'statName' : 'Same_auth_perc',
            'statVal' : print_percent(same_auth, 'auth')
        })
        writer.writerow({
            'statName' : 'Same_commmit_perc',
            'statVal' : print_percent(same_commit, 'commit')
        })
        
        writer.writerow({
            'statName' : 'Multi_src',
            'statVal' : multiple_fix_counter
        })
        writer.writerow({
            'statName' : 'Error_num',
            'statVal' : error_counter
        })
        
        writer.writerow({
            'statName' : 'AVG_stub_len',
            'statVal' : sum(lengths) / len(lengths)
        })
        

def print_percent(list, name):
    list_perc = len([l for l in list if l]) / len(list)
    print('same '+ name + ' perc: ' + str(list_perc*100) + '%')
    return list_perc


def stats_per_group(diffs, same, group, func):
    new_diffs = [d for d in diffs if same[diffs.index(d)] == group]
    return arrow.get(func(new_diffs)) - arrow.get(0)


if __name__ == '__main__':
    main()
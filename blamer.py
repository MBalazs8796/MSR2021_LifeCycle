import os
import pandas as pd
import subprocess
import json
import re

def get_sourceBlames():
    BASEDIR = os.getcwd()
    checkpoint_df = None
    bug_df = pd.read_json('./bugs')
    downloaded_list = os.listdir('./repos')

    bug_df['blameData'] = [None] * len(bug_df)

    # if a previous checkpoint exists rename it to backup, this is done is order to minimize the impact of possible file corruption
    # only 1 backup checkpoint is stored, the previous is not needed, therefore is removed
    if os.path.exists('checkpoint.json'):
        checkpoint_df = pd.read_json('checkpoint.json')
        if os.path.exists('checkpoint_backup.json'):
            os.remove('checkpoint_backup.json')
        os.rename('checkpoint.json', 'checkpoint_backup.json')
        bug_df = bug_df.iloc[len(checkpoint_df):]
    elif os.path.exists('checkpoint_backup.json'):
        checkpoint_df = pd.read_json('checkpoint_backup.json')
    else:
        checkpoint_df = bug_df.iloc[0:0]

    if not os.path.isdir('./repos'):
        os.mkdir('./repos')
    os.chdir('./repos')

    #download the not yet present repos
    for project in bug_df.drop_duplicates(subset=['projectName'])['projectName']:
        project_maker = project.split('.')[0]
        project_name = '.'.join(project.split('.')[1:])
        if project_name not in downloaded_list:
            downloaded_list.append(project_name)
            subprocess.run(['git', 'clone', f'https://github.com/{project_maker}/{project_name}.git'])

    REPOS = os.getcwd()

    # get blame data for all rows
    for index, bug in bug_df.iterrows():

        data_read = False

        project_name = '.'.join(bug['projectName'].split('.')[1:])
        if project_name == 'solo' or bug['projectName'] == 'libnd4j':
            bug['blameData'] = ['Project not found']
        else:
            os.chdir(project_name)

            clean_checkout(bug['fixCommitParentSHA1'])
            try:
                with open('./'+bug['bugFilePath'], 'r', errors='ignore') as fp:
                    data = fp.read()
                data_read = True
            except FileNotFoundError:
                bug['blameData'] = ['File not found']

            if data_read:
                line_count = data[bug['bugNodeStartChar']:bug['bugNodeStartChar']+bug['bugNodeLength']].count('\n')

                dLines =  [line.strip() for line in data.split('\n')]

                lines = dLines[bug['bugLineNum']-1:bug['bugLineNum']+line_count]
                try:          
                    bug['blameData'] = sourcefinder(lines, bug['fixCommitParentSHA1'], bug['bugFilePath'], bug['bugLineNum'])
                except FileNotFoundError:
                    bug['blameData'] = ['File not found']
                except subprocess.CalledProcessError:
                    bug['blameData'] = ['Incorrect line number']
                except Exception as e:
                    if str(e) not in ['Empty path', 'No filename']:
                        raise Exception(e)
                    bug['blameData'] = ['Blame_error: ' + str(e)]
            
            checkpoint_df = checkpoint_df.append(bug)
            os.chdir(BASEDIR)
            with open('checkpoint.json', 'w') as fp:
                json.dump(json.loads(checkpoint_df.to_json(orient="records")), fp, indent=4)
            os.chdir(REPOS)
            print(f'{index} bug is done')
    os.chdir(BASEDIR)
    with open('blamed.json', 'w') as fp:
        json.dump(json.loads(bug_df.to_json(orient="records")), fp, indent=4)

    print('Mining done')

def get_hash_blame(target_hash, path, lineNum, amount):
    regex = re.compile(r'[^a-zA-Z0-9]')
    if path == '':
        raise Exception('Empty path')
    if '/'.join(path.split('/')[:-1]) == '':
        raise Exception('No filename')
    startPath = os.getcwd()
    blames = set()
    file_name = path.split('/')[-1]
    clean_checkout(target_hash)
    os.chdir('/'.join(path.split('/')[:-1]))
    for i in range(amount):
        blame = subprocess.check_output(['git', 'blame', file_name, '-L', str(lineNum+i)+','+str(lineNum+i)]).decode("utf8", 'ignore').split(' ')[0]
        if not blame.isalnum():
            blame = regex.sub('', blame)
        blames.add(blame)
    os.chdir(startPath)
    return blames

def sourcefinder(lines, paraHash, path, startLine):
    blames = set()
    possible_sources = list()
    blames = get_hash_blame(paraHash, path, startLine, len(lines))
    for hash in blames:
        clean_checkout(hash)
        try:
            with open(path,'r', errors='ignore') as fp:
                current = fp.read().split('\n')
        except FileNotFoundError:
            break
        for i, file_line in enumerate(current):
            bad_match = True
            if(file_line.strip() == lines[0]):
                bad_match = False
                for j, stubLine in enumerate(lines):
                    if stubLine != current[i+j].strip():
                        bad_match = True
                        break

            if not bad_match:
                if hash != paraHash:
                    possible_sources.extend(sourcefinder(lines, hash, path, i))
                if hash not in possible_sources:
                    possible_sources.append(hash)
    return possible_sources

def clean_checkout(hash) -> str:
    subprocess.run(['git','reset','-q','--hard'])
    subprocess.run(['git','clean', '-fd'])
    subprocess.run(['git', 'checkout', hash, '-f', '-q'])

def main():
    get_sourceBlames()

if __name__ == '__main__':
    main()
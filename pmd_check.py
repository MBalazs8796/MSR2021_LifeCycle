import json
import subprocess
import os
from tqdm import tqdm

from blamer import clean_checkout

class bugKey:
    def __init__(self, hash, repo):
        self.hash = hash
        self.repo = repo
    
    def __hash__(self):
        return hash((self.hash, self.repo))

    def __eq__(self, other):
        return (self.hash, self.repo) == (other.hash, other.repo)

    def __ne__(self, other):
        return not(self == other)
    
    def __str__(self) -> str:
        return f'{self.hash}, {self.repo}'

class bugInfo:
    def __init__(self, path, lineNum):
        self.path = path
        self.lineNum = lineNum
    
    def __hash__(self):
        return hash((self.path, self.lineNum))

    def __eq__(self, other):
        return (self.path, self.lineNum) == (other.path, other.lineNum)

    def __ne__(self, other):
        return not(self == other)
    
    def __str__(self) -> str:
        return f'{self.path}, {self.lineNum}'

def main():
    with open('checkpoint.json', 'r') as fp:
        bug_data = json.load(fp)
    
    hash_dict = dict()

    marked = list()

    for bug in bug_data:
        for hash in set(bug['blameData']):
            key = bugKey(hash, '.'.join(bug['projectName'].split('.')[1:]))
            if key not in hash_dict:
                hash_dict[key] = set()
            
            hash_dict[key].add(bugInfo(bug['bugFilePath'], bug['bugLineNum']))
    
    BASEDIR = os.getcwd()
    for key in tqdm(hash_dict):
        if ' ' in key.hash:
            continue
        os.chdir(f'./repos/{key.repo}')
        clean_checkout(key.hash)
        os.chdir('../../pmd/pmd-bin-6.30.0/bin')
        for file_info in hash_dict[key]:
            found = False
            subprocess.run(['run.sh', 'pmd' ,'-R', '../../../rules.xml', '-d', '../../../repos/'+key.repo+'/'+file_info.path, '-r', '../../../pmd_out.txt', '-cache', 'cache'])
            with open('../../../pmd_out.txt', 'r') as fp:
                for line in fp.readlines():
                    try:
                        if file_info.lineNum == line.split('\\')[-1].split(':')[-3].strip():
                            found = True
                            break
                    except IndexError:
                        continue
                marked.append(found)
        os.chdir(BASEDIR)

    with open('pmd_found_perc.txt', 'w') as fp:
        fp.write(str(len([m for m in marked if m]) / len(marked)))

if __name__ == '__main__':
    main()
import json
import datetime
import os
import subprocess

BASEDIR = os.getcwd()

class Data(object):
    def __init__(self, path=None, line=None, project=None, blame=None, status=None, num=1):
        self.path = path
        self.line = line
        self.project = project
        self.num = num
        if blame:
            self.blame = blame
        else:
            self.blame = list()
        if status:
            self.status = status
        else:
            self.status = list()

    def __eq__(self, other):
        return self.path == other.path and self.line == other.line

    def to_json(self):
        return{
            'project': self.project,
            'path': self.path,
            'line': self.line,
            'blame': str(self.blame),
            'status': str(self.status),
            'num': self.num
        }


class DataEncoder(json.JSONEncoder):
    def default(self, data):
        if isinstance(data, Data):
            return data.to_json()
        return super(DataEncoder, self).default(data)


def parse_datetime(blame):
    blame = blame.split(' ')[0]
    blame = ' '.join(blame.split(' ')[-4:-2])
    return datetime.datetime.strptime(blame, '%Y-%m-%d %H:%M:%S')


def process_data(processed_data):

    with open('blamed.json', 'r') as f:
        blame_data = json.load(f)

    for blame in blame_data:
        data = Data()
        data.path = blame['bugFilePath']
        data.line = blame['bugLineNum']
        data.project = blame['projectName'].split('.')[1]
        blame_str = blame['blameData']

        if data not in processed_data:
            data.blame.append(blame_str)
            processed_data.append(data)
        else:
            index = processed_data.index(data)
            temp = processed_data[index]

            if blame_str in temp.blame:
                continue

            temp.num += 1
            temp.blame.append(blame_str)
            temp.blame = sorted(temp.blame, key=lambda bd: parse_datetime(bd))
            processed_data[index] = temp


def get_status(data, incorrectDir=True):
    if incorrectDir:
        os.chdir(f'./repos/{data.project}')

    file_path = 'b/' + data.path
    for blame_data in data.blame:
        blame_hash = blame_data.split(' ')[0]
        bug = blame_data.split(' ')[-1].strip()
        correct = False
        not_replace = True
        try:
            patch = subprocess.check_output(['git', 'format-patch', '-1', blame_hash, '--stdout']).decode("utf8", 'ignore').strip()
        except subprocess.CalledProcessError as e:
            print(os.getcwd())
            patch = None
            print(e.returncode, e.output)
        for line in patch.splitlines():
            if file_path in line:
                correct = True

            if correct and bug in line.strip() and (line.startswith('+') or line.startswith('-')):
                if not_replace:
                    data.status.append('addition')
                else:
                    data.status.append('replace')

                break

            if line.startswith('-'):
                not_replace = False
            else:
                not_replace = True

        if not len(data.status):
            data.status.append('not_found')
    return data

def main():
    processed_data = list()
    process_data(processed_data)

    for data in processed_data:
        get_status(data)
        os.chdir(BASEDIR)

    with open('result.json', 'w') as f:
        json.dump(processed_data, f, indent=4, cls=DataEncoder)


if __name__ == '__main__':
    main()

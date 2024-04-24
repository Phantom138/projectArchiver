import os
import re
from pathlib import Path, PurePath
import subprocess
from fnmatch import fnmatch

import argparse


class Colors:
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'  # orange on some systems
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    LIGHT_GRAY = '\033[37m'
    DARK_GRAY = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    WHITE = '\033[97m'

    RESET = '\033[0m'  # called to return to standard terminal text color



class File:
    re_version = re.compile(r'(.*[^A-Za-z])v(\d+)', re.IGNORECASE)
    re_version2 = re.compile(r'(.+)v(\d+).')
    re_version3 = re.compile(r'^()v(\d+)$')

    def __init__(self, file):
        match = re.search(self.re_version, file)
        if match is None:
            match = re.search(self.re_version2, file)
        if match is None:
            match = re.search(self.re_version3, file)

        self.file = file
        if match is None:
            self.base_name = file
            self.version = None
        else:
            self.base_name = match.group(1)
            self.version = int(match.group(2))

        self.extension = os.path.splitext(file)[1]


def convert_size(size_bytes):
    import math
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)

    return f'{s} {size_name[i]}'


def get_size(path):
    if os.path.isfile(path):
        return os.path.getsize(path)

    elif os.path.isdir(path):
        return sum(file.stat().st_size for file in Path(path).rglob('*') if file.is_file())

def get_highest_version(src_files):
    mx_version = -1

    prev_file = File('s_v01.extention')
    mx_file = [prev_file.file]

    version_files = []
    single_files = []
    files = src_files.copy()
    files.sort(key=lambda f: os.path.splitext(f)[1])

    for f in files:
        # Get info from file name
        file = File(f)
        # Unversioned files are added to single_files list
        if file.version is None:
            single_files.append(file.file)
            prev_file = file
            continue

        if file.base_name != prev_file.base_name or file.extension != prev_file.extension:
            # This means we have a new file name
            mx_version = -1
            version_files.extend(mx_file)

        if file.version > mx_version:
            mx_file = [file.file]
            mx_version = file.version

        elif file.version == mx_version:
            # This keeps files with different extensions but same version
            mx_file.append(file.file)
            mx_version = file.version

        prev_file = file

    version_files.extend(mx_file)

    return version_files, single_files



def match_rule(rules: dict, path: Path, single_files: list = None, version_files: list = None):
    """
    :param version_files: list of files that have the highest version
    :param single_files: param used for version matching
    :param rules: dict containing rules for keeping/ignoring files
    :param path: full path of file or directory
    :return: False if file should be ignored, True if file should be kept
    If file does not match any rule, it returns None
    """

    if single_files is None:
        single_files = []
    if version_files is None:
        version_files = []


    if rules['ignore_empty']:
        if get_size(str(path)) == 0:
            return False, 'Empty', Colors.DARK_GRAY

    # Convert path to string with normal / for easier matching
    # Also get file names for version matching
    if path.is_dir():
        path_str = path.as_posix() + '/'
    elif path.is_file():
        path_str = path.as_posix()
    else:
        raise ValueError(f'{path} is not dir or file')

    for rule in rules['ignore']:
        if fnmatch(path_str, rule):
            return False, f'Ignore ({rule})', Colors.DARK_GRAY

    for rule in rules['keep']:
        if fnmatch(path_str, rule):

            return True, f'Keep ({rule})', Colors.MAGENTA


    # Version matching
    if path.name in version_files:
        return True, 'High version', Colors.GREEN

    if path.is_file() and path.name in single_files:
        return True, 'Unique', Colors.YELLOW

    if path.name not in single_files and path.name not in version_files:
        return False, 'Low version', Colors.DARK_GRAY

    return None, '', Colors.RESET



class Project:
    def __init__(self, path: str, rules: dict):
        self.path = path
        self.rules = rules

        self.ignore = []
        self.keep = []

    def check_project(self, output=True, verbose=False):
        """
        Runs over the project directory and checks if files and directories should be kept or ignored,
        Based on the rules provided in the dir_rules and file_rules dictionaries

        :param output: bool to enable output
        :param verbose: bool to enable verbose output
        """
        self.ignore = []
        self.keep = []
        for root, dirs, files in os.walk(self.path):
            # Changes to forward slashes and adds / to the end of directories
            # This is for easier pattern matching later on
            root = Path(root)

            ver_dir, single_dir = get_highest_version(dirs)

            # Check directories
            for dr in dirs[:]:
                dr_path = root.joinpath(dr)
                match, reason, out_color = match_rule(self.rules, dr_path, single_dir, ver_dir)

                if match is None:
                    continue

                if match is False:
                    self.ignore.append(dr_path)
                    dirs.remove(dr)

                if match is True:
                    self.keep.append(dr_path)
                    dirs.remove(dr)

                if output:
                    reason = f"{reason:>20}  " if verbose else ''
                    print(f"{out_color}{reason}{dr_path}{Colors.RESET}")

            # Print root directory if it contains files
            if len(files) != 0 and output:
                sep = f'{'-'*20}  ' if verbose else ''
                print(f"{sep}{root}")

            # Check files
            file_paths = [root.joinpath(f) for f in files]
            self.__check_files(file_paths, output, verbose)

        self.test_size(output=output)

    def __check_files(self, files: list, output: bool, verbose: bool):
        """
        Check files based on the rules provided in the file_rules dictionary

        :param output: bool to enable output
        :param verbose: bool to enable verbose output
        :param files: full path of files
        """
        # Get files that should be kept

        file_names = [f.name for f in files]
        versioned_files, single_files = get_highest_version(file_names)

        for file in files:
            match, reason, out_color = match_rule(self.rules, file, single_files, versioned_files)

            if match is True:
                self.keep.append(file)

            if match is False:
                self.ignore.append(file)

            if output:
                reason = f'{reason:>20}  ' if verbose else ''
                print(f"{out_color}{reason}-  {file.name}{Colors.RESET}")

    def archive(self, dest_path, output=True):
        """
        Method to archive the project directory based on the keep list
        Runs check_project method to get the keep list
        Runs robocopy to copy the files to the destination path

        :param dest_path: path where the archive will be saved
        :param output: bool to enable output
        """
        self.check_project(output=False)

        for file in self.keep:
            rel_path = os.path.relpath(file, self.path)
            dest = os.path.join(dest_path, rel_path)

            # print('Copying: ', os.path.join(dest, file))
            if os.path.isdir(file):
                copy_cmd = ['robocopy', file, dest, '/J', '/NJS', '/NJH', '/S', '/V']
            else:
                copy_cmd = ['robocopy', os.path.dirname(file), os.path.dirname(dest), os.path.basename(file), '/J',
                            '/NJS', '/NJH', '/NDL', '/V']
            subprocess.run(copy_cmd, shell=True)

        archive_size = sum(file.stat().st_size for file in Path(dest_path).rglob('*'))
        src_size = sum(file.stat().st_size for file in Path(self.path).rglob('*'))

        if output:
            print()
            print(f"{Colors.GREEN}_________ARCHIVE RESULTS__________{Colors.RESET}")
            print(f"{Colors.MAGENTA}Archive path: {dest_path}{Colors.RESET}")
            print(f"Original size: {convert_size(src_size)}")
            print(f"Total archive size: {convert_size(archive_size)}")
            print(f"Saved: {convert_size(src_size-archive_size)}")

    def test_size(self, output=True):
        del_size = 0
        keep_size = 0
        for file in self.ignore:
            del_size += get_size(file)

        for file in self.keep:
            keep_size += get_size(file)



        proj_size = get_size(self.path)

        if output:
            print()
            print(f"{Colors.BLUE}_________CHECK RESULTS__________{Colors.RESET}")
            print(f"{Colors.MAGENTA}Project path: {self.path}{Colors.RESET}")
            print(f"Total project size: {convert_size(proj_size)}")
            print(f"Don't keep: {convert_size(del_size)}")
            print(f"Keep: {convert_size(keep_size)}")

        if del_size + keep_size != proj_size:
            raise ValueError('Size mismatch')

        if output:
            print(f'{Colors.GREEN}Size test passed{Colors.RESET}')
        return True


def rules_from_file(file, output=False):
    lines = []
    # Read lines from file and ignore comments
    with open(file) as f:
        file_path = os.path.realpath(f.name)
        for line in f:
            pattern = line.split('#', 1)[0].strip()
            if pattern:
                lines.append(pattern)

    # Build rule dictionary
    available_rules = ['ignore_empty', 'check_versions']
    rules = {
        'ignore_empty': False,
        'check_versions': False,
        'keep': [],
        'ignore': []
    }
    for line in lines:
        # Rules are defined with the @ character
        if line.startswith('@'):
            res = re.search(r'@(.*):\s*([A-Za-z0-9]*)', line)
            rule = res.group(1)
            value = res.group(2)

            if rule not in available_rules:
                raise ValueError(f"Invalid rule {rule} in {line}")

            # Validate input
            if value in ['True', 'true', '1']:
                rules[rule] = True
            elif value in ['False', 'false', '0']:
                rules[rule] = False
            else:
                raise ValueError(f"Invalid value {value} in {line}")

        # Ignore is with !
        elif line.startswith('!'):
            rules['ignore'].append(line)

        # If nothing else matches, it must be a rule to keep
        else:
            rules['keep'].append(line)

    if output:
        print(f"Rules from: {file_path}")
        print("-----------")
        print(Colors.MAGENTA, end='')
        for rule in available_rules:
            print(f'{rule}: {rules[rule]}')

        print(Colors.GREEN)
        for keep in rules['keep']:
            print(keep)

        print(Colors.RED, end='')
        for ignore in rules['ignore']:
            print(ignore)

        print(Colors.RESET)
    return rules

def main():
    parser = argparse.ArgumentParser(description="Clean and archive a project directory.")

    # Subparser for the check command
    parser.add_argument("source_path", help="Path to the project directory")
    parser.add_argument("archive_path", help="Path to the archive directory")
    parser.add_argument("--check-rules", action="store_true", help="Check if the rules are detected properly")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--check", action="store_true", help="Archive the project directory")

    args = parser.parse_args()

    rule_file = "./rules.txt"
    if args.check_rules:
        rules_from_file("./rules.txt", output=True)
        return
    else:
        rules = rules_from_file("./rules.txt", output=False)

    if args.check:
        proj = Project(args.source_path, rules)
        proj.check_project(verbose=args.verbose)
    else:
        proj = Project(args.source_path, rules)
        proj.archive(args.archive_path)

def quick_test():
    rules = {
        'ignore_empty': True,
        'ignore': [
            '*/.*/',
            '*/_archive/',
            '*.tx',
            'Thumbs.db',
        ],
        'keep': [
            '*/dailies/',
        ]
    }


    proj = Project(r'D:\CreatureProject', rules)
    proj.check_project(output=True, verbose=True)


if __name__ == '__main__':
    main()





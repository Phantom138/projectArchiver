import os
import re
from colorama import init as colorama_init
from colorama import Fore
from pathlib import Path
import logging
import subprocess
from fnmatch import fnmatch
import argparse

re_version = re.compile(r'(.*[^A-Za-z])v(\d+)', re.IGNORECASE)
re_version2 = re.compile(r'(.+)v(\d+).')
# re_version3 = re.compile(r'([A-Za-z]+)(\d+)\.')

class File:
    def __init__(self, file):
        match = re.search(re_version, file)
        if match is None:
            match = re.search(re_version2, file)
        # if match is None:
        #     match = re.search(re_version3, file)

        self.file = file
        if match is None:
            self.base_name = file
            self.version = None
        else:
            self.base_name = match.group(1)
            self.version = int(match.group(2))

        self.extension = file.split('.')[-1]


def convert_size(size_bytes, base=1024):
    import math
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, base)))
    p = math.pow(base, i)
    s = round(size_bytes / p, 2)

    return f'{s} {size_name[i]}'

def get_size(directory):
    total_size = 0
    for file in os.scandir(directory):
        total_size += os.stat(file).st_size

    return total_size


def match_rule(rules: dict, full_path: str):
    """
    :param rules: dict containing rules for keeping/ignoring files
    :param full_path: full path of file or directory
    :return: False if file should be ignored, True if file should be kept
    If file does not match any rule, it returns None
    """

    if rules['ignore_empty']:
        if is_empty(full_path):
            return False

    file = os.path.basename(full_path)

    for rule in rules['ignore']:
        if fnmatch(file, rule):
            return False

    for rule in rules['keep']:
        if fnmatch(file, rule):
            return True

    return None


def is_empty(path):
    if os.path.isfile(path):
        return os.path.getsize(path) == 0
    elif os.path.isdir(path):
        return sum(file.stat().st_size for file in Path(path).rglob('*')) == 0


def get_highest_version(files):
    mx_version = -1

    prev_file = File('s_v01.extention')
    mx_file = prev_file.file

    version_files = []
    single_files = []

    for f in files:
        # Get info from file name
        file = File(f)

        # Unversioned files are added to single_files list
        if file.version is None:
            single_files.append(file.file)
            prev_file = file
            continue


        if file.base_name != prev_file.base_name:
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

class Project:
    def __init__(self, path: str, dir_rules: dict, file_rules: dict):
        self.path = path
        self.dir_rules = dir_rules
        self.file_rules = file_rules

        self.ignore = []
        self.keep = []

    def check_project(self, output=True):
        self.ignore = []
        self.keep = []
        for root, dirs, files in os.walk(self.path):
            # If dirs match ignore rule, they are ignored
            # If dirs match keep rule, all the contents are kept
            # Iterate over copy of dirs so we can remove items from original list
            for dr in dirs[:]:
                full_path = os.path.join(root, dr)
                match = match_rule(self.dir_rules, full_path)

                if match is None:
                    continue

                if match is False:
                    self.ignore.append(full_path)
                    dirs.remove(dr)

                    if output: print(f"{Fore.LIGHTBLACK_EX}{full_path}{Fore.RESET}")

                if match is True:
                    self.keep.append(full_path)
                    dirs.remove(dr)
                    if output: print(f"{Fore.MAGENTA}{full_path}{Fore.RESET}")

            # Print root directory if it contains files
            if len(files) != 0:
                if output: print(root)

            full_path_files = [os.path.join(root, file) for file in files]
            self.__check_files(full_path_files, output)

        self.test_size(output=output)

    def __check_files(self, files: list, output: bool):
        """
        :param files: full path of files
        """
        # Get files that should be kept
        file_names = [os.path.basename(file) for file in files]
        versioned_files, single_files = get_highest_version(file_names)

        for file, file_name in zip(files, file_names):
            if output: print('― ', end='')
            match = match_rule( self.file_rules, file)

            if match is None:
                # Keep files according to versioned_files and single_files
                if file_name in versioned_files or file_name in single_files:
                    self.keep.append(file)
                    color = Fore.GREEN if file_name in versioned_files else Fore.YELLOW
                    if output: print(f"{color}{file_name}{Fore.RESET}")
                else:
                    self.ignore.append(file)
                    if output: print(file_name)

            if match is True:
                self.keep.append(file)
                if output: print(f"{Fore.MAGENTA}{file_name}{Fore.RESET}")

            if match is False:
                self.ignore.append(file)
                if output: print(f"{Fore.LIGHTBLACK_EX}{file_name}{Fore.RESET}")

    def archive(self, dest_path, output=True):
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
            print(f"{Fore.GREEN}_________ARCHIVE RESULTS__________{Fore.RESET}")
            print(f"{Fore.MAGENTA}Archive path: {dest_path}{Fore.RESET}")
            print(f"Original size: {convert_size(src_size)}")
            print(f"Total archive size: {convert_size(archive_size)}")
            print(f"Saved: {convert_size(src_size-archive_size)}")

    def test_size(self, output=True):
        del_size = 0
        keep_size = 0
        for file in self.ignore:
            if os.path.isdir(file):
                del_size += sum(file.stat().st_size for file in Path(file).rglob('*'))
            else:
                del_size += os.path.getsize(file)

        for file in self.keep:
            if os.path.isdir(file):
                keep_size += sum(file.stat().st_size for file in Path(file).rglob('*'))
            else:
                keep_size += os.path.getsize(file)



        proj_size = sum(file.stat().st_size for file in Path(self.path).rglob('*'))


        if output:
            print()
            print(f"{Fore.BLUE}_________CHECK RESULTS__________{Fore.RESET}")
            print(f"{Fore.MAGENTA}Project path: {self.path}{Fore.RESET}")
            print(f"Total project size: {convert_size(proj_size)}")
            print(f"Don't keep: {convert_size(del_size)}")
            print(f"Keep: {convert_size(keep_size)}")

        if del_size + keep_size != proj_size:
            raise ValueError('Size mismatch')

        if output:
            print(f'{Fore.GREEN}Size test passed{Fore.RESET}')
        return True


def main():
    parser = argparse.ArgumentParser(description="Clean and archive a project directory.")

    # Subparser for the check command
    parser.add_argument("source_path", help="Path to the project directory")
    parser.add_argument("archive_path", help="Path to the archive directory")
    parser.add_argument("--output", action="store_true", help="Enable verbose output")
    parser.add_argument("--check", action="store_true", help="Archive the project directory")


    args = parser.parse_args()

    dir_rules = {
        'ignore_empty': True,
        'ignore': [
            '.*',
            '_archive',
        ],
        'keep': [
            '*dailies',
        ]
    }

    file_rules = {
        'ignore_empty': True,
        'ignore': [
            '*.tx',
            'Thumbs.db'
        ],
        'keep': [
        ]
    }
    if args.check:
        proj = Project(args.source_path, dir_rules, file_rules)
        proj.check_project()
    else:
        proj = Project(args.source_path, dir_rules, file_rules)
        proj.archive(args.archive_path)

if __name__ == '__main__':
    main()

    # archive_path = r'D:\CreatureProject_archive'
    # proj.archive(archive_path)
    #
    # archive_size = sum(file.stat().st_size for file in Path(archive_path).rglob('*'))
    # print(archive_size)





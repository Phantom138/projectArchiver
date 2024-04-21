import os
import re
from colorama import init as colorama_init
from colorama import Fore
from pathlib import Path
import logging
import subprocess
from fnmatch import fnmatch


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


def match_rule(rules, file):
    for rule in rules:
        if fnmatch(file, rule):
            return True

    return False


def is_empty(path):
    size = sum(file.stat().st_size for file in Path(path).rglob('*'))
    if size == 0:
        return True
    return False


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



def check_project(path: str, dir_rules: list, file_rules: list, ignore_empty_dirs: bool = True):
    ignore = []
    keep = []

    for root, dirs, files in os.walk(path):
        # Check if directories match rules and add them to ignore list
        dirs_to_remove = [dr for dr in dirs if match_rule(dir_rules, dr)]
        for dr in dirs_to_remove:
            full_path = os.path.join(root, dr)
            ignore.append(full_path)

            dirs.remove(dr)
            print(f"{Fore.MAGENTA}{full_path}{Fore.RESET}")

        # ignore empty directories
        if ignore_empty_dirs and is_empty(root):
            ignore.append(root)
            print(f"{Fore.LIGHTBLACK_EX}{root}{Fore.RESET}")

        # Print root directory if it contains files
        elif len(files) != 0:
            print(root)

        # Get files that should be kept
        versioned_files, single_files = get_highest_version(files)

        for file in files:
            print('― ', end='')
            full_path = os.path.join(root, file)

            if match_rule(file_rules, file):
                ignore.append(full_path)
                print(f"{Fore.LIGHTBLACK_EX}{file}{Fore.RESET}")
                continue

            # Empty files are ignored
            if os.path.getsize(full_path) == 0:
                ignore.append(full_path)
                print(f"{Fore.LIGHTBLACK_EX}{file}{Fore.RESET}")
                continue

            # Keep files according to versioned_files and single_files
            if file in versioned_files or file in single_files:
                keep.append(full_path)
                color = Fore.GREEN if file in versioned_files else Fore.YELLOW
                print(f"{color}{file}{Fore.RESET}")
            else:
                ignore.append(full_path)
                print(file)

    return ignore, keep


def archive_project(path: str, org_path: str, to_keep: list):
    for file in to_keep:
        # Get relative paths
        src_dir = os.path.dirname(file)
        src_file = os.path.basename(file)

        rel_path = os.path.relpath(file, org_path)
        dest_dir = os.path.dirname(os.path.join(path, rel_path))

        print('Copying: ', os.path.join(dest_dir, src_file))
        copy_cmd = ['robocopy', src_dir, dest_dir, src_file, '/J', '/NJS', '/NJH', '/NDL']
        subprocess.run(copy_cmd, shell=True)



def test(project_path, to_ignore, to_keep):
    del_size = 0
    keep_size = 0
    for file in to_ignore:
        if os.path.isdir(file):
            del_size += sum(file.stat().st_size for file in Path(file).rglob('*'))
        else:
            del_size += os.path.getsize(file)

    for file in to_keep:
        if os.path.isdir(file):
            keep_size += sum(file.stat().st_size for file in Path(file).rglob('*'))
        else:
            keep_size += os.path.getsize(file)
    print(keep_size)

    proj_size = sum(file.stat().st_size for file in Path(project_path).rglob('*'))
    print(proj_size)
    if del_size + keep_size != proj_size:
        print('Error, size mismatch')
        return False

    return True


if __name__ == '__main__':
    dir_rules = {
        'ignore': [
            '.*',
            '_archive',
            '*dailies'
        ],
        'keep': [
        ]
    }

    file_rules = [
        '*.tx',
        'Thumbs.db'
    ]

    to_ignore, to_keep = check_project(r'D:\CreatureProject', dir_rules['ignore'], file_rules, ignore_empty_dirs=True)

    if test(r'D:\CreatureProject', to_ignore, to_keep):
        print('All tests passed')
        # archive_project(r'D:\CreatureProject_archive', r'D:\CreatureProject', to_keep)




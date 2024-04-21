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



def check_project(path: str, dir_rules: dict, file_rules: dict):
    ignore = []
    keep = []

    for root, dirs, files in os.walk(path):
        # If dirs match ignore rule, they are ignored
        # If dirs match keep rule, all the contents are kept
        # Iterate over copy of dirs so we can remove items from original list
        for dr in dirs[:]:
            full_path = os.path.join(root, dr)
            match = match_rule(dir_rules, full_path)

            if match is None:
                continue

            if match is False:
                ignore.append(full_path)
                dirs.remove(dr)
                print(f"{Fore.LIGHTBLACK_EX}{full_path}{Fore.RESET}")

            if match is True:
                keep.append(full_path)
                dirs.remove(dr)
                print(f"{Fore.MAGENTA}{full_path}{Fore.RESET}")

        # Print root directory if it contains files
        if len(files) != 0:
            print(root)

        # Get files that should be kept
        versioned_files, single_files = get_highest_version(files)

        for file in files:
            print('― ', end='')
            full_path = os.path.join(root, file)
            match = match_rule(file_rules, full_path)

            if match is None:
                # Keep files according to versioned_files and single_files
                if file in versioned_files or file in single_files:
                    keep.append(full_path)
                    color = Fore.GREEN if file in versioned_files else Fore.YELLOW
                    print(f"{color}{file}{Fore.RESET}")
                else:
                    ignore.append(full_path)
                    print(file)

            if match is True:
                keep.append(full_path)
                print(f"{Fore.MAGENTA}{file}{Fore.RESET}")

            if match is False:
                ignore.append(full_path)
                print(f"{Fore.LIGHTBLACK_EX}{file}{Fore.RESET}")


    return ignore, keep


def archive_project(dest_path: str, org_path: str, to_keep: list):
    for file in to_keep:
        rel_path = os.path.relpath(file, org_path)
        dest = os.path.join(dest_path, rel_path)


        print('Copying: ', os.path.join(dest, file))
        if os.path.isdir(file):
            copy_cmd = ['robocopy', file, dest, '/J', '/NJS', '/NJH', '/NDL', '/S']
        else:
            copy_cmd = ['robocopy', os.path.dirname(file), os.path.dirname(dest), os.path.basename(file), '/J', '/NJS', '/NJH', '/NDL']
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
        'ignore_empty': True,
        'ignore': [
            '.*',
            '_archive',
            'tex'
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

    to_ignore, to_keep = check_project(r'D:\CreatureProject', dir_rules, file_rules)

    if test(r'D:\CreatureProject', to_ignore, to_keep):
        print('All tests passed')
        archive_project(r'D:\CreatureProject_archive', r'D:\CreatureProject', to_keep)

        archive_size = sum(file.stat().st_size for file in Path(r'D:\CreatureProject_archive').rglob('*'))
        print(archive_size)
        test(r'D:\CreatureProject', to_ignore, to_keep)





# Project Archiver

Python CLI tool for archiving large projects by version and pattern matching.

Currently only working in Windows.

Not the most performant tool, sruggles with directories that have more than 50k files. It is meant for smaller directories with large files.

## Usage

### Basic Usage
It is recommended to first run it with  the `--check` flag. This is not going to archive anything, just check how much data should be kept.

```bash
python archiveProj.py <source_path> <archive_path> --check
```
Replace `<source_path>` with the path to the project directory you want to archive, and `<archive_path>` with the desired location for the archived project.

By adding also the `--output` flag, you can see which files are matched and which are not.
By also adding the `--verbose` flag, you can see more detailed output.

```bash
python archiveProj.py <source_path> <archive_path> --check --output --verbose
```

When running in CMD, appending `| more` at the end is going to enable you to go line-by-line. It is recommended to use it when the output is too long to see.

```bash
python archiveProj.py <source_path> <archive_path> --check --output --verbose | more
```

Once you are happy with the file selection, archive by using the following command:
`<archive_path>` should be an empty/non-existent directory

```bash
python archiveProj.py <source_path> <archive_path>
```

### Parameters

| Parameter          | Description                                             |
|--------------------|---------------------------------------------------------|
| `--check-rules`    | Check if the rules are detected properly.               |
| `--verbose`        | Enable verbose output.                                  |
| `--check`          | Show the data to be kept or ignored before archiving.   |
| `--output`         | Enables output during the checking process.             |


### Rule Specification

The Project Archiver allows you to specify rules for managing project files and directories in a `rules.txt` file.
Specify options using `@` decorator.
Supported options: `ignore_empty, keep_versions`

- `@ignore_empty:` specifies if it should ignore empty directories/files. Note: directory is considered empty when it's size is `0kb`. Default: False
- `@keep_versions: ` specifies that how many latest versions should be kept. Default: 1
  
- Lines starting with `!` denote patterns to ignore. For example, `!*.tx` ignores all files with the `.tx` extension.
- Lines without a prefix specify patterns to keep. For example, `*/my_file.txt` keeps all files named `my_file.txt`.
- For matching directories add a `/` at the end. For example, `*/dir/` matches all directories named `dir`

You can check if your rules are detected by running:

```bash
python archiveProj.py <source_path> <archive_path> --check-rules
```



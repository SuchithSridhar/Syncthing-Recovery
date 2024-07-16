import os
import shutil
import csv
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import time
from typing import List, Tuple

# Ensure to set the right directories here
# Corrupted Directory: The original directory that has been corrupted, this is
# used as a reference to keep track of which files are missing.
# Backup Directory: The .stversions directory where the backup files are stored.
# Recovery Directory: The location where the backup files are restored to.
CORRUPTED_DIR = ''
BACKUP_DIR = ''
RECOVERY_DIR = 'recovery'
LOGS_DIR = 'logs'

MISSING_FILES_LOG = f'{LOGS_DIR}/missing-files.txt'
RECOVERED_FILES_CSV = f'{LOGS_DIR}/recovered-files.csv'
POSSIBLY_CORRUPTED_LOG = f'{LOGS_DIR}/possibly-corrupted-file-backups.txt'

# This options allows you to configure the maximum time after which a backup
# should be used. If a backup has been created after this time limit then it's
# not used as a possible recovery file.
# This is for cases where a corrupted file has changed after a while leading to
# a corrupted file being stored as a backup as well.
TIME_LIMIT = timedelta(hours=3)
REFERENCE_TIME = datetime.strptime('20240714-180000', '%Y%m%d-%H%M%S')

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()


@dataclass
class BackupFileInfo:
    '''
        This dataclass is intended to be associated with EACH original file. It
        contains information that would be required for analysis and
        restoration of that one single file.
    '''
    count: int = 0

    latest_time: datetime = None
    latest_file: str = None
    latest_outside_limit: bool = False

    # The file to be used for backup (within time limit)
    backup_file: str = None
    backup_time: datetime = None


@dataclass
class FileRecoveryResult:
    total_original: int = 0
    total_missing: int = 0
    total_recovered: int = 0
    total_possibly_corrupted: int = 0

    # The earliest file that was used for the restore process
    earliest_file_used: str = None
    earliest_time_used: datetime = None

    # The latest file that was used for the restore process
    latest_file_used: str = None
    latest_time_used: datetime = None

    missing_files: List[str] = field(default_factory=list)

    # original filename, backup filename, backup timestamp,
    # number of backups found, last backup outside limit?, last backup found,
    # last backup time
    recovered_files: List[Tuple[str, str, datetime,
                                int, bool, str, datetime
                                ]] = field(default_factory=list)

    # A possibly corrupted file is a file that's a backup that's more recent
    # than the time limit set.
    possibly_corrupted_files: List[str] = field(default_factory=list)


def ensure_directory_exists(directory: str):
    '''
        Create $directory if it's not present. It will create all required
        directory in provided path.

        Example: ensure_directory_exists("test/test/test") will create all 3
        test directories if they are not present.
    '''
    os.makedirs(directory, exist_ok=True)


def check_directory_exists(directory: str) -> bool:
    '''
        Returns True if $directory is a directory.
    '''
    return os.path.isdir(directory)


def split_extension(filename: str) -> Tuple[str, str]:
    name, ext = os.path.splitext(filename)

    # swap name and ext for cases like '.gitignore'
    # os.splitext treats it as a pure name and syncthing
    # treats it as a pure extension.
    if name.startswith('.') and len(ext) == 0:
        ext = name
        name = ''

    return name, ext


def get_backup_file_info(backup_files: List[str]) -> BackupFileInfo:
    '''
        Takes a list of backup files for a particular original file and then
        decides on a few things like latest file and earliest time.
    '''
    bak = BackupFileInfo()
    bak.count = len(backup_files)

    for file in backup_files:
        basename, ext = split_extension(file)
        timestamp_str = basename.split('~')[-1]
        timestamp = datetime.strptime(timestamp_str, '%Y%m%d-%H%M%S')
        is_inside_time_limit = timestamp <= REFERENCE_TIME + TIME_LIMIT

        if bak.latest_time is None or timestamp > bak.latest_time:
            bak.latest_time = timestamp
            bak.latest_file = file
            bak.latest_outside_limit = (not is_inside_time_limit)

        if is_inside_time_limit:
            if bak.backup_time is None or timestamp > bak.backup_time:
                bak.backup_time = timestamp
                bak.backup_file = file

    return bak


def get_all_files(directory: str) -> List[str]:
    '''
        Get all files inside of $directory
        as a list of relative path from that directory

        Example: get_all_files("test-dir"):
            ["inner-dir/file1.txt", "outerfile.txt", "l1/l2/file2.txt"]
    '''
    return [
        os.path.relpath(os.path.join(root, file), directory)
        for root, _, files in os.walk(directory)
        for file in files
    ]


def find_and_copy_backup(all_files: List[str], log_inline: bool = False
                         ) -> FileRecoveryResult:
    '''
        For each file in $all_files find the corresponding backups in
        the $BACKUP_DIR. Then find the latest backup file within the time limit
        set using $TIME_LIMIT and $REFERENCE_TIME. Copy that file into the
        $RECOVERY_DIR and log details.
    '''

    terminal_width = shutil.get_terminal_size().columns - 10
    results = FileRecoveryResult()

    results.total_original = len(all_files)
    start_time = time.time()

    for index, file in enumerate(all_files):
        elapsed_time = int(time.time() - start_time)
        progress_message = f"[{elapsed_time} s] ({
            index + 1} / {results.total_original}) {file}"

        if log_inline:
            print('\r' + (' ' * (terminal_width + 1)), end='')
            print('\r' + progress_message[:terminal_width-3] + "...", end='')
        else:
            logger.info(progress_message)

        file_dir = os.path.dirname(file)
        file_name = os.path.basename(file)
        prefix_pattern, suffix_pattern = split_extension(file_name)
        prefix_pattern += '~'

        backup_dir_path = os.path.join(BACKUP_DIR, file_dir)
        if not os.path.exists(backup_dir_path):
            # If the directory is not present, then we're sure that no back up
            # files exist.
            results.missing_files.append(file)
            continue

        backup_files: List[str] = [
            f for f in os.listdir(backup_dir_path)
            if f.startswith(prefix_pattern) and f.endswith(suffix_pattern)
        ]

        if not backup_files:
            # If not backup files are found then it's missing
            results.missing_files.append(file)
            continue

        backup_info: BackupFileInfo = get_backup_file_info(backup_files)

        if backup_info.backup_file is None:
            # if not valid backup file is found
            breakpoint()
            results.missing_files.append(file)
            continue

        backup_path = os.path.join(
            BACKUP_DIR, file_dir, backup_info.backup_file
        )

        recovery_path = os.path.join(RECOVERY_DIR, file)
        recovery_dir = os.path.dirname(recovery_path)
        ensure_directory_exists(recovery_dir)

        try:
            shutil.copy2(backup_path, recovery_path)
            results.recovered_files.append(
                (
                    file,                              # original filename
                    backup_info.backup_file,           # backup filename
                    backup_info.backup_time,           # backup time
                    backup_info.count,                 # backup count
                    backup_info.latest_outside_limit,  # is outside time limit
                    backup_info.latest_file,           # last file found
                    backup_info.latest_time,           # last file timestamp
                )
            )

        except Exception:
            logger.error(f'Error copying {backup_path} to {recovery_path}.')

    if log_inline:
        # Ensure we move to the next line after inline progress
        print()

    return results


def log_missing_files(missing_files: List[str]):
    with open(MISSING_FILES_LOG, 'w') as f:
        for missing_file in missing_files:
            f.write(f'{missing_file}\n')


def log_recovered_files(
    recovered_files: List[Tuple[str, str, datetime,
                                int, bool, str, datetime
                                ]]):
    '''
        Write recovered file information to CSV file.
    '''

    with open(RECOVERED_FILES_CSV, 'w', newline='') as csvfile:
        fieldnames = [
            'Original File', 'Backup File', 'Timestamp of Backup File',
            'Number of Backup Files Present', 'Is Last Backup Outside Limit',
            'Last Backup Found', 'Last Backup Timestamp'
        ]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in recovered_files:
            orig, bak, bak_time, count, out_limit, last, last_time = row

            writer.writerow({
                fieldnames[0]: orig,
                fieldnames[1]: bak,
                fieldnames[2]: bak_time.strftime('%Y-%m-%d %H:%M:%S'),
                fieldnames[3]: count,
                fieldnames[4]: out_limit,
                fieldnames[5]: last,
                fieldnames[6]: last_time.strftime('%Y-%m-%d %H:%M:%S'),
            })


def log_possibly_corrupted_files(possibly_corrupted_files: List[str]):
    with open(POSSIBLY_CORRUPTED_LOG, 'w') as f:
        for file in possibly_corrupted_files:
            f.write(f'{file}\n')


def main(log_inline: bool = False):
    if not check_directory_exists(CORRUPTED_DIR):
        logger.error("Corrupted directory not found.")
        exit(1)

    if not check_directory_exists(BACKUP_DIR):
        logger.error("Backup directory not found.")
        exit(1)

    ensure_directory_exists(RECOVERY_DIR)
    all_files = get_all_files(CORRUPTED_DIR)
    results = find_and_copy_backup(all_files, log_inline)

    ensure_directory_exists(LOGS_DIR)
    log_missing_files(results.missing_files)
    log_recovered_files(results.recovered_files)
    log_possibly_corrupted_files(results.possibly_corrupted_files)

    logger.info('Recovery complete.')
    logger.info(f'Missing files log: {MISSING_FILES_LOG}')
    logger.info(f'Recovered files log: {RECOVERED_FILES_CSV}')
    logger.info(f'Possibly corrupted files log: {POSSIBLY_CORRUPTED_LOG}')


if __name__ == "__main__":
    main(log_inline=True)

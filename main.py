import argparse
import recovery as rec


def main():
    parser = argparse.ArgumentParser(description='Recover files from backup.')
    parser.add_argument('--corrupted-dir', type=str, default='', help='Path to the corrupted directory.')
    parser.add_argument('--backup-dir', type=str, default='', help='Path to the backup directory.')
    parser.add_argument('--recovery-dir', type=str, default='recovery', help='Path to the recovery directory.')
    parser.add_argument('--logs-dir', type=str, default='logs', help='Path to the logs directory.')
    parser.add_argument('--time-limit', type=int, default=3, help='Time limit in hours for backups to be considered valid.')
    parser.add_argument('--reference-time', type=str, default='', help='Reference time for backup file consideration.')
    parser.add_argument('--log-inline', action='store_true', help='Enable inline logging.')
    
    args = parser.parse_args()
    
    corrupted_dir = args.corrupted_dir
    backup_dir = args.backup_dir
    recovery_dir = args.recovery_dir
    logs_dir = args.logs_dir
    time_limit = timedelta(hours=args.time_limit)
    reference_time = datetime.strptime(args.reference_time, '%Y%m%d-%H%M%S')
    log_inline = args.log_inline

    logging.basicConfig(level=logging.INFO, format='%(message)s', handlers=[
        logging.FileHandler(os.path.join(logs_dir, 'recovery.log')),
        logging.StreamHandler()
    ])
    global logger
    logger = logging.getLogger()

    # Confirmation message
    print("Starting recovery process with the following options:")
    print(f"Corrupted Directory: {corrupted_dir}")
    print(f"Backup Directory: {backup_dir}")
    print(f"Recovery Directory: {recovery_dir}")
    print(f"Logs Directory: {logs_dir}")
    print(f"Time Limit: {time_limit}")
    print(f"Reference Time: {reference_time}")
    print(f"Log Inline: {log_inline}")
    print()

    if not check_directory_exists(corrupted_dir):
        logger.error("Corrupted directory not found.")
        exit(1)

    if not check_directory_exists(backup_dir):
        logger.error("Backup directory not found.")
        exit(1)

    ensure_directory_exists(recovery_dir)
    all_files = get_all_files(corrupted_dir)
    results = find_and_copy_backup(all_files, backup_dir, recovery_dir, reference_time, time_limit, log_inline)

    ensure_directory_exists(logs_dir)
    log_missing_files(results.missing_files, logs_dir)
    log_recovered_files(results.recovered_files, logs_dir)
    log_possibly_corrupted_files(results.possibly_corrupted_files, logs_dir)

    logger.info('Recovery complete.')
    logger.info(f'Missing files log: {os.path.join(logs_dir, "missing-files.txt")}')
    logger.info(f'Recovered files log: {os.path.join(logs_dir, "recovered-files.csv")}')
    logger.info(f'Possibly corrupted files log: {os.path.join(logs_dir, "possibly-corrupted-file-backups.txt")}')


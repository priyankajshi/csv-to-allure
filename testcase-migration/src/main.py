import asyncio
import sys
import click
import aiohttp
from typing import Optional

from src.config import (
    ALLURE_BASE_URL,
    PROJECT_ID as DEFAULT_PROJECT_ID,
    TESTCASE_API_ENDPOINT as DEFAULT_API_ENDPOINT,
    CSV_FILE_PATH as DEFAULT_CSV_PATH,
)
from src.utils.logger import setup_logger
from src.core.reader import CsvReader
from src.core.transformer import TestCaseTransformer
from src.core.client import AllureClient

# Constants
BATCH_SIZE = 10

async def process_migration(
    csv_file: str, 
    project_id: int, 
    api_endpoint: str, 
    api_token: str, 
    dry_run: bool, 
    batch_size: int,
    insecure: bool,
    logger
):
    """
    Orchestrates the migration process.
    """
    reader = CsvReader(csv_file)
    transformer = TestCaseTransformer(project_id)
    client = AllureClient(api_endpoint, api_token, insecure=insecure)

    try:
        reader.validate()
        total_rows = reader.count_rows()
        logger.info(f"Starting migration for Project ID: {project_id}")
        logger.info(f"Found {total_rows} test cases in {csv_file}")

        migrated_count = 0
        failed_count = 0
        tasks = []

        async with aiohttp.ClientSession() as session:
            for i, row in enumerate(reader.read(), 1):
                try:
                    payload = transformer.transform(row)
                    test_name = payload.get('name', f'TestCase_{i}')
                    
                    # Log the full payload for visibility
                    import json
                    logger.info(f"--- PREPARING MIGRATION: {test_name} ---")
                    logger.info(f"Payload structure:\n{json.dumps(payload, indent=2)}")
                    logger.info(f"API Call: POST {api_endpoint}")
                    
                    if dry_run:
                        logger.info(f"[DRY RUN] Would migrate: {test_name}")
                        migrated_count += 1
                        continue

                    # Create a task for each migration
                    task = asyncio.create_task(client.migrate_test_case(session, payload))
                    tasks.append(task)

                    # Process in batches to control concurrency
                    if len(tasks) >= batch_size:
                        results = await asyncio.gather(*tasks)
                        migrated_count += results.count(True)
                        failed_count += results.count(False)
                        tasks = [] 
                        
                except Exception as e:
                    logger.error(f"Error processing row {i}: {e}")
                    failed_count += 1

            # Process remaining tasks
            if tasks:
                results = await asyncio.gather(*tasks)
                migrated_count += results.count(True)
                failed_count += results.count(False)

        # Summary
        total_processed = migrated_count + failed_count
        success_rate = (migrated_count / total_processed * 100) if total_processed > 0 else 0
        
        logger.info("="*50)
        logger.info("Migration Summary")
        logger.info("="*50)
        logger.info(f"Total processed: {total_processed}")
        logger.info(f"Successfully migrated: {migrated_count}")
        if failed_count > 0:
            logger.info(f"Failed migrations: {failed_count}")
        logger.info(f"Success rate: {success_rate:.1f}%")
        logger.info("="*50)

        return failed_count == 0

    except Exception as e:
        logger.critical(f"Fatal error during migration: {e}")
        return False

@click.command()
@click.option('--csv-file', '-f', default=DEFAULT_CSV_PATH, help='Path to CSV file')
@click.option('--project-id', '-p', default=DEFAULT_PROJECT_ID, type=int, help='Allure Project ID')
@click.option('--api-endpoint', '-e', default=DEFAULT_API_ENDPOINT, help='API Endpoint')
@click.option('--api-token', '-t', envvar='ALLURE_API_TOKEN', help='Allure API Token')
@click.option('--dry-run', '-d', is_flag=True, help='Dry run mode')
@click.option('--verbose', '-v', is_flag=True, help='Verbose logging')
@click.option('--batch-size', '-b', default=BATCH_SIZE, type=int, help='Concurrency batch size')
@click.option('--insecure', '-k', is_flag=True, help='Disable SSL certificate verification')
def main(csv_file, project_id, api_endpoint, api_token, dry_run, verbose, batch_size, insecure):
    """
    Migrate test cases from CSV to Allure TestOps.
    """
    logger = setup_logger(verbose=verbose)

    if insecure:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        logger.warning("SSL certificate verification disabled!")

    if not api_token and not dry_run:
        logger.critical("API token is required (except for dry-run). Set ALLURE_API_TOKEN env var or use --api-token.")
        sys.exit(1)

    # placeholder for dry run token if needed
    if dry_run and not api_token:
        api_token = "dummy_token"

    success = asyncio.run(process_migration(
        csv_file, project_id, api_endpoint, api_token, dry_run, batch_size, insecure, logger
    ))
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()

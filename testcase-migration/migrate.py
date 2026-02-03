# migrate.py

import csv
import json
import requests
import os
import sys
from typing import Dict, List, Any, Optional
from pathlib import Path
import click
from config import (
    ALLURE_BASE_URL, 
    PROJECT_ID as DEFAULT_PROJECT_ID, 
    TESTCASE_API_ENDPOINT as DEFAULT_API_ENDPOINT, 
    CSV_FILE_PATH as DEFAULT_CSV_PATH, 
    FIELD_MAPPING, 
    STEP_SEPARATOR, 
    ACTION_EXPECTED_SEPARATOR
)

# --- Constants ---
REQUEST_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
BATCH_SIZE = 10  # Process in batches for better performance

def validate_environment() -> Optional[str]:
    """Validate environment and return API token if available."""
    return os.environ.get("ALLURE_API_TOKEN")

def parse_steps(steps_str: str) -> List[Dict[str, str]]:
    """
    Transforms a single string of steps (from CSV) into the required 
    list of step objects for the Allure TestOps API.
    """
    if not steps_str or not steps_str.strip():
        return []
        
    steps_list = []
    raw_steps = steps_str.split(STEP_SEPARATOR)
    
    for raw_step in raw_steps:
        raw_step = raw_step.strip()
        if not raw_step:
            continue
            
        if ACTION_EXPECTED_SEPARATOR in raw_step:
            try:
                action, expected = raw_step.split(ACTION_EXPECTED_SEPARATOR, 1)
                steps_list.append({
                    "name": action.strip(),
                    "expectedResult": expected.strip()
                })
            except ValueError:
                click.echo(click.style(f"Warning: Could not parse step: {raw_step}", fg='yellow'))
                steps_list.append({"name": raw_step, "expectedResult": ""})
        else:
            steps_list.append({"name": raw_step, "expectedResult": ""})
            
    return steps_list

def create_allure_payload(row_data: Dict[str, str], project_id: int) -> Dict[str, Any]:
    """
    Constructs the final JSON payload for the Allure TestOps API.
    """
    payload = {
        "project": {"id": project_id},
        "steps": [],
        "tags": [],
        "description": ""
    }

    for csv_key, api_key in FIELD_MAPPING.items():
        value = row_data.get(csv_key)
        if not value or not value.strip():
            continue
            
        value = value.strip()
        
        if api_key == "description_preconditions":
            payload["description"] += f"**Preconditions:**\n{value}\n\n"
        elif api_key == "description_steps":
            payload["steps"] = parse_steps(value)
        elif api_key == "tags":
            # Filter out empty tags
            tags = [tag.strip() for tag in value.split(',') if tag.strip()]
            payload["tags"] = [{"name": tag} for tag in tags]
        elif api_key == "priority":
            payload[api_key] = value.upper()
        else:
            payload[api_key] = value
            
    return payload

def migrate_test_case_with_retry(payload: Dict[str, Any], api_endpoint: str, 
                                api_token: str, max_retries: int = MAX_RETRIES) -> bool:
    """
    Sends the payload to the Allure TestOps API with retry logic.
    """
    headers = {
        "Authorization": f"Api-Token {api_token}",
        "Content-Type": "application/json"
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(
                api_endpoint, 
                headers=headers, 
                json=payload,  # Use json parameter instead of data
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                test_name = payload.get('name', 'Unknown')
                click.echo(click.style(
                    f"✓ SUCCESS: '{test_name}' migrated. ID: {result.get('id')}, "
                    f"External ID: {result.get('externalId')}", 
                    fg='green'
                ))
                return True
            elif response.status_code == 429:  # Rate limit
                click.echo(click.style(f"Rate limited, retrying in {2**attempt} seconds...", fg='yellow'))
                import time
                time.sleep(2**attempt)
                continue
            else:
                test_name = payload.get('name', 'Unknown')
                click.echo(click.style(f"✗ FAILURE: '{test_name}'", fg='red'))
                click.echo(f"Status: {response.status_code}, Response: {response.text[:200]}")
                return False

        except requests.exceptions.Timeout:
            click.echo(click.style(f"Timeout on attempt {attempt + 1}, retrying...", fg='yellow'))
        except requests.exceptions.RequestException as e:
            click.echo(click.style(f"Request error on attempt {attempt + 1}: {e}", fg='red'))
            
        if attempt < max_retries - 1:
            import time
            time.sleep(1)  # Brief pause before retry
    
    click.echo(click.style(f"Failed after {max_retries} attempts", fg='red'))
    return False

def validate_csv_file(csv_file: str) -> None:
    """Validate CSV file exists and is readable."""
    csv_path = Path(csv_file)
    if not csv_path.exists():
        raise click.ClickException(f"CSV file not found: {csv_file}")
    if not csv_path.is_file():
        raise click.ClickException(f"Path is not a file: {csv_file}")

def count_csv_rows(csv_file: str) -> int:
    """Count total rows in CSV for progress tracking."""
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return sum(1 for row in reader if any(row.values()))
    except Exception:
        return 0

@click.command()
@click.option('--csv-file', '-f', 
              default=DEFAULT_CSV_PATH, 
              type=click.Path(exists=True),
              help='Path to the CSV file containing test cases')
@click.option('--project-id', '-p', 
              default=DEFAULT_PROJECT_ID,
              type=int,
              help='Allure TestOps Project ID')
@click.option('--api-endpoint', '-e', 
              default=DEFAULT_API_ENDPOINT, 
              help='Allure TestOps API endpoint URL')
@click.option('--api-token', '-t', 
              envvar='ALLURE_API_TOKEN',
              help='Allure API Token (can be set via ALLURE_API_TOKEN env var)')
@click.option('--dry-run', '-d', 
              is_flag=True, 
              help='Show what would be migrated without actually doing it')
@click.option('--verbose', '-v', 
              is_flag=True, 
              help='Enable verbose output')
@click.option('--batch-size', '-b',
              default=BATCH_SIZE,
              type=int,
              help='Number of test cases to process in each batch')
def migrate(csv_file: str, project_id: int, api_endpoint: str, 
           api_token: Optional[str], dry_run: bool, verbose: bool, batch_size: int):
    """
    Migrate test cases from CSV to Allure TestOps.
    
    This tool reads test cases from a CSV file and migrates them to Allure TestOps
    using the REST API. Configure your CSV file path and API credentials before running.
    """
    
    # Validate API token
    if not api_token:
        api_token = validate_environment()
        if not api_token:
            click.echo(click.style("FATAL: API token not provided via --api-token or ALLURE_API_TOKEN env var", fg='red', bold=True))
            sys.exit(1)
    
    # Validate inputs
    validate_csv_file(csv_file)
    
    if dry_run:
        click.echo(click.style("🔍 DRY RUN MODE: No actual migration will be performed", fg='yellow', bold=True))
    
    # Count total rows for progress tracking
    total_rows = count_csv_rows(csv_file)
    click.echo(f"📊 Starting migration to Allure TestOps Project ID: {project_id}")
    click.echo(f"📁 Found {total_rows} test cases to process")
    
    if verbose:
        click.echo(f"📄 CSV File: {csv_file}")
        click.echo(f"🌐 API Endpoint: {api_endpoint}")
        click.echo(f"🎯 Project ID: {project_id}")
        click.echo(f"📦 Batch Size: {batch_size}")
    
    migrated_count = 0
    failed_count = 0
    current_batch = []
    
    try:
        with open(csv_file, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            with click.progressbar(reader, length=total_rows, 
                                 label='Processing test cases') as progress_reader:
                
                for i, row in enumerate(progress_reader, 1):
                    # Skip empty rows
                    if not any(row.values()):
                        continue
                        
                    test_case_name = row.get('Title', f'TestCase_{i}')
                    
                    if verbose:
                        click.echo(f"\n🔄 Processing ({i}/{total_rows}): {test_case_name}")
                    
                    # Transform data
                    try:
                        payload = create_allure_payload(row, project_id)
                        current_batch.append((payload, test_case_name))
                    except Exception as e:
                        click.echo(click.style(f"✗ Error creating payload for '{test_case_name}': {e}", fg='red'))
                        failed_count += 1
                        continue
                    
                    # Process batch when it's full
                    if len(current_batch) >= batch_size:
                        if dry_run:
                            for payload, name in current_batch:
                                click.echo(click.style(f"📝 Would migrate: {name}", fg='blue'))
                                if verbose:
                                    click.echo(f"Payload preview: {json.dumps(payload, indent=2)[:200]}...")
                            migrated_count += len(current_batch)
                        else:
                            # Process the batch
                            for payload, name in current_batch:
                                if migrate_test_case_with_retry(payload, api_endpoint, api_token):
                                    migrated_count += 1
                                else:
                                    failed_count += 1
                        
                        current_batch = []
                
                # Process remaining items in the last batch
                if current_batch:
                    if dry_run:
                        for payload, name in current_batch:
                            click.echo(click.style(f"📝 Would migrate: {name}", fg='blue'))
                        migrated_count += len(current_batch)
                    else:
                        for payload, name in current_batch:
                            if migrate_test_case_with_retry(payload, api_endpoint, api_token):
                                migrated_count += 1
                            else:
                                failed_count += 1

    except Exception as e:
        click.echo(click.style(f"FATAL: An unexpected error occurred: {e}", fg='red', bold=True))
        raise click.ClickException(str(e))

    # Enhanced summary
    total_processed = migrated_count + failed_count
    success_rate = (migrated_count / total_processed * 100) if total_processed > 0 else 0
    
    click.echo("\n" + "="*50)
    click.echo(click.style("📈 Migration Summary", fg='cyan', bold=True))
    click.echo("="*50)
    click.echo(f"📊 Total rows processed: {total_processed}")
    click.echo(click.style(f"✅ Successfully migrated: {migrated_count}", fg='green'))
    if failed_count > 0:
        click.echo(click.style(f"❌ Failed migrations: {failed_count}", fg='red'))
    click.echo(f"📈 Success rate: {success_rate:.1f}%")
    click.echo("="*50)
    
    # Exit with appropriate code
    sys.exit(0 if failed_count == 0 else 1)

if __name__ == "__main__":
    migrate()

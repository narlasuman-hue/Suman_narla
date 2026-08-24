# CLI Reference Guide

The Database Metadata Catalog provides a comprehensive CLI for managing metadata operations, lifecycle management, and reporting.

## Installation

The CLI is included with the main application. Make sure you have the virtual environment activated:

```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

## Available Commands

### Initialize Database

```bash
python -m src.cli init
```

Initializes the catalog database with the required schema.

### Synchronization

#### Sync Metadata from Teradata

```bash
python -m src.cli sync
```

Synchronizes all metadata from Teradata to the catalog database:
- Databases and tables
- Columns and their definitions
- Views
- Table statistics (size, row count, last accessed)

Options:
- `--no-stats`: Skip table statistics collection (speeds up sync)

Example:
```bash
python -m src.cli sync --no-stats
```

### Reporting

#### Get Catalog Summary

```bash
python -m src.cli summary
```

Displays overall catalog statistics:
- Total number of tables
- Count by status (active, inactive, deprecated, decommissioned)
- Total storage used

Example output:
```
Catalog Summary
========================================
Total Tables: 1,250
  Active: 1,100
  Inactive: 100
  Deprecated: 40
  Decommissioned: 10

Total Storage: 5,234.50 MB
```

#### List Unused Assets

```bash
python -m src.cli unused-assets [OPTIONS]
```

Identifies assets that haven't been accessed for a specified period.

Options:
- `--days INTEGER`: Number of days of inactivity (default: 90)

Examples:
```bash
# Find assets unused for 90 days
python -m src.cli unused-assets

# Find assets unused for 6 months
python -m src.cli unused-assets --days 180
```

#### List Decommissioning Candidates

```bash
python -m src.cli decommissioning-candidates [OPTIONS]
```

Identifies assets that are candidates for decommissioning based on extended non-use.

Options:
- `--days INTEGER`: Number of days of inactivity (default: 180)

Examples:
```bash
# Find tables unused for 180 days
python -m src.cli decommissioning-candidates

# Find tables unused for 1 year
python -m src.cli decommissioning-candidates --days 365
```

Output includes:
- Table name
- Database
- Creation and last access dates
- Size and row count
- Current lifecycle status

### Lifecycle Management

#### Mark Asset as Deprecated

```bash
python -m src.cli deprecate TABLE_ID [OPTIONS]
```

Marks a table for future decommissioning without immediately removing it.

Arguments:
- `TABLE_ID`: ID of the table to deprecate

Options:
- `--reason TEXT`: Reason for deprecation

Examples:
```bash
python -m src.cli deprecate 42

python -m src.cli deprecate 42 --reason "Replaced by new_table_v2"
```

#### Decommission Asset

```bash
python -m src.cli decommission TABLE_ID [OPTIONS]
```

Permanently decommissions a table. Requires confirmation.

Arguments:
- `TABLE_ID`: ID of the table to decommission

Options:
- `--reason TEXT`: Reason for decommissioning

Examples:
```bash
python -m src.cli decommission 42

python -m src.cli decommission 42 --reason "End of support"
```

The command will prompt for confirmation:
```
Are you sure you want to decommission table 42? [y/N]: y
✓ Table 42 decommissioned
```

## Workflow Examples

### Complete Asset Lifecycle

1. **Initial Sync**
   ```bash
   python -m src.cli sync
   ```

2. **Review Summary**
   ```bash
   python -m src.cli summary
   ```

3. **Identify Unused Assets**
   ```bash
   python -m src.cli unused-assets --days 90
   ```

4. **Check Decommissioning Candidates**
   ```bash
   python -m src.cli decommissioning-candidates --days 180
   ```

5. **Mark for Deprecation**
   ```bash
   python -m src.cli deprecate 123 --reason "No longer needed"
   ```

6. **Decommission After Review Period**
   ```bash
   python -m src.cli decommission 123 --reason "End of lifecycle"
   ```

### Scheduled Sync

To run metadata sync on a schedule, use the built-in scheduler (starts automatically with the API server):

```bash
# The scheduler will sync metadata every hour (configurable)
python main.py
```

Or create a cron job:

```bash
# Add to crontab to sync daily at 2 AM
0 2 * * * cd /path/to/project && python -m src.cli sync >> logs/sync.log 2>&1
```

### Custom Reporting

Combine CLI commands with standard Unix tools for custom reporting:

```bash
# Get unused assets and save to file
python -m src.cli unused-assets --days 90 > unused_assets.txt

# Count deprecated assets
python -m src.cli decommissioning-candidates --days 365 | grep "deprecated" | wc -l
```

## Exit Codes

- `0`: Success
- `1`: Error (check output for details)

## Logging

CLI operations are logged to the file specified in `LOG_FILE` configuration (default: `logs/app.log`).

Enable verbose logging by setting `LOG_LEVEL=DEBUG` in `.env`:

```bash
LOG_LEVEL=DEBUG python -m src.cli sync
```

## Configuration

All CLI commands use the configuration from `.env` file:

- `CATALOG_DB_*`: Catalog database connection settings
- `TERADATA_*`: Teradata connection settings (required for sync)
- `LOG_LEVEL`: Logging verbosity
- `LOG_FILE`: Log file location

## Tips & Best Practices

1. **Always review before decommissioning**: Use `unused-assets` and `decommissioning-candidates` to thoroughly review before marking assets for decommission.

2. **Use deprecation as a staging step**: Mark assets as deprecated first, allow a review period, then decommission.

3. **Document reasons**: Always provide a `--reason` when deprecating or decommissioning for audit trails.

4. **Backup before major operations**: Ensure database backups are in place before running bulk operations.

5. **Schedule regular syncs**: Run sync operations during off-peak hours to minimize impact on Teradata.

6. **Monitor logs**: Check `logs/app.log` regularly for any sync errors or warnings.

## Troubleshooting

### "Teradata connector not initialized"

Make sure:
- Teradata credentials in `.env` are correct
- Teradata server is accessible and running
- Network connectivity is available

### "Database connection error"

Check:
- PostgreSQL is running
- Connection settings in `.env` are correct
- Database user has proper permissions

### Slow sync performance

Try:
- Running sync during off-peak hours
- Using `--no-stats` flag to skip statistics collection
- Reducing the number of tables to sync

For more help, check the logs:
```bash
tail -f logs/app.log
```

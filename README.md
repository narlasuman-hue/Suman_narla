# Suman_narla - Teradata to AWS Migration Project

A comprehensive Python project for migrating Teradata tables to AWS cloud infrastructure.

## Overview

This project provides tools and utilities for extracting data from Teradata databases and loading it into AWS services including S3, Glue, and Athena.

## Features

- **Table Extraction**: Batch extraction of Teradata tables to S3
- **Schema Management**: Automatic schema detection and Glue catalog registration
- **Data Validation**: Quality checks and data integrity validation
- **Configurable**: YAML-based configuration for tables and migration parameters
- **Parallel Processing**: Support for parallel extractions
- **CLI Interface**: Easy-to-use command-line tools

## Quick Start

### Setup

1. Clone the repository and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
```

2. Configure your Teradata and AWS credentials:
```bash
export TERADATA_HOST=your-teradata-host
export TERADATA_USER=your-username
export TERADATA_PASSWORD=your-password
export AWS_GLUE_ROLE_ARN=arn:aws:iam::account:role/glue-role
```

3. Edit configuration file:
```bash
cp config/migration_config.yaml config/migration_config.local.yaml
# Edit config/migration_config.local.yaml with your settings
```

### Usage

Extract all enabled tables:
```bash
python -m migration extract --config config/migration_config.yaml
```

Extract specific table:
```bash
python -m migration extract --table schema.table_name --config config/migration_config.yaml
```

Validate extracted data:
```bash
python -m migration validate --config config/migration_config.yaml
```

Check migration status:
```bash
python -m migration status --config config/migration_config.yaml
```

## Project Structure

```
├── docs/
│   ├── MIGRATION_GUIDE.md     # Detailed migration documentation
│   └── README.md
├── config/
│   └── migration_config.yaml  # Migration configuration template
├── src/
│   └── migration/             # Main migration module
│       ├── __init__.py
│       ├── __main__.py        # CLI entry point
│       ├── cli.py             # Command-line interface
│       ├── config.py          # Configuration management
│       ├── teradata_client.py # Teradata connection & queries
│       ├── aws_client.py      # AWS S3 & Glue operations
│       ├── extractor.py       # Data extraction logic
│       └── validator.py       # Data validation
├── tests/
│   ├── test_migration_config.py
│   ├── test_extractor.py
│   └── test_example.py
├── scripts/
│   └── example_script.py
├── pyproject.toml
├── requirements-dev.txt
└── README.md
```

## Configuration

The migration is configured via `config/migration_config.yaml`. Key settings:

- **Teradata Connection**: Host, port, credentials
- **AWS Configuration**: Region, S3 buckets, Glue role
- **Migration Parameters**: Batch size, output format, compression
- **Tables**: List of tables to migrate with status

See `docs/MIGRATION_GUIDE.md` for detailed configuration options.

## Testing

Run the test suite:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=src tests/
```

## Development

### Code Style

- Follow PEP 8 conventions
- Use type hints
- Maximum line length: 100 characters
- Run linting: `ruff check .`
- Format code: `ruff format .`

### Git Workflow

- Create feature branches: `feature/<name>` or `fix/<name>`
- Use descriptive commit messages
- All changes go through pull requests

## Migration Workflow

Refer to `docs/MIGRATION_GUIDE.md` for detailed information about:
- Assessment and planning
- Infrastructure setup
- Data extraction
- Validation
- Testing and cutover

## Dependencies

- **boto3**: AWS SDK for Python
- **pandas**: Data manipulation
- **teradatasql**: Teradata Python driver
- **pyyaml**: YAML configuration parsing
- **pytest**: Testing framework

## License

Mozilla Public License 2.0 - See LICENSE file for details

## Support

For issues or questions about the migration process, refer to `docs/MIGRATION_GUIDE.md` or contact the project maintainers.

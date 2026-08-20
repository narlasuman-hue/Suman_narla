# Migration Documentation

Complete documentation for the Teradata to AWS migration framework.

## Quick Links

- **[Migration Guide](MIGRATION_GUIDE.md)** - Overview, phases, and workflow
- **[API Reference](API_REFERENCE.md)** - Complete API documentation for all modules
- **[Architecture](ARCHITECTURE.md)** - System design, patterns, and scalability
- **[Operations](OPERATIONS.md)** - Deployment, configuration, and troubleshooting

---

## Documentation Structure

### For Getting Started

Start here if you're new to the project:

1. Read [Migration Guide](MIGRATION_GUIDE.md) - High-level overview
2. Follow [Operations](OPERATIONS.md) - Deployment section
3. Run tests to verify setup
4. Extract first table

### For Developers

Understanding the codebase:

1. Review [Architecture](ARCHITECTURE.md) - System design and patterns
2. Study [API Reference](API_REFERENCE.md) - Module interfaces
3. Examine test files - `tests/test_*.py`
4. Run tests with coverage: `pytest --cov=src`

### For Operations

Running and maintaining the system:

1. [Operations Guide](OPERATIONS.md) - Complete operations manual
2. [Migration Guide - Common Tasks](MIGRATION_GUIDE.md#common-tasks)
3. Reference [API Reference](API_REFERENCE.md) for CLI commands

### For Troubleshooting

Finding solutions to problems:

1. [Operations - Troubleshooting](OPERATIONS.md#troubleshooting)
2. [Operations - Common Errors](OPERATIONS.md#common-errors)
3. Search documentation for error message

---

## Document Summaries

### [Migration Guide](MIGRATION_GUIDE.md)

**Purpose**: Overview of the migration process and phases

**Contents**:
- Project overview and goals
- 6-phase migration workflow
- Configuration reference
- Common operational tasks
- Troubleshooting tips
- External references

**Best for**: Understanding the big picture, getting started

---

### [API Reference](API_REFERENCE.md)

**Purpose**: Complete API documentation for all modules

**Contents**:
- Configuration module (`migration.config`)
- Teradata client (`migration.teradata_client`)
- AWS clients (`migration.aws_client`)
- Extractor (`migration.extractor`)
- Validator (`migration.validator`)
- CLI interface (`migration.cli`)
- Configuration file format
- Error handling
- Complete usage examples

**Best for**: Developers, API consumers, integration

---

### [Architecture](ARCHITECTURE.md)

**Purpose**: Detailed system design and technical documentation

**Contents**:
- System overview and goals
- Architecture diagram
- Component design for each module
- Data flow diagrams
- Technology stack
- Design patterns used
- Scalability considerations
- Error handling strategy
- Security considerations
- Monitoring and observability
- Future enhancements

**Best for**: Architects, developers, advanced usage

---

### [Operations](OPERATIONS.md)

**Purpose**: Complete deployment and operations manual

**Contents**:
- Deployment steps and prerequisites
- AWS infrastructure setup
- Network configuration
- Configuration management
- Step-by-step migration workflow
- Monitoring and metrics
- Comprehensive troubleshooting guide
- Maintenance procedures
- Best practices
- Troubleshooting workflow

**Best for**: Operations, DevOps, system administrators

---

## Quick Reference

### File Locations

```
docs/
├── README.md                 # This file
├── MIGRATION_GUIDE.md        # Migration process overview
├── API_REFERENCE.md          # Complete API documentation
├── ARCHITECTURE.md           # System design and patterns
└── OPERATIONS.md             # Deployment and operations

config/
└── migration_config.yaml     # Configuration template

src/migration/
├── __init__.py              # Package initialization
├── __main__.py              # CLI entry point
├── cli.py                   # Command-line interface
├── config.py                # Configuration management
├── teradata_client.py       # Teradata database client
├── aws_client.py            # AWS S3 and Glue clients
├── extractor.py             # Data extraction orchestrator
└── validator.py             # Data validation

tests/
├── test_migration_config.py # Configuration tests
└── test_extractor.py        # Extraction tests

.env.example                 # Environment variables template
requirements-dev.txt         # Python dependencies
```

### Common Commands

```bash
# View status of tables
python -m migration status --config config/migration_config.yaml

# Extract all tables
python -m migration extract --config config/migration_config.yaml

# Extract specific table
python -m migration extract --table schema.table_name

# Validate data quality
python -m migration validate --config config/migration_config.yaml

# Run tests
pytest tests/ -v

# Run tests with coverage
pytest --cov=src --cov-report=html tests/
```

### Key Concepts

**Batch Extraction**: Data extracted in chunks (default 10,000 rows) for memory efficiency

**S3 Zones**:
- **Raw**: Original extracted data in Parquet/CSV/JSON format
- **Processed**: Transformed data (future enhancement)
- **Metadata**: Extraction metadata and schemas

**Glue Catalog**: AWS metadata registry mapping S3 data to queryable tables in Athena

**Validation**: Automated checks for row counts, schemas, and data integrity

---

## Troubleshooting Quick Links

| Problem | Document | Section |
|---------|----------|---------|
| Can't connect to Teradata | Operations | [Connection Issues](OPERATIONS.md#connection-issues) |
| S3 upload failing | Operations | [S3 Upload Fails](OPERATIONS.md#s3-upload-fails) |
| Row count mismatch | Operations | [Row Count Mismatch](OPERATIONS.md#row-count-mismatch) |
| Slow extraction | Operations | [Slow Extraction](OPERATIONS.md#slow-extraction) |
| High memory usage | Operations | [High Memory Usage](OPERATIONS.md#high-memory-usage) |
| CLI not working | API Reference | [CLI Interface](API_REFERENCE.md#cli-interface) |
| Configuration error | Operations | [Configuration](OPERATIONS.md#configuration) |

---

## Learning Path

### Beginner (Just Getting Started)

1. Read: [Migration Guide](MIGRATION_GUIDE.md) - Overview section
2. Read: [Operations](OPERATIONS.md) - Deployment section
3. Do: Follow deployment steps
4. Do: Run first test extraction
5. Reference: [API Reference](API_REFERENCE.md) - CLI commands

### Intermediate (Regular Operations)

1. Understand: [Architecture](ARCHITECTURE.md) - Components section
2. Learn: [Operations](OPERATIONS.md) - Monitoring section
3. Practice: Multi-table extractions
4. Master: Configuration customization
5. Reference: [API Reference](API_REFERENCE.md) - Full module docs

### Advanced (Development/Optimization)

1. Study: [Architecture](ARCHITECTURE.md) - Complete document
2. Deep dive: [API Reference](API_REFERENCE.md) - Complete API
3. Code review: `src/migration/` - All modules
4. Implement: Custom extensions
5. Optimize: Performance tuning per [Architecture - Scalability](ARCHITECTURE.md#scalability-considerations)

---

## Documentation Version

**Last Updated**: August 20, 2024
**Documentation Version**: 1.0
**Framework Version**: 0.1.0

---

## Next Steps

- **New to the project?** → Start with [Migration Guide](MIGRATION_GUIDE.md)
- **Setting up?** → Follow [Operations - Deployment](OPERATIONS.md#deployment)
- **Developing?** → Read [Architecture](ARCHITECTURE.md)
- **Troubleshooting?** → Check [Operations - Troubleshooting](OPERATIONS.md#troubleshooting)
- **Using the API?** → Reference [API Reference](API_REFERENCE.md)

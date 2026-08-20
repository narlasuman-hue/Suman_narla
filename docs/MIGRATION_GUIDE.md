# Teradata to AWS Migration Guide

## Overview

This guide documents the migration of Teradata tables to AWS cloud infrastructure, specifically using AWS S3, Glue, and Athena services.

## Migration Architecture

### Components

- **Source**: Teradata Database (on-premises or managed service)
- **Target**: AWS Data Lake on S3
- **Processing**: AWS Glue for ETL operations
- **Querying**: Amazon Athena for SQL queries

### Data Flow

```
Teradata → Extraction Layer → AWS S3 (Raw) → AWS Glue → S3 (Processed) → Athena Queries
```

## Migration Phases

### Phase 1: Assessment & Planning
- [ ] Inventory all Teradata tables
- [ ] Document table schemas and row counts
- [ ] Identify dependencies and relationships
- [ ] Estimate data volume and transfer time
- [ ] Plan partition strategy

### Phase 2: Setup Infrastructure
- [ ] Create AWS S3 buckets (raw, processed, metadata)
- [ ] Configure IAM roles and policies
- [ ] Set up AWS Glue catalogs
- [ ] Configure network connectivity (VPN/Direct Connect if needed)

### Phase 3: Data Extraction
- [ ] Extract table metadata
- [ ] Export data in batches
- [ ] Validate data integrity
- [ ] Handle incremental updates

### Phase 4: Data Loading
- [ ] Load data to S3 raw zone
- [ ] Register metadata in Glue Catalog
- [ ] Run quality checks

### Phase 5: Transformation & Validation
- [ ] Create Glue jobs for data transformation
- [ ] Validate data against source
- [ ] Handle edge cases and data quality issues

### Phase 6: Testing & Cutover
- [ ] Parallel run queries on source and target
- [ ] Performance testing
- [ ] User acceptance testing
- [ ] Cutover execution

## Configuration

See `config/migration_config.yaml` for detailed configuration parameters.

## Common Tasks

### Extract Single Table
```bash
python -m migration extract --table <table_name> --config config/migration_config.yaml
```

### Validate Data
```bash
python -m migration validate --table <table_name>
```

### Load to S3
```bash
python -m migration load --table <table_name> --format parquet
```

## Troubleshooting

### Connection Issues
- Verify Teradata connection string
- Check network connectivity
- Validate credentials

### Data Quality
- Review logs in `logs/` directory
- Compare row counts before/after
- Check for NULL handling differences

## References

- [AWS Glue Documentation](https://docs.aws.amazon.com/glue/)
- [Amazon Athena Documentation](https://docs.aws.amazon.com/athena/)
- [Teradata SQL Reference](https://docs.teradata.com/)

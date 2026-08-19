# Data Directory

This directory contains sample data and data-related scripts.

## Structure

- `sample/` - Sample data files for development and testing
  - `users.csv` - Sample user data with 8 records (includes duplicates)
  - `posts.csv` - Sample post data with 10 records (includes duplicates)
  - `comments.csv` - Sample comment data with 14 records (includes duplicates)

## Loading Sample Data

To load the sample data into your database:

```bash
python scripts/load_sample_data.py
```

This will:
1. Create the database tables if they don't exist
2. Load all sample data from CSV files
3. Display statistics showing records loaded

The sample data includes intentional duplicates for testing the duplicate detection scripts:
- Duplicate usernames: "alice_smith" appears twice
- Duplicate post titles: "Getting Started with Python" appears twice
- Duplicate comments: Some identical comments from different users

## CSV File Format

### users.csv
- `id` - User identifier
- `username` - Unique username
- `email` - Unique email address
- `password_hash` - Hashed password (sample values)

### posts.csv
- `id` - Post identifier
- `user_id` - Reference to user who created the post
- `title` - Post title
- `content` - Post content/body

### comments.csv
- `id` - Comment identifier
- `post_id` - Reference to post being commented on
- `user_id` - Reference to user who made the comment
- `content` - Comment text

## Adding More Data

To add more sample data:
1. Edit the appropriate CSV file (users.csv, posts.csv, or comments.csv)
2. Follow the existing format and column order
3. Run `python scripts/load_sample_data.py` again to reload the database

Note: The script will fail on duplicate key violations (by design) to maintain data integrity.

## Testing Duplicate Detection

After loading sample data, you can test the duplicate detection:

```bash
python scripts/export_duplicates.py
```

This will generate reports showing the intentional duplicates in the sample data.

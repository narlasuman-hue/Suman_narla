-- Find duplicates in database tables
-- This script identifies duplicate records based on various criteria

-- Find duplicate usernames
SELECT 'Duplicate Usernames' as check_type,
       username,
       COUNT(*) as count,
       GROUP_CONCAT(id) as user_ids
FROM users
GROUP BY username
HAVING COUNT(*) > 1;

-- Find duplicate emails
SELECT 'Duplicate Emails' as check_type,
       email,
       COUNT(*) as count,
       GROUP_CONCAT(id) as user_ids
FROM users
GROUP BY email
HAVING COUNT(*) > 1;

-- Find duplicate post titles by the same user (potential duplicates)
SELECT 'Duplicate Post Titles' as check_type,
       user_id,
       title,
       COUNT(*) as count,
       GROUP_CONCAT(id) as post_ids
FROM posts
GROUP BY user_id, title
HAVING COUNT(*) > 1;

-- Find identical comments by the same user on the same post
SELECT 'Duplicate Comments' as check_type,
       post_id,
       user_id,
       content,
       COUNT(*) as count,
       GROUP_CONCAT(id) as comment_ids
FROM comments
GROUP BY post_id, user_id, content
HAVING COUNT(*) > 1;

-- Find posts with identical content from same user (exact duplicates)
SELECT 'Duplicate Post Content' as check_type,
       user_id,
       COUNT(*) as count,
       GROUP_CONCAT(id) as post_ids,
       SUBSTR(content, 1, 50) as content_preview
FROM posts
GROUP BY user_id, content
HAVING COUNT(*) > 1;

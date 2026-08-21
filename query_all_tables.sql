SELECT
    b.*,
    c.*,
    d.*,
    i.*,
    p.*
FROM balt b
INNER JOIN cent c ON b.acc_idr = c.acc_idr
INNER JOIN dent d ON b.acc_idr = d.acc_idr
INNER JOIN ient i ON b.acc_idr = i.acc_idr
INNER JOIN prdt p ON b.acc_idr = p.acc_idr
WHERE b.entry_date BETWEEN '2026-01-01' AND '2026-03-31'
  AND p.product_code = 2300
ORDER BY b.acc_idr, b.entry_date;

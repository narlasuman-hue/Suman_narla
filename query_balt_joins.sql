SELECT
    b.*,
    a.*,
    bl.*,
    p.*,
    pn.*
FROM Balt b
INNER JOIN ACCT a ON b.acc_idr = a.acc_idr
INNER JOIN BLNC bl ON b.acc_idr = bl.acc_idr
INNER JOIN PRDT p ON b.acc_idr = p.acc_idr
INNER JOIN PANF pn ON b.acc_idr = pn.acc_idr
WHERE b.entry_date BETWEEN '2026-01-01' AND '2026-03-31'
  AND p.product_code = 2300
ORDER BY b.acc_idr, b.entry_date;

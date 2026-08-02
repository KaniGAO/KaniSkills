-- 参考数据种子（幂等：使用 INSERT OR IGNORE）
-- 央行预期利率（替代 report.py 中硬编码的 "TBD"）
INSERT OR IGNORE INTO expected_central_bank (region, meeting_date, expected_rate) VALUES
    ('Eurozone', '2026-07-23', '2.25% hold'),
    ('US',       '2026-07-28-29', '3.50-3.75% hold (25bp cut unlikely)'),
    ('UK',       '2026-07-30', '4.00% hold'),
    ('Japan',    '2026-07-30-31', '0.50% (hike watch)'),
    ('China',    '2026-08-20', '3.10% LPR hold'),
    ('Canada',   '2026-09-09', '2.75% hold'),
    ('Eurozone', '2026-09-10', '2.25% hold'),
    ('US',       '2026-09-17', 'TBD (data-dependent)'),
    ('Japan',    '2026-09-18', '0.50-0.75% (hike watch)'),
    ('UK',       '2026-09-19', '4.00% hold'),
    ('China',    '2026-09-20', '3.10% LPR hold');

-- 财报日历（修正 Alphabet Q2 日期为 2026-07-22）
INSERT OR IGNORE INTO earnings_calendar (ticker, report_date, confirmed) VALUES
    ('GOOGL', '2026-07-22', 1),
    ('TSLA',  '2026-07-22', 1),
    ('INTC',  '2026-07-23', 1);

-- ============================================================================
-- MSSQL — Incremental Demo Changes
-- ============================================================================
-- Run this in SSMS / Azure Data Studio AFTER the initial FULL migration.
-- Simulates real-world changes: updates + inserts on Customers and Orders.
-- ============================================================================

USE TestDB;
GO


-- ╔══════════════════════════════════════════════════════════════════════════════╗
-- ║  STEP 1: UPDATE existing Customers (simulate profile changes)               ║
-- ╚══════════════════════════════════════════════════════════════════════════════╝

-- Update 50 customers (change email, phone, city)
UPDATE dbo.Customers SET
    Email = 'updated_' + CAST(CustomerID AS VARCHAR) + '@newdomain.com',
    Phone = '999-' + RIGHT('000000' + CAST(CustomerID AS VARCHAR), 7),
    City = 'UpdatedCity-' + CAST(CustomerID AS VARCHAR),
    UpdatedAt = SYSUTCDATETIME()
WHERE CustomerID IN (
    1, 2, 3, 4, 5, 10, 15, 20, 25, 30,
    50, 75, 100, 200, 300, 400, 500, 600, 700, 800,
    1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000, 5500,
    6000, 7000, 8000, 9000, 10000, 15000, 20000, 25000, 30000, 35000,
    40000, 50000, 60000, 70000, 80000, 85000, 90000, 92000, 95000, 99000
);

PRINT 'Updated 50 customers';
GO


-- ╔══════════════════════════════════════════════════════════════════════════════╗
-- ║  STEP 2: INSERT new Customers (simulate new sign-ups)                       ║
-- ╚══════════════════════════════════════════════════════════════════════════════╝

-- Insert 20 new customers
INSERT INTO dbo.Customers (FirstName, LastName, Email, Phone, City, State, Country, ZipCode, CustomerType, CreditLimit, IsActive, CreatedAt, UpdatedAt)
VALUES
    ('Demo', 'Alpha',    'demo.alpha@test.com',    '555-1001', 'New York',    'NY', 'USA',    '10001', 'Premium',  15000.00, 1, SYSUTCDATETIME(), SYSUTCDATETIME()),
    ('Demo', 'Beta',     'demo.beta@test.com',     '555-1002', 'London',      NULL, 'UK',     'EC1A',  'Standard', 5000.00,  1, SYSUTCDATETIME(), SYSUTCDATETIME()),
    ('Demo', 'Gamma',    'demo.gamma@test.com',    '555-1003', 'Mumbai',      'MH', 'India',  '400001','Premium',  12000.00, 1, SYSUTCDATETIME(), SYSUTCDATETIME()),
    ('Demo', 'Delta',    'demo.delta@test.com',    '555-1004', 'Sydney',      'NSW','Australia','2000', 'Standard', 8000.00,  1, SYSUTCDATETIME(), SYSUTCDATETIME()),
    ('Demo', 'Epsilon',  'demo.epsilon@test.com',  '555-1005', 'Toronto',     'ON', 'Canada', 'M5V',   'Premium',  20000.00, 1, SYSUTCDATETIME(), SYSUTCDATETIME()),
    ('Demo', 'Zeta',     'demo.zeta@test.com',     '555-1006', 'Berlin',      NULL, 'Germany','10115', 'Standard', 6000.00,  1, SYSUTCDATETIME(), SYSUTCDATETIME()),
    ('Demo', 'Eta',      'demo.eta@test.com',      '555-1007', 'Tokyo',       NULL, 'Japan',  '100',   'Premium',  25000.00, 1, SYSUTCDATETIME(), SYSUTCDATETIME()),
    ('Demo', 'Theta',    'demo.theta@test.com',    '555-1008', 'Paris',       NULL, 'France', '75001', 'Standard', 7000.00,  1, SYSUTCDATETIME(), SYSUTCDATETIME()),
    ('Demo', 'Iota',     'demo.iota@test.com',     '555-1009', 'Dubai',       NULL, 'UAE',    '00000', 'Premium',  30000.00, 1, SYSUTCDATETIME(), SYSUTCDATETIME()),
    ('Demo', 'Kappa',    'demo.kappa@test.com',    '555-1010', 'Singapore',   NULL, 'Singapore','048',  'Standard', 9000.00,  1, SYSUTCDATETIME(), SYSUTCDATETIME()),
    ('Demo', 'Lambda',   'demo.lambda@test.com',   '555-1011', 'São Paulo',   'SP', 'Brazil', '01310', 'Standard', 4500.00,  1, SYSUTCDATETIME(), SYSUTCDATETIME()),
    ('Demo', 'Mu',       'demo.mu@test.com',       '555-1012', 'Seoul',       NULL, 'S.Korea','04524', 'Premium',  18000.00, 1, SYSUTCDATETIME(), SYSUTCDATETIME()),
    ('Demo', 'Nu',       'demo.nu@test.com',       '555-1013', 'Amsterdam',   NULL, 'Netherlands','1012','Standard',5500.00, 1, SYSUTCDATETIME(), SYSUTCDATETIME()),
    ('Demo', 'Xi',       'demo.xi@test.com',       '555-1014', 'Melbourne',   'VIC','Australia','3000','Premium',  11000.00, 1, SYSUTCDATETIME(), SYSUTCDATETIME()),
    ('Demo', 'Omicron',  'demo.omicron@test.com',  '555-1015', 'Stockholm',   NULL, 'Sweden', '111',   'Standard', 6500.00,  1, SYSUTCDATETIME(), SYSUTCDATETIME()),
    ('Demo', 'Pi',       'demo.pi@test.com',       '555-1016', 'Zurich',      NULL, 'Switzerland','8001','Premium',35000.00,1, SYSUTCDATETIME(), SYSUTCDATETIME()),
    ('Demo', 'Rho',      'demo.rho@test.com',      '555-1017', 'Bangkok',     NULL, 'Thailand','10110','Standard', 4000.00, 1, SYSUTCDATETIME(), SYSUTCDATETIME()),
    ('Demo', 'Sigma',    'demo.sigma@test.com',    '555-1018', 'Cape Town',   'WC', 'S.Africa','8001', 'Standard', 5000.00, 1, SYSUTCDATETIME(), SYSUTCDATETIME()),
    ('Demo', 'Tau',      'demo.tau@test.com',      '555-1019', 'Mexico City', NULL, 'Mexico', '06600', 'Premium',  13000.00, 1, SYSUTCDATETIME(), SYSUTCDATETIME()),
    ('Demo', 'Upsilon',  'demo.upsilon@test.com',  '555-1020', 'Jakarta',     NULL, 'Indonesia','10110','Standard',3500.00, 1, SYSUTCDATETIME(), SYSUTCDATETIME());

PRINT 'Inserted 20 new customers';
GO


-- ╔══════════════════════════════════════════════════════════════════════════════╗
-- ║  STEP 3: INSERT new Orders (simulate recent transactions)                   ║
-- ╚══════════════════════════════════════════════════════════════════════════════╝

-- Insert 100 new orders
;WITH nums AS (
    SELECT TOP (100) ROW_NUMBER() OVER(ORDER BY (SELECT NULL)) AS n
    FROM sys.all_objects
)
INSERT INTO dbo.Orders (CustomerID, ProductID, OrderDate, ShipDate, Quantity, UnitPrice, Discount, TotalAmount, OrderStatus, PaymentMethod, ShippingMethod, Region, CreatedAt, UpdatedAt)
SELECT
    ABS(CHECKSUM(NEWID())) % 100000 + 1,  -- Random CustomerID
    ABS(CHECKSUM(NEWID())) % 5000 + 1,    -- Random ProductID
    CAST(SYSUTCDATETIME() AS DATE),        -- Today
    DATEADD(DAY, ABS(CHECKSUM(NEWID())) % 7 + 1, CAST(SYSUTCDATETIME() AS DATE)),  -- Ship in 1-7 days
    ABS(CHECKSUM(NEWID())) % 10 + 1,      -- Quantity 1-10
    CAST(ABS(CHECKSUM(NEWID())) % 500 + 10 AS DECIMAL(10,2)),  -- UnitPrice
    CAST(ABS(CHECKSUM(NEWID())) % 20 AS DECIMAL(5,2)),          -- Discount
    CAST(ABS(CHECKSUM(NEWID())) % 5000 + 50 AS DECIMAL(12,2)), -- TotalAmount
    CASE ABS(CHECKSUM(NEWID())) % 4
        WHEN 0 THEN 'Pending' WHEN 1 THEN 'Confirmed' WHEN 2 THEN 'Shipped' ELSE 'Processing'
    END,
    CASE ABS(CHECKSUM(NEWID())) % 4
        WHEN 0 THEN 'CreditCard' WHEN 1 THEN 'DebitCard' WHEN 2 THEN 'PayPal' ELSE 'BankTransfer'
    END,
    CASE ABS(CHECKSUM(NEWID())) % 3
        WHEN 0 THEN 'Standard' WHEN 1 THEN 'Express' ELSE 'Overnight'
    END,
    CASE ABS(CHECKSUM(NEWID())) % 6
        WHEN 0 THEN 'North' WHEN 1 THEN 'South' WHEN 2 THEN 'East'
        WHEN 3 THEN 'West' WHEN 4 THEN 'Central' ELSE 'International'
    END,
    SYSUTCDATETIME(),
    SYSUTCDATETIME()
FROM nums;

PRINT 'Inserted 100 new orders';
GO


-- ╔══════════════════════════════════════════════════════════════════════════════╗
-- ║  STEP 4: UPDATE some existing Orders (simulate status changes)              ║
-- ╚══════════════════════════════════════════════════════════════════════════════╝

-- Update 30 orders to "Shipped" status
UPDATE TOP (30) dbo.Orders SET
    OrderStatus = 'Shipped',
    ShipDate = CAST(SYSUTCDATETIME() AS DATE),
    UpdatedAt = SYSUTCDATETIME()
WHERE OrderStatus = 'Processing'
  AND OrderDate >= DATEADD(DAY, -30, SYSUTCDATETIME());

PRINT 'Updated 30 orders to Shipped status';
GO


-- ╔══════════════════════════════════════════════════════════════════════════════╗
-- ║  STEP 5: VERIFY — Check what changed                                        ║
-- ╚══════════════════════════════════════════════════════════════════════════════╝

-- Total counts (should be slightly more than before)
SELECT 'Customers' AS TableName, COUNT(*) AS [TotalRows] FROM dbo.Customers
UNION ALL SELECT 'Orders', COUNT(*) FROM dbo.Orders
UNION ALL SELECT 'Products', COUNT(*) FROM dbo.Products;
-- Expected: Customers=100,020 | Orders=1,000,100 | Products=5,000

-- How many rows were modified recently? (This is what incremental will extract)
SELECT 'Customers_Changed' AS Metric,
       COUNT(*) AS [RowCount]
FROM dbo.Customers
WHERE UpdatedAt >= DATEADD(MINUTE, -5, SYSUTCDATETIME());
-- Expected: 70 (50 updated + 20 new)

SELECT 'Orders_Changed' AS Metric,
       COUNT(*) AS [RowCount]
FROM dbo.Orders
WHERE UpdatedAt >= DATEADD(MINUTE, -5, SYSUTCDATETIME());
-- Expected: 130 (100 new + 30 updated)

-- Sample updated customers
SELECT TOP 5 CustomerID, Email, Phone, City, UpdatedAt
FROM dbo.Customers
WHERE CustomerID IN (1, 2, 3, 4, 5);

-- Sample new customers
SELECT TOP 5 CustomerID, FirstName, LastName, Email, City, Country
FROM dbo.Customers
WHERE FirstName = 'Demo'
ORDER BY CustomerID;

PRINT '─────────────────────────────────────────────';
PRINT 'INCREMENTAL CHANGES READY:';
PRINT '  Customers: 70 rows changed (50 updated + 20 new)';
PRINT '  Orders:   130 rows changed (30 updated + 100 new)';
PRINT '  Products: 0 changes (no incremental needed)';
PRINT '─────────────────────────────────────────────';
PRINT 'Now run INCREMENTAL migration from the Streamlit app.';
PRINT 'Expected: Only 70+130=200 rows moved (not 1.1M)';
GO

-- ============================================================================
-- MSSQL Test Data Generator — Large Volume (1M+ rows)
-- ============================================================================
-- Run this on your Azure SQL Server (TestDB) to create realistic demo data.
-- Total: ~1.1 Million rows across 3 tables
--   • CUSTOMERS:   100,000 rows
--   • ORDERS:    1,000,000 rows
--   • PRODUCTS:      5,000 rows
-- ============================================================================

USE TestDB;
GO

-- ╔══════════════════════════════════════════════════════════════════════════════╗
-- ║  TABLE 1: CUSTOMERS (100,000 rows)                                          ║
-- ╚══════════════════════════════════════════════════════════════════════════════╝

-- Drop and recreate
IF OBJECT_ID('dbo.Customers', 'U') IS NOT NULL DROP TABLE dbo.Customers;
GO

CREATE TABLE dbo.Customers (
    CustomerID      INT IDENTITY(1,1) PRIMARY KEY,
    FirstName       VARCHAR(50)   NOT NULL,
    LastName        VARCHAR(50)   NOT NULL,
    Email           VARCHAR(100)  NOT NULL,
    Phone           VARCHAR(20),
    City            VARCHAR(50),
    State           VARCHAR(30),
    Country         VARCHAR(30)   DEFAULT 'USA',
    ZipCode         VARCHAR(10),
    CustomerType    VARCHAR(20),
    CreditLimit     DECIMAL(12,2),
    IsActive        BIT           DEFAULT 1,
    CreatedAt       DATETIME2     DEFAULT SYSUTCDATETIME(),
    UpdatedAt       DATETIME2     DEFAULT SYSUTCDATETIME()
);
GO

-- Generate 100,000 customers
SET NOCOUNT ON;

DECLARE @i INT = 1;
DECLARE @batch INT = 10000;

WHILE @i <= 100000
BEGIN
    INSERT INTO dbo.Customers (FirstName, LastName, Email, Phone, City, State, Country, ZipCode, CustomerType, CreditLimit, IsActive, CreatedAt, UpdatedAt)
    SELECT TOP (@batch)
        LEFT('FName' + CAST(ROW_NUMBER() OVER(ORDER BY (SELECT NULL)) + @i - 1 AS VARCHAR), 50),
        LEFT('LName' + CAST(ROW_NUMBER() OVER(ORDER BY (SELECT NULL)) + @i - 1 AS VARCHAR), 50),
        'customer' + CAST(ROW_NUMBER() OVER(ORDER BY (SELECT NULL)) + @i - 1 AS VARCHAR) + '@company' + CAST(ABS(CHECKSUM(NEWID())) % 100 AS VARCHAR) + '.com',
        '+1-' + RIGHT('000' + CAST(ABS(CHECKSUM(NEWID())) % 999 AS VARCHAR), 3) + '-' + RIGHT('0000' + CAST(ABS(CHECKSUM(NEWID())) % 9999 AS VARCHAR), 4),
        CHOOSE(ABS(CHECKSUM(NEWID())) % 10 + 1, 'New York','Los Angeles','Chicago','Houston','Phoenix','Philadelphia','San Antonio','San Diego','Dallas','Austin'),
        CHOOSE(ABS(CHECKSUM(NEWID())) % 10 + 1, 'NY','CA','IL','TX','AZ','PA','TX','CA','TX','TX'),
        CHOOSE(ABS(CHECKSUM(NEWID())) % 5 + 1, 'USA','USA','USA','Canada','UK'),
        RIGHT('00000' + CAST(ABS(CHECKSUM(NEWID())) % 99999 AS VARCHAR), 5),
        CHOOSE(ABS(CHECKSUM(NEWID())) % 4 + 1, 'Enterprise','Business','Individual','Partner'),
        CAST(ABS(CHECKSUM(NEWID())) % 50000 + 1000 AS DECIMAL(12,2)),
        CASE WHEN ABS(CHECKSUM(NEWID())) % 100 < 90 THEN 1 ELSE 0 END,
        DATEADD(DAY, -ABS(CHECKSUM(NEWID())) % 730, SYSUTCDATETIME()),
        DATEADD(DAY, -ABS(CHECKSUM(NEWID())) % 30, SYSUTCDATETIME())
    FROM sys.all_objects a CROSS JOIN sys.all_objects b;

    SET @i = @i + @batch;
END;
GO

SELECT COUNT(*) AS CustomerCount FROM dbo.Customers;
-- Expected: 100,000
GO


-- ╔══════════════════════════════════════════════════════════════════════════════╗
-- ║  TABLE 2: PRODUCTS (5,000 rows)                                             ║
-- ╚══════════════════════════════════════════════════════════════════════════════╝

IF OBJECT_ID('dbo.Products', 'U') IS NOT NULL DROP TABLE dbo.Products;
GO

CREATE TABLE dbo.Products (
    ProductID       INT IDENTITY(1,1) PRIMARY KEY,
    ProductName     VARCHAR(100)  NOT NULL,
    Category        VARCHAR(50),
    SubCategory     VARCHAR(50),
    Brand           VARCHAR(50),
    SKU             VARCHAR(30),
    UnitPrice       DECIMAL(10,2) NOT NULL,
    CostPrice       DECIMAL(10,2),
    Weight          DECIMAL(8,2),
    IsActive        BIT           DEFAULT 1,
    CreatedAt       DATETIME2     DEFAULT SYSUTCDATETIME(),
    UpdatedAt       DATETIME2     DEFAULT SYSUTCDATETIME()
);
GO

DECLARE @p INT = 1;

WHILE @p <= 5000
BEGIN
    ;WITH nums AS (
        SELECT TOP (1000) ROW_NUMBER() OVER(ORDER BY (SELECT NULL)) AS n
        FROM sys.all_objects a CROSS JOIN sys.all_objects b
    )
    INSERT INTO dbo.Products (ProductName, Category, SubCategory, Brand, SKU, UnitPrice, CostPrice, Weight, IsActive, CreatedAt, UpdatedAt)
    SELECT
        'Product-' + CAST(n + @p - 1 AS VARCHAR) + '-' +
            CASE ABS(CHECKSUM(NEWID())) % 5
                WHEN 0 THEN 'Pro' WHEN 1 THEN 'Elite' WHEN 2 THEN 'Basic' WHEN 3 THEN 'Ultra' ELSE 'Max'
            END,
        CASE ABS(CHECKSUM(NEWID())) % 8
            WHEN 0 THEN 'Electronics' WHEN 1 THEN 'Clothing' WHEN 2 THEN 'Home' WHEN 3 THEN 'Sports'
            WHEN 4 THEN 'Food' WHEN 5 THEN 'Beauty' WHEN 6 THEN 'Toys' ELSE 'Office'
        END,
        CASE ABS(CHECKSUM(NEWID())) % 6
            WHEN 0 THEN 'Premium' WHEN 1 THEN 'Standard' WHEN 2 THEN 'Budget'
            WHEN 3 THEN 'Luxury' WHEN 4 THEN 'Eco' ELSE 'Value'
        END,
        CASE ABS(CHECKSUM(NEWID())) % 10
            WHEN 0 THEN 'BrandA' WHEN 1 THEN 'BrandB' WHEN 2 THEN 'BrandC' WHEN 3 THEN 'BrandD'
            WHEN 4 THEN 'BrandE' WHEN 5 THEN 'BrandF' WHEN 6 THEN 'BrandG' WHEN 7 THEN 'BrandH'
            WHEN 8 THEN 'BrandI' ELSE 'BrandJ'
        END,
        'SKU-' + RIGHT('00000' + CAST(n + @p - 1 AS VARCHAR), 6),
        CAST(ABS(CHECKSUM(NEWID())) % 999 + 1 AS DECIMAL(10,2)) + 0.99,
        CAST(ABS(CHECKSUM(NEWID())) % 500 + 1 AS DECIMAL(10,2)) + 0.50,
        CAST(ABS(CHECKSUM(NEWID())) % 50 AS DECIMAL(8,2)) + 0.1,
        CASE WHEN ABS(CHECKSUM(NEWID())) % 100 < 85 THEN 1 ELSE 0 END,
        DATEADD(DAY, -ABS(CHECKSUM(NEWID())) % 365, SYSUTCDATETIME()),
        DATEADD(DAY, -ABS(CHECKSUM(NEWID())) % 30, SYSUTCDATETIME())
    FROM nums;

    SET @p = @p + 1000;
END;
GO

SELECT COUNT(*) AS ProductCount FROM dbo.Products;
-- Expected: 5,000
GO


-- ╔══════════════════════════════════════════════════════════════════════════════╗
-- ║  TABLE 3: ORDERS (1,000,000 rows)                                           ║
-- ╚══════════════════════════════════════════════════════════════════════════════╝

IF OBJECT_ID('dbo.Orders', 'U') IS NOT NULL DROP TABLE dbo.Orders;
GO

CREATE TABLE dbo.Orders (
    OrderID         INT IDENTITY(1,1) PRIMARY KEY,
    CustomerID      INT           NOT NULL,
    ProductID       INT           NOT NULL,
    OrderDate       DATE          NOT NULL,
    ShipDate        DATE,
    Quantity        INT           NOT NULL,
    UnitPrice       DECIMAL(10,2) NOT NULL,
    Discount        DECIMAL(5,2)  DEFAULT 0,
    TotalAmount     DECIMAL(12,2) NOT NULL,
    OrderStatus     VARCHAR(20),
    PaymentMethod   VARCHAR(20),
    ShippingMethod  VARCHAR(20),
    Region          VARCHAR(30),
    CreatedAt       DATETIME2     DEFAULT SYSUTCDATETIME(),
    UpdatedAt       DATETIME2     DEFAULT SYSUTCDATETIME()
);
GO

-- Insert 1M orders in batches of 50,000
DECLARE @o INT = 1;
DECLARE @batchSize INT = 50000;

WHILE @o <= 1000000
BEGIN
    INSERT INTO dbo.Orders (CustomerID, ProductID, OrderDate, ShipDate, Quantity, UnitPrice, Discount, TotalAmount, OrderStatus, PaymentMethod, ShippingMethod, Region, CreatedAt, UpdatedAt)
    SELECT TOP (@batchSize)
        ABS(CHECKSUM(NEWID())) % 100000 + 1,  -- CustomerID (1-100000)
        ABS(CHECKSUM(NEWID())) % 5000 + 1,    -- ProductID (1-5000)
        DATEADD(DAY, -ABS(CHECKSUM(NEWID())) % 730, CAST(GETDATE() AS DATE)),  -- OrderDate (last 2 years)
        DATEADD(DAY, -ABS(CHECKSUM(NEWID())) % 720, CAST(GETDATE() AS DATE)),  -- ShipDate
        ABS(CHECKSUM(NEWID())) % 20 + 1,      -- Quantity (1-20)
        CAST(ABS(CHECKSUM(NEWID())) % 500 + 10 AS DECIMAL(10,2)),  -- UnitPrice
        CAST(ABS(CHECKSUM(NEWID())) % 30 AS DECIMAL(5,2)),          -- Discount %
        CAST((ABS(CHECKSUM(NEWID())) % 20 + 1) * (ABS(CHECKSUM(NEWID())) % 500 + 10) AS DECIMAL(12,2)),  -- TotalAmount
        CHOOSE(ABS(CHECKSUM(NEWID())) % 5 + 1, 'Completed','Shipped','Processing','Cancelled','Returned'),
        CHOOSE(ABS(CHECKSUM(NEWID())) % 4 + 1, 'CreditCard','DebitCard','PayPal','BankTransfer'),
        CHOOSE(ABS(CHECKSUM(NEWID())) % 3 + 1, 'Standard','Express','Overnight'),
        CHOOSE(ABS(CHECKSUM(NEWID())) % 6 + 1, 'North','South','East','West','Central','International'),
        DATEADD(DAY, -ABS(CHECKSUM(NEWID())) % 730, SYSUTCDATETIME()),
        DATEADD(DAY, -ABS(CHECKSUM(NEWID())) % 30, SYSUTCDATETIME())
    FROM sys.all_objects a CROSS JOIN sys.all_objects b;

    SET @o = @o + @batchSize;

    -- Progress indicator
    IF @o % 200000 = 1
        PRINT CONCAT('Inserted ', @o - 1, ' orders...');
END;
GO

SELECT COUNT(*) AS OrderCount FROM dbo.Orders;
-- Expected: 1,000,000
GO


-- ╔══════════════════════════════════════════════════════════════════════════════╗
-- ║  VERIFICATION                                                               ║
-- ╚══════════════════════════════════════════════════════════════════════════════╝

SELECT 'Customers' AS TableName, COUNT(*) AS [RowCount] FROM dbo.Customers
UNION ALL SELECT 'Orders', COUNT(*) FROM dbo.Orders
UNION ALL SELECT 'Products', COUNT(*) FROM dbo.Products;

-- Expected Output:
-- Customers:   100,000
-- Orders:    1,000,000
-- Products:     5,000
-- TOTAL:     1,105,000

-- Table sizes
EXEC sp_spaceused 'dbo.Customers';
EXEC sp_spaceused 'dbo.Orders';
EXEC sp_spaceused 'dbo.Products';
GO


-- ╔══════════════════════════════════════════════════════════════════════════════╗
-- ║  CREATE INDEXES (improve BCP export performance)                            ║
-- ╚══════════════════════════════════════════════════════════════════════════════╝

CREATE INDEX IX_Customers_UpdatedAt ON dbo.Customers(UpdatedAt);
CREATE INDEX IX_Orders_UpdatedAt ON dbo.Orders(UpdatedAt);
CREATE INDEX IX_Orders_CustomerID ON dbo.Orders(CustomerID);
CREATE INDEX IX_Orders_OrderDate ON dbo.Orders(OrderDate);
CREATE INDEX IX_Products_UpdatedAt ON dbo.Products(UpdatedAt);
GO

PRINT '✓ Large volume test data created successfully (1.1M rows total)';
GO

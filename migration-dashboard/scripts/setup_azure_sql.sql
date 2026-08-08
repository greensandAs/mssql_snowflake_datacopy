-- ============================================================================
-- MSSQL → Snowflake Migration: Azure SQL Test Data Setup
-- ============================================================================
-- Run this in Azure Query Editor or SSMS connected to ta-poc.database.windows.net
-- Login: tapocadmin / tiger@12345
-- ============================================================================

-- Create the test database (run on master if using SSMS)
-- In Azure Query Editor, select 'master' database first:
-- CREATE DATABASE TestDB;
-- Then switch to TestDB and run the rest.

-- ============================================================================
-- TABLE 1: Customers (FULL load test — 100 rows)
-- ============================================================================
IF OBJECT_ID('dbo.Customers', 'U') IS NOT NULL DROP TABLE dbo.Customers;

CREATE TABLE dbo.Customers (
    CustomerID INT PRIMARY KEY IDENTITY(1,1),
    FirstName NVARCHAR(50),
    LastName NVARCHAR(50),
    Email NVARCHAR(100),
    Phone NVARCHAR(20),
    City NVARCHAR(50),
    Country NVARCHAR(50),
    CreatedDate DATETIME2 DEFAULT GETDATE()
);

-- Insert 100 customers
DECLARE @i INT = 1;
WHILE @i <= 100
BEGIN
    INSERT INTO dbo.Customers (FirstName, LastName, Email, Phone, City, Country)
    VALUES (
        CONCAT('FirstName_', @i),
        CONCAT('LastName_', @i),
        CONCAT('user', @i, '@example.com'),
        CONCAT('+1-555-', RIGHT('0000' + CAST(@i * 37 % 10000 AS VARCHAR), 4)),
        CASE @i % 5
            WHEN 0 THEN 'New York'
            WHEN 1 THEN 'London'
            WHEN 2 THEN 'Mumbai'
            WHEN 3 THEN 'Dubai'
            WHEN 4 THEN 'Singapore'
        END,
        CASE @i % 5
            WHEN 0 THEN 'USA'
            WHEN 1 THEN 'UK'
            WHEN 2 THEN 'India'
            WHEN 3 THEN 'UAE'
            WHEN 4 THEN 'Singapore'
        END
    );
    SET @i = @i + 1;
END;


-- ============================================================================
-- TABLE 2: Orders (INCREMENTAL load test — 500 rows, has ModifiedDate watermark)
-- ============================================================================
IF OBJECT_ID('dbo.Orders', 'U') IS NOT NULL DROP TABLE dbo.Orders;

CREATE TABLE dbo.Orders (
    OrderID INT PRIMARY KEY IDENTITY(1,1),
    CustomerID INT,
    OrderDate DATETIME2,
    TotalAmount DECIMAL(10,2),
    Status NVARCHAR(20),
    ShippingCity NVARCHAR(50),
    CreatedDate DATETIME2 DEFAULT GETDATE(),
    ModifiedDate DATETIME2 DEFAULT GETDATE()
);

DECLARE @j INT = 1;
WHILE @j <= 500
BEGIN
    INSERT INTO dbo.Orders (CustomerID, OrderDate, TotalAmount, Status, ShippingCity, ModifiedDate)
    VALUES (
        (@j % 100) + 1,
        DATEADD(DAY, -(@j % 365), GETDATE()),
        CAST(10 + (RAND(CHECKSUM(NEWID())) * 990) AS DECIMAL(10,2)),
        CASE @j % 4
            WHEN 0 THEN 'Delivered'
            WHEN 1 THEN 'Shipped'
            WHEN 2 THEN 'Processing'
            WHEN 3 THEN 'Cancelled'
        END,
        CASE @j % 5
            WHEN 0 THEN 'New York'
            WHEN 1 THEN 'London'
            WHEN 2 THEN 'Mumbai'
            WHEN 3 THEN 'Dubai'
            WHEN 4 THEN 'Singapore'
        END,
        DATEADD(HOUR, -(@j % 720), GETDATE())
    );
    SET @j = @j + 1;
END;


-- ============================================================================
-- TABLE 3: Products (FULL load test — 50 rows)
-- ============================================================================
IF OBJECT_ID('dbo.Products', 'U') IS NOT NULL DROP TABLE dbo.Products;

CREATE TABLE dbo.Products (
    ProductID INT PRIMARY KEY IDENTITY(1,1),
    ProductName NVARCHAR(100),
    Category NVARCHAR(50),
    Price DECIMAL(10,2),
    StockQuantity INT,
    IsActive BIT DEFAULT 1,
    CreatedDate DATETIME2 DEFAULT GETDATE()
);

DECLARE @k INT = 1;
WHILE @k <= 50
BEGIN
    INSERT INTO dbo.Products (ProductName, Category, Price, StockQuantity, IsActive)
    VALUES (
        CONCAT('Product_', @k),
        CASE @k % 5
            WHEN 0 THEN 'Electronics'
            WHEN 1 THEN 'Clothing'
            WHEN 2 THEN 'Food'
            WHEN 3 THEN 'Furniture'
            WHEN 4 THEN 'Sports'
        END,
        CAST(5 + (RAND(CHECKSUM(NEWID())) * 495) AS DECIMAL(10,2)),
        CAST(RAND(CHECKSUM(NEWID())) * 1000 AS INT),
        CASE WHEN @k % 7 = 0 THEN 0 ELSE 1 END
    );
    SET @k = @k + 1;
END;


-- ============================================================================
-- Verify
-- ============================================================================
SELECT 'Customers' AS TableName, COUNT(*) AS RowCount FROM dbo.Customers
UNION ALL
SELECT 'Orders', COUNT(*) FROM dbo.Orders
UNION ALL
SELECT 'Products', COUNT(*) FROM dbo.Products;

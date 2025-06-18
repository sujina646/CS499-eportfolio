#pragma once
#include <sqlite3.h>
#include <string>
#include <vector>
#include <map>
#include <stdexcept>
#include <iostream>

// Class to handle database operations for scene persistence
class DatabaseManager {
public:
    DatabaseManager() : db(nullptr) {}
    
    ~DatabaseManager() {
        disconnect();
    }
    
    // Connect to a SQLite database
    bool connect(const std::string& dbPath) {
        if (db) {
            std::cerr << "Already connected to a database. Disconnect first." << std::endl;
            return false;
        }
        
        int result = sqlite3_open(dbPath.c_str(), &db);
        if (result != SQLITE_OK) {
            std::cerr << "Failed to open database: " << sqlite3_errmsg(db) << std::endl;
            sqlite3_close(db);
            db = nullptr;
            return false;
        }
        
        std::cout << "Connected to database: " << dbPath << std::endl;
        return true;
    }
    
    // Disconnect from the database
    void disconnect() {
        if (db) {
            sqlite3_close(db);
            db = nullptr;
            std::cout << "Disconnected from database." << std::endl;
        }
    }
    
    // Execute a SQL statement with no results
    bool execute(const std::string& sql, const std::vector<std::string>& params = {}) {
        if (!db) {
            throw std::runtime_error("Not connected to a database.");
        }
        
        sqlite3_stmt* stmt;
        int result = sqlite3_prepare_v2(db, sql.c_str(), -1, &stmt, nullptr);
        
        if (result != SQLITE_OK) {
            std::string error = sqlite3_errmsg(db);
            std::cerr << "SQL prepare error: " << error << std::endl;
            return false;
        }
        
        // Bind parameters
        for (size_t i = 0; i < params.size(); ++i) {
            result = sqlite3_bind_text(stmt, i + 1, params[i].c_str(), -1, SQLITE_TRANSIENT);
            if (result != SQLITE_OK) {
                std::cerr << "SQL bind error: " << sqlite3_errmsg(db) << std::endl;
                sqlite3_finalize(stmt);
                return false;
            }
        }
        
        // Execute statement
        result = sqlite3_step(stmt);
        
        // Clean up
        sqlite3_finalize(stmt);
        
        // Check for errors
        if (result != SQLITE_DONE && result != SQLITE_ROW) {
            std::cerr << "SQL execution error: " << sqlite3_errmsg(db) << std::endl;
            return false;
        }
        
        return true;
    }
    
    // Execute an INSERT statement and return the last inserted row ID
    int executeInsert(const std::string& sql, const std::vector<std::string>& params = {}) {
        if (!execute(sql, params)) {
            return -1;
        }
        
        return sqlite3_last_insert_rowid(db);
    }
    
    // Execute a SELECT statement and return results
    std::vector<std::map<std::string, std::string>> executeQuery(
        const std::string& sql, 
        const std::vector<std::string>& params = {}
    ) {
        std::vector<std::map<std::string, std::string>> results;
        
        if (!db) {
            throw std::runtime_error("Not connected to a database.");
        }
        
        sqlite3_stmt* stmt;
        int result = sqlite3_prepare_v2(db, sql.c_str(), -1, &stmt, nullptr);
        
        if (result != SQLITE_OK) {
            std::string error = sqlite3_errmsg(db);
            std::cerr << "SQL prepare error: " << error << std::endl;
            return results;
        }
        
        // Bind parameters
        for (size_t i = 0; i < params.size(); ++i) {
            result = sqlite3_bind_text(stmt, i + 1, params[i].c_str(), -1, SQLITE_TRANSIENT);
            if (result != SQLITE_OK) {
                std::cerr << "SQL bind error: " << sqlite3_errmsg(db) << std::endl;
                sqlite3_finalize(stmt);
                return results;
            }
        }
        
        // Execute and fetch results
        while ((result = sqlite3_step(stmt)) == SQLITE_ROW) {
            std::map<std::string, std::string> row;
            
            int columnCount = sqlite3_column_count(stmt);
            for (int i = 0; i < columnCount; ++i) {
                const char* columnName = sqlite3_column_name(stmt, i);
                
                // Get column value as text
                const unsigned char* value = sqlite3_column_text(stmt, i);
                if (value) {
                    row[columnName] = reinterpret_cast<const char*>(value);
                } else {
                    row[columnName] = "";
                }
            }
            
            results.push_back(row);
        }
        
        // Clean up
        sqlite3_finalize(stmt);
        
        // Check for errors
        if (result != SQLITE_DONE) {
            std::cerr << "SQL execution error: " << sqlite3_errmsg(db) << std::endl;
        }
        
        return results;
    }
    
    // Helper to check if a table exists
    bool tableExists(const std::string& tableName) {
        auto results = executeQuery(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
            {tableName}
        );
        
        return !results.empty();
    }
    
private:
    sqlite3* db;
}; 

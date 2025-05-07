#pragma once
#include "SceneObject.h"
#include "SceneNode.h"
#include <memory>
#include <vector>
#include <map>
#include <sqlite3.h>

class SceneManager {
public:
    SceneManager();
    ~SceneManager();

    void init();
    void renderScene();
    void handleKeyPress(unsigned char key, int x, int y);
    
    // Scene graph operations
    void addObject(std::shared_ptr<SceneObject> obj, SceneNode* parent = nullptr);
    void removeObject(SceneNode* node);
    
    // Database operations
    bool saveScene(const std::string& filename);
    bool loadScene(const std::string& filename);
    
    // Performance monitoring
    double getLastRenderTime() const { return lastRenderTime; }
    size_t getVisibleObjectCount() const { return visibleObjectCount; }

private:
    std::vector<std::unique_ptr<SceneNode>> sceneGraph;
    std::map<std::string, GLuint> textures;
    sqlite3* db;
    
    // Camera and view state
    glm::vec3 cameraPosition{0.0f, 0.0f, 5.0f};
    glm::vec3 cameraRotation{0.0f};
    
    // Performance metrics
    double lastRenderTime{0.0};
    size_t visibleObjectCount{0};
    
    // Helper methods
    bool isInFrustum(SceneNode* node) const;
    void loadTexture(const std::string& name, const std::string& filename);
    void initializeDatabase();
}; 
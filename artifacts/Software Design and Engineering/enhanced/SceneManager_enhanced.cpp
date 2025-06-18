#include "SceneNode.h"
#include "SceneObject.h"
#include "ResourceManager.h"
#include "DatabaseManager.h"
#include <GL/glut.h>
#include <map>
#include <string>
#include <memory>
#include <chrono>
#include <iostream>
#include <vector>

class SceneManager {
private:
    // Resource management
    ResourceManager resourceManager;
    
    // Scene graph root nodes
    std::vector<std::unique_ptr<SceneNode>> sceneGraph;
    
    // Camera and view state
    float cameraX = 0.0f, cameraY = 0.0f, cameraZ = 5.0f;
    float rotationX = 0.0f, rotationY = 0.0f;
    
    // Database for scene persistence
    DatabaseManager dbManager;
    
    // Performance metrics
    std::chrono::high_resolution_clock::time_point lastFrameTime;
    double frameRenderTime = 0.0;
    size_t visibleObjectCount = 0;
    
    // Observer pattern for scene change notifications
    std::vector<class SceneObserver*> observers;

public:
    SceneManager() : lastFrameTime(std::chrono::high_resolution_clock::now()) {
        // Initialize database connection
        dbManager.connect("kitchen_scene.db");
        
        // Create required tables if they don't exist
        dbManager.execute(
            "CREATE TABLE IF NOT EXISTS scenes ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  name TEXT NOT NULL,"
            "  creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            ");"
        );
        
        dbManager.execute(
            "CREATE TABLE IF NOT EXISTS scene_objects ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  scene_id INTEGER,"
            "  parent_id INTEGER,"
            "  type TEXT NOT NULL,"
            "  name TEXT,"
            "  pos_x REAL, pos_y REAL, pos_z REAL,"
            "  rot_x REAL, rot_y REAL, rot_z REAL,"
            "  scale_x REAL, scale_y REAL, scale_z REAL,"
            "  texture_name TEXT,"
            "  FOREIGN KEY (scene_id) REFERENCES scenes(id),"
            "  FOREIGN KEY (parent_id) REFERENCES scene_objects(id)"
            ");"
        );
    }
    
    ~SceneManager() {
        // Clean up resources
        dbManager.disconnect();
    }

    void init() {
        // Initialize textures through resource manager
        resourceManager.loadTexture("wood", "textures/wood.bmp");
        resourceManager.loadTexture("metal", "textures/metal.bmp");
        
        // Set up lighting
        glEnable(GL_LIGHTING);
        glEnable(GL_LIGHT0);
        GLfloat lightPos[] = {1.0f, 1.0f, 1.0f, 0.0f};
        glLightfv(GL_LIGHT0, GL_POSITION, lightPos);
        
        // Create scene graph
        createDefaultScene();
    }
    
    // Create a default kitchen scene
    void createDefaultScene() {
        // Create cutting board
        auto cuttingBoard = std::make_unique<SceneNode>();
        auto cuttingBoardObj = std::make_shared<CuttingBoard>();
        cuttingBoardObj->setTexture("wood");
        cuttingBoardObj->setPosition({0.0f, 0.0f, 0.0f});
        cuttingBoard->setObject(cuttingBoardObj);
        
        // Create teapot as child of cutting board
        auto teapot = std::make_unique<SceneNode>();
        auto teapotObj = std::make_shared<Teapot>();
        teapotObj->setTexture("metal");
        teapotObj->setPosition({0.5f, 0.5f, 0.0f});
        teapot->setObject(teapotObj);
        
        // Add teapot as child of cutting board
        cuttingBoard->addChild(std::move(teapot));
        
        // Create fruit bowl
        auto fruitBowl = std::make_unique<SceneNode>();
        auto fruitBowlObj = std::make_shared<FruitBowl>();
        fruitBowlObj->setPosition({-0.5f, 0.3f, 0.0f});
        fruitBowl->setObject(fruitBowlObj);
        
        // Create salt shaker
        auto saltShaker = std::make_unique<SceneNode>();
        auto saltShakerObj = std::make_shared<SaltShaker>();
        saltShakerObj->setPosition({0.0f, 0.2f, 0.5f});
        saltShaker->setObject(saltShakerObj);
        
        // Add all root nodes to scene graph
        sceneGraph.push_back(std::move(cuttingBoard));
        sceneGraph.push_back(std::move(fruitBowl));
        sceneGraph.push_back(std::move(saltShaker));
        
        // Notify observers
        notifySceneChanged();
    }

    void renderScene() {
        // Start timing
        auto startTime = std::chrono::high_resolution_clock::now();
        
        // Reset visibility counter
        visibleObjectCount = 0;
        
        // Set up camera
        glMatrixMode(GL_MODELVIEW);
        glLoadIdentity();
        glTranslatef(-cameraX, -cameraY, -cameraZ);
        glRotatef(rotationX, 1.0f, 0.0f, 0.0f);
        glRotatef(rotationY, 0.0f, 1.0f, 0.0f);
        
        // Render each node in the scene graph
        for (const auto& node : sceneGraph) {
            renderNode(node.get());
        }
        
        // Calculate render time
        auto endTime = std::chrono::high_resolution_clock::now();
        frameRenderTime = std::chrono::duration<double, std::milli>(endTime - startTime).count();
        
        // Calculate FPS
        auto frameTime = std::chrono::duration<double>(endTime - lastFrameTime).count();
        lastFrameTime = endTime;
        
        // Display performance metrics in console
        std::cout << "Render time: " << frameRenderTime << "ms, FPS: " << 1.0/frameTime 
                  << ", Visible objects: " << visibleObjectCount << std::endl;
    }
    
    // Recursive rendering of scene graph nodes
    void renderNode(SceneNode* node) {
        if (!node) return;
        
        // Check if node is in view frustum
        if (!isInFrustum(node)) {
            return; // Skip rendering if not in view
        }
        
        glPushMatrix();
        
        // Apply node's transformation
        auto transform = node->getWorldTransform();
        glTranslatef(transform.position.x, transform.position.y, transform.position.z);
        glRotatef(transform.rotation.x, 1.0f, 0.0f, 0.0f);
        glRotatef(transform.rotation.y, 0.0f, 1.0f, 0.0f);
        glRotatef(transform.rotation.z, 0.0f, 0.0f, 1.0f);
        glScalef(transform.scale.x, transform.scale.y, transform.scale.z);
        
        // Render the object if this node has one
        auto obj = node->getObject();
        if (obj) {
            // Bind texture if the object has one
            if (!obj->getTexture().empty()) {
                auto textureID = resourceManager.getTexture(obj->getTexture());
                glBindTexture(GL_TEXTURE_2D, textureID);
            }
            
            // Render the object
            obj->render();
            visibleObjectCount++;
        }
        
        // Render all children
        for (size_t i = 0; i < node->getChildCount(); ++i) {
            renderNode(node->getChild(i));
        }
        
        glPopMatrix();
    }

    void handleKeyPress(unsigned char key, int x, int y) {
        switch(key) {
            case 'w': cameraZ -= 0.1f; break;
            case 's': cameraZ += 0.1f; break;
            case 'a': cameraX -= 0.1f; break;
            case 'd': cameraX += 0.1f; break;
            case 'q': rotationY -= 5.0f; break;
            case 'e': rotationY += 5.0f; break;
            case 'r': rotationX -= 5.0f; break;
            case 'f': rotationX += 5.0f; break;
            case '1': saveScene("default"); break;
            case '2': loadScene("default"); break;
        }
        glutPostRedisplay();
    }
    
    // Scene graph operations
    void addNode(std::unique_ptr<SceneNode> node, SceneNode* parent = nullptr) {
        if (parent) {
            parent->addChild(std::move(node));
        } else {
            sceneGraph.push_back(std::move(node));
        }
        notifySceneChanged();
    }
    
    void removeNode(SceneNode* node) {
        // Find and remove the node
        for (auto it = sceneGraph.begin(); it != sceneGraph.end(); ++it) {
            if (it->get() == node) {
                sceneGraph.erase(it);
                notifySceneChanged();
                return;
            }
        }
        
        // If not found at root level, search in children
        for (auto& rootNode : sceneGraph) {
            if (removeNodeRecursive(rootNode.get(), node)) {
                notifySceneChanged();
                return;
            }
        }
    }
    
    bool removeNodeRecursive(SceneNode* parent, SceneNode* nodeToRemove) {
        for (size_t i = 0; i < parent->getChildCount(); ++i) {
            if (parent->getChild(i) == nodeToRemove) {
                parent->removeChild(i);
                return true;
            }
            
            if (removeNodeRecursive(parent->getChild(i), nodeToRemove)) {
                return true;
            }
        }
        return false;
    }
    
    // Observer pattern methods
    void addObserver(SceneObserver* observer) {
        observers.push_back(observer);
    }
    
    void removeObserver(SceneObserver* observer) {
        auto it = std::find(observers.begin(), observers.end(), observer);
        if (it != observers.end()) {
            observers.erase(it);
        }
    }
    
    void notifySceneChanged() {
        for (auto observer : observers) {
            observer->onSceneChanged();
        }
    }
    
    // Database operations
    bool saveScene(const std::string& name) {
        try {
            // Begin transaction
            dbManager.execute("BEGIN TRANSACTION;");
            
            // Clear previous scene with this name if it exists
            dbManager.execute("DELETE FROM scene_objects WHERE scene_id IN "
                             "(SELECT id FROM scenes WHERE name = ?);", {name});
            dbManager.execute("DELETE FROM scenes WHERE name = ?;", {name});
            
            // Insert new scene
            int sceneId = dbManager.executeInsert(
                "INSERT INTO scenes (name) VALUES (?);", {name}
            );
            
            // Save all objects
            for (const auto& node : sceneGraph) {
                saveNodeRecursive(node.get(), sceneId, -1); // -1 indicates no parent
            }
            
            // Commit transaction
            dbManager.execute("COMMIT;");
            std::cout << "Scene saved successfully." << std::endl;
            return true;
        } catch (const std::exception& e) {
            dbManager.execute("ROLLBACK;");
            std::cerr << "Error saving scene: " << e.what() << std::endl;
            return false;
        }
    }
    
    int saveNodeRecursive(SceneNode* node, int sceneId, int parentId) {
        if (!node) return -1;
        
        auto obj = node->getObject();
        auto transform = node->getWorldTransform();
        
        // Default values if no object
        std::string type = "empty";
        std::string name = "";
        std::string texture = "";
        
        if (obj) {
            type = obj->getType();
            name = obj->getName();
            texture = obj->getTexture();
        }
        
        // Insert node
        int nodeId = dbManager.executeInsert(
            "INSERT INTO scene_objects (scene_id, parent_id, type, name, "
            "pos_x, pos_y, pos_z, rot_x, rot_y, rot_z, scale_x, scale_y, scale_z, texture_name) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
            {
                sceneId, parentId, type, name, 
                transform.position.x, transform.position.y, transform.position.z,
                transform.rotation.x, transform.rotation.y, transform.rotation.z,
                transform.scale.x, transform.scale.y, transform.scale.z,
                texture
            }
        );
        
        // Save children
        for (size_t i = 0; i < node->getChildCount(); ++i) {
            saveNodeRecursive(node->getChild(i), sceneId, nodeId);
        }
        
        return nodeId;
    }
    
    bool loadScene(const std::string& name) {
        try {
            // Clear current scene
            sceneGraph.clear();
            
            // Get scene ID
            auto results = dbManager.executeQuery(
                "SELECT id FROM scenes WHERE name = ?;", {name}
            );
            
            if (results.empty()) {
                std::cerr << "Scene not found: " << name << std::endl;
                return false;
            }
            
            int sceneId = std::stoi(results[0]["id"]);
            
            // Load root nodes (those with no parent)
            auto rootNodes = dbManager.executeQuery(
                "SELECT * FROM scene_objects WHERE scene_id = ? AND parent_id IS NULL OR parent_id = -1;", 
                {sceneId}
            );
            
            for (const auto& row : rootNodes) {
                auto node = createNodeFromData(row);
                loadChildrenRecursive(node.get(), sceneId, std::stoi(row["id"]));
                sceneGraph.push_back(std::move(node));
            }
            
            notifySceneChanged();
            std::cout << "Scene loaded successfully." << std::endl;
            return true;
            
        } catch (const std::exception& e) {
            std::cerr << "Error loading scene: " << e.what() << std::endl;
            return false;
        }
    }
    
    std::unique_ptr<SceneNode> createNodeFromData(const std::map<std::string, std::string>& data) {
        auto node = std::make_unique<SceneNode>();
        
        // Create object based on type
        std::shared_ptr<SceneObject> obj = nullptr;
        std::string type = data.at("type");
        
        if (type == "CuttingBoard") {
            obj = std::make_shared<CuttingBoard>();
        } else if (type == "Teapot") {
            obj = std::make_shared<Teapot>();
        } else if (type == "FruitBowl") {
            obj = std::make_shared<FruitBowl>();
        } else if (type == "SaltShaker") {
            obj = std::make_shared<SaltShaker>();
        }
        
        if (obj) {
            // Set object properties
            if (data.count("name") > 0) {
                obj->setName(data.at("name"));
            }
            
            if (data.count("texture_name") > 0 && !data.at("texture_name").empty()) {
                obj->setTexture(data.at("texture_name"));
            }
            
            // Set position
            float x = std::stof(data.at("pos_x"));
            float y = std::stof(data.at("pos_y"));
            float z = std::stof(data.at("pos_z"));
            obj->setPosition({x, y, z});
            
            node->setObject(obj);
        }
        
        // Set node transform
        Transform transform;
        transform.position = {
            std::stof(data.at("pos_x")),
            std::stof(data.at("pos_y")),
            std::stof(data.at("pos_z"))
        };
        transform.rotation = {
            std::stof(data.at("rot_x")),
            std::stof(data.at("rot_y")),
            std::stof(data.at("rot_z"))
        };
        transform.scale = {
            std::stof(data.at("scale_x")),
            std::stof(data.at("scale_y")),
            std::stof(data.at("scale_z"))
        };
        node->setLocalTransform(transform);
        
        return node;
    }
    
    void loadChildrenRecursive(SceneNode* parent, int sceneId, int parentId) {
        auto children = dbManager.executeQuery(
            "SELECT * FROM scene_objects WHERE scene_id = ? AND parent_id = ?;",
            {sceneId, parentId}
        );
        
        for (const auto& row : children) {
            auto node = createNodeFromData(row);
            int nodeId = std::stoi(row["id"]);
            loadChildrenRecursive(node.get(), sceneId, nodeId);
            parent->addChild(std::move(node));
        }
    }
    
    // Performance metrics
    double getFrameRenderTime() const {
        return frameRenderTime;
    }
    
    size_t getVisibleObjectCount() const {
        return visibleObjectCount;
    }
    
private:
    // Helper method to check if object is in view frustum
    bool isInFrustum(SceneNode* node) {
        if (!node || !node->getObject()) {
            return false;
        }
        
        // Simple frustum culling based on distance
        auto transform = node->getWorldTransform();
        float distance = std::sqrt(
            std::pow(transform.position.x - cameraX, 2) +
            std::pow(transform.position.y - cameraY, 2) +
            std::pow(transform.position.z - cameraZ, 2)
        );
        
        // Skip objects too far away
        if (distance > 10.0f) {
            return false;
        }
        
        // In a real implementation, we would do proper view frustum culling
        // with the 6 frustum planes, but this is a simplified version
        return true;
    }
}; 

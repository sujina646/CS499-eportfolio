#pragma once
#include "SceneObject.h"
#include <memory>
#include <vector>
#include <algorithm>

// Transform structure to hold position, rotation, and scale
struct Transform {
    glm::vec3 position{0.0f, 0.0f, 0.0f};
    glm::vec3 rotation{0.0f, 0.0f, 0.0f};
    glm::vec3 scale{1.0f, 1.0f, 1.0f};
};

// Forward declaration for observer pattern
class SceneObserver {
public:
    virtual void onSceneChanged() = 0;
    virtual ~SceneObserver() = default;
};

class SceneNode {
public:
    SceneNode() : parent(nullptr) {}
    
    ~SceneNode() = default;
    
    // Object management
    void setObject(std::shared_ptr<SceneObject> obj) {
        object = obj;
    }
    
    std::shared_ptr<SceneObject> getObject() const {
        return object;
    }
    
    // Transform management
    void setLocalTransform(const Transform& transform) {
        localTransform = transform;
        updateWorldTransform();
    }
    
    Transform getLocalTransform() const {
        return localTransform;
    }
    
    Transform getWorldTransform() const {
        return worldTransform;
    }
    
    void updateWorldTransform() {
        if (parent) {
            // Combine parent's world transform with this node's local transform
            auto parentTransform = parent->getWorldTransform();
            
            // Position is affected by parent's position, rotation, and scale
            worldTransform.position = parentTransform.position + 
                                     parentTransform.scale * localTransform.position;
            
            // Rotation combines parent and local (simplified - in a real app we'd use quaternions)
            worldTransform.rotation = parentTransform.rotation + localTransform.rotation;
            
            // Scale multiplies
            worldTransform.scale = parentTransform.scale * localTransform.scale;
        } else {
            // Root node - world transform equals local transform
            worldTransform = localTransform;
        }
        
        // Update all children's world transforms
        for (auto& child : children) {
            child->updateWorldTransform();
        }
    }
    
    // Hierarchy management
    void addChild(std::unique_ptr<SceneNode> child) {
        child->parent = this;
        children.push_back(std::move(child));
        updateWorldTransform(); // Update transforms for the new branch
    }
    
    void removeChild(size_t index) {
        if (index < children.size()) {
            children.erase(children.begin() + index);
        }
    }
    
    SceneNode* getChild(size_t index) const {
        if (index < children.size()) {
            return children[index].get();
        }
        return nullptr;
    }
    
    size_t getChildCount() const {
        return children.size();
    }
    
    SceneNode* getParent() const {
        return parent;
    }

private:
    std::shared_ptr<SceneObject> object;
    std::vector<std::unique_ptr<SceneNode>> children;
    SceneNode* parent;
    
    Transform localTransform;
    Transform worldTransform;
}; 

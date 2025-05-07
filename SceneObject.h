#pragma once
#include <glm/glm.hpp>
#include <string>

class SceneObject {
public:
    virtual void render() = 0;
    virtual void update() = 0;
    
    void setPosition(const glm::vec3& pos) { position = pos; }
    void setTexture(const std::string& tex) { texture = tex; }
    
    glm::vec3 getPosition() const { return position; }
    std::string getTexture() const { return texture; }
    
    virtual ~SceneObject() = default;

protected:
    glm::vec3 position{0.0f};
    std::string texture;
}; 
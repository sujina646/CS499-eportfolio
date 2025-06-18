#pragma once
#include <GL/glut.h>
#include <string>
#include <unordered_map>
#include <iostream>
#include <memory>

// Class to manage and cache resources like textures, models, etc.
class ResourceManager {
public:
    ResourceManager() = default;
    ~ResourceManager() {
        // Clean up all textures when the manager is destroyed
        for (const auto& pair : textures) {
            GLuint id = pair.second;
            glDeleteTextures(1, &id);
        }
        textures.clear();
    }
    
    // Prevent copying to avoid double-freeing resources
    ResourceManager(const ResourceManager&) = delete;
    ResourceManager& operator=(const ResourceManager&) = delete;
    
    // Load a texture if it doesn't exist, or return existing one
    GLuint loadTexture(const std::string& name, const std::string& filename) {
        // Check if texture already exists
        auto it = textures.find(name);
        if (it != textures.end()) {
            std::cout << "Using cached texture: " << name << std::endl;
            return it->second;
        }
        
        // Create new texture
        GLuint textureID;
        glGenTextures(1, &textureID);
        glBindTexture(GL_TEXTURE_2D, textureID);
        
        // Set texture parameters
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
        
        // Load image data (simplified for this example)
        // In a real application, we would use a library like stb_image.h
        std::cout << "Loading texture: " << filename << std::endl;
        
        // Simulate loading texture data
        unsigned char* data = new unsigned char[256 * 256 * 3];
        // Fill with some dummy data
        for (int i = 0; i < 256 * 256; i++) {
            data[i*3] = (i % 256);         // R
            data[i*3+1] = ((i/256) % 256); // G
            data[i*3+2] = ((i+128) % 256); // B
        }
        
        // Upload texture data
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, 256, 256, 0, GL_RGB, GL_UNSIGNED_BYTE, data);
        glGenerateMipmap(GL_TEXTURE_2D);
        
        // Free memory
        delete[] data;
        
        // Store in cache
        textures[name] = textureID;
        
        return textureID;
    }
    
    // Get a texture by name
    GLuint getTexture(const std::string& name) const {
        auto it = textures.find(name);
        if (it != textures.end()) {
            return it->second;
        }
        std::cerr << "Texture not found: " << name << std::endl;
        return 0; // Default texture ID or error value
    }
    
    // Unload a specific texture
    void unloadTexture(const std::string& name) {
        auto it = textures.find(name);
        if (it != textures.end()) {
            GLuint id = it->second;
            glDeleteTextures(1, &id);
            textures.erase(it);
            std::cout << "Unloaded texture: " << name << std::endl;
        }
    }
    
    // Get memory usage statistics
    size_t getTextureCount() const {
        return textures.size();
    }
    
    // This would be expanded with similar methods for meshes, shaders, etc.
    
private:
    std::unordered_map<std::string, GLuint> textures;
}; 

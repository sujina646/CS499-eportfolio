#include <GL/glut.h>
#include <map>
#include <string>

class SceneManager {
private:
    std::map<std::string, GLuint> textures;
    float cameraX = 0.0f, cameraY = 0.0f, cameraZ = 5.0f;
    float rotationX = 0.0f, rotationY = 0.0f;

public:
    void init() {
        // Initialize textures
        loadTexture("wood", "textures/wood.bmp");
        loadTexture("metal", "textures/metal.bmp");
        
        // Set up lighting
        glEnable(GL_LIGHTING);
        glEnable(GL_LIGHT0);
        GLfloat lightPos[] = {1.0f, 1.0f, 1.0f, 0.0f};
        glLightfv(GL_LIGHT0, GL_POSITION, lightPos);
    }

    void renderScene() {
        glBindTexture(GL_TEXTURE_2D, textures["wood"]);
        // Render cutting board
        glBegin(GL_QUADS);
        glTexCoord2f(0, 0); glVertex3f(-1, 0, -1);
        glTexCoord2f(1, 0); glVertex3f(1, 0, -1);
        glTexCoord2f(1, 1); glVertex3f(1, 0, 1);
        glTexCoord2f(0, 1); glVertex3f(-1, 0, 1);
        glEnd();

        // Render teapot
        glBindTexture(GL_TEXTURE_2D, textures["metal"]);
        glPushMatrix();
        glTranslatef(0.5f, 0.5f, 0.0f);
        glutSolidTeapot(0.3);
        glPopMatrix();

        // Render fruit bowl
        glPushMatrix();
        glTranslatef(-0.5f, 0.3f, 0.0f);
        glutSolidSphere(0.2, 32, 32);
        glPopMatrix();

        // Render salt shaker
        glPushMatrix();
        glTranslatef(0.0f, 0.2f, 0.5f);
        glutSolidCylinder(0.1, 0.3, 32, 32);
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
        }
        glutPostRedisplay();
    }

private:
    void loadTexture(const std::string& name, const std::string& filename) {
        // Texture loading implementation
        // This is a placeholder for the actual texture loading code
        GLuint textureID;
        glGenTextures(1, &textureID);
        textures[name] = textureID;
    }
}; 

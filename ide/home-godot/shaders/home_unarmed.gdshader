shader_type canvas_item;

// Home is a peaceful space. The shared hunter sheets still contain a sword;
// hide its outer silhouette here without changing the source or combat art.
// Coordinates are in the original 48x46 sprite cell, before horizontal flip.
uniform int facing = 0; // 0 front, 1 side, 2 back

void fragment() {
    vec2 pixel = floor(UV / TEXTURE_PIXEL_SIZE);
    float x = mod(pixel.x, 48.0);
    float y = pixel.y;
    bool blade = false;
    if (facing == 0) {
        blade = y >= 29.0 && x >= 29.0 && x >= y - 4.0;
    } else if (facing == 1) {
        blade = y >= 30.0 && x <= 22.0 && x + y <= 53.0;
    } else {
        blade = y >= 27.0 && x <= 17.0 && x + y <= 49.0;
    }
    if (blade) {
        COLOR.a = 0.0;
    }
}

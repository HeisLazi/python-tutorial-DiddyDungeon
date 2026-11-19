shader_type canvas_item;
// Cloth sway: shifts rows sideways, more toward the hem. Sprite2D is anchored at its feet,
// so local y runs from -height (top) to 0 (hem).
uniform float amp = 0.9;
uniform float speed = 1.8;
uniform float height = 36.0;
uniform float phase = 0.0;

void vertex() {
	float t = clamp((VERTEX.y + height) / height, 0.0, 1.0);
	VERTEX.x += sin(TIME * speed + phase + VERTEX.y * 0.18) * amp * t * t;
}

shader_type canvas_item;
// The opponent is an explicitly simulated hollow figure, not a real mob.
void fragment() {
    vec4 pixel = texture(TEXTURE, UV);
    float value = dot(pixel.rgb, vec3(0.299, 0.587, 0.114));
    float edge = step(0.25, value);
    float scan = mod(floor(FRAGCOORD.y / 2.0), 3.0) == 0.0 ? 0.7 : 1.0;
    COLOR = vec4(mix(vec3(0.04, 0.31, 0.58), vec3(0.52, 0.94, 1.0), value * 0.8 + edge * 0.12) * scan, pixel.a * 0.88);
}

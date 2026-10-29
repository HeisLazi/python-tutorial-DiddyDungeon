shader_type canvas_item;
// The opponent is an explicitly simulated hollow figure, not a real mob.
void fragment() {
    vec4 pixel = texture(TEXTURE, UV);
    float value = dot(pixel.rgb, vec3(0.299, 0.587, 0.114));
    float edge = step(0.25, value);
    float scan = mod(floor(FRAGCOORD.y / 2.0), 3.0) == 0.0 ? 0.82 : 1.0;
    COLOR = vec4(mix(vec3(0.06, 0.47, 0.68), vec3(0.68, 1.0, 1.0), value * 0.8 + edge * 0.12) * scan, pixel.a * 0.97);
}

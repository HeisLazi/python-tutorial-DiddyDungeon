shader_type canvas_item;
uniform vec3 tint : source_color = vec3(1.0);
uniform float strength = 0.0;
uniform bool ivory = false;
varying vec4 sprite_color;
void vertex() { sprite_color = COLOR; }
void fragment() {
    vec4 tex = texture(TEXTURE, UV);
    float high = max(tex.r, max(tex.g, tex.b));
    float low = min(tex.r, min(tex.g, tex.b));
    float neutral = (1.0 - smoothstep(0.04, 0.18, high - low)) * smoothstep(0.10, 0.28, high);
    vec3 recolor = tex.rgb * tint;
    if (ivory) {
        // Below the head, lift the near-neutral coat while keeping black outlines.
        float coat = (1.0 - smoothstep(0.05, 0.20, high - low)) * smoothstep(0.045, 0.15, high) * smoothstep(0.34, 0.46, UV.y);
        recolor = mix(recolor, vec3(0.53, 0.51, 0.48) + tex.rgb * 0.48, coat);
        neutral = max(neutral, coat);
    }
    COLOR = vec4(mix(tex.rgb, recolor, neutral * strength), tex.a) * sprite_color;
}

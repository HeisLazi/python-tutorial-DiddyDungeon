shader_type canvas_item;
uniform vec3 tint : source_color = vec3(1.0);
uniform float strength = 0.0;
uniform bool ivory = false;
uniform vec4 armor_mastery_tint : source_color = vec4(1.0, 1.0, 1.0, 0.0);
uniform vec4 weapon_mastery_tint : source_color = vec4(1.0, 1.0, 1.0, 0.0);
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
    vec3 final_color = mix(tex.rgb, recolor, neutral * strength);
    vec2 pixel = floor(UV * vec2(56.0, 72.0));
    float fleck = step(0.91, fract(sin(dot(pixel, vec2(12.9898, 78.233))) * 43758.5453 + TIME * 0.12));
    float mastery_mask = step(0.30, high) * (0.72 + fleck * 0.28);
    final_color = mix(final_color, armor_mastery_tint.rgb, mastery_mask * 0.16 * armor_mastery_tint.a);
    float weapon_fleck = step(0.965, fract(sin(dot(pixel + vec2(17.0, 31.0), vec2(39.346, 11.135))) * 24634.6345 + TIME * 0.17));
    final_color = mix(final_color, weapon_mastery_tint.rgb, weapon_fleck * 0.34 * weapon_mastery_tint.a);
    COLOR = vec4(final_color, tex.a) * sprite_color;
}
